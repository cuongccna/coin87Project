"""
Job: Promote InformationEvents to InversionFeeds.
Logic: Selects recent raw events, applies simple heuristics (symbol/sentiment), 
deduplicates based on source_id, and publishes to InversionFeed table + Redis.
Now Includes: Narrative Risk Logic (Heuristic V1).
"""
import sys
import json
import logging
import re
import random
from typing import List, Optional, Tuple, Dict
from uuid import UUID
from datetime import datetime, timezone
from pathlib import Path

# Setup path to import backend app modules
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import select, exists
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.information_event import InformationEvent
from app.models.information_event_enrichment import InformationEventEnrichment
from app.models.inversion_feed import InversionFeed
from app.services.redis_client import get_redis
from derive.lib.inversion_hints import pick_hint_for_text

# Configuration
SYMBOL_MAP = {
    r'\b(bitcoin|btc)\b': 'BTC',
    r'\b(ethereum|eth)\b': 'ETH',
    r'\b(solana|sol)\b': 'SOL',
    r'\b(ripple|xrp)\b': 'XRP',
    r'\b(bnb|binance coin)\b': 'BNB'
}

UP_KEYWORDS = {'surge', 'soar', 'jump', 'rally', 'climb', 'gain', 'bull', 'high', 'breakout', 'record', 'etf', 'approve'}
DOWN_KEYWORDS = {'drop', 'plunge', 'crash', 'dump', 'slump', 'loss', 'bear', 'low', 'dip', 'lawsuit', 'ban', 'hack', 'risk'}

# Inversion Keywords - Signs of potential narrative deception/conflict
# Used to auto-assign risk levels if LLM is not available.
HIGH_RISK_KEYWORDS = {'hack', 'ban', 'lawsuit', 'investigation', 'insolvency', 'arrest', 'sec ', 'regulation'}
CONFLICT_KEYWORDS = {'debate', 'uncertain', 'delay', 'analyst', 'predicts', 'could', 'might', 'rumor'} 

logger = logging.getLogger("promote_feed")
logging.basicConfig(level=logging.INFO)

def extract_symbol(text: str) -> str:
    text_lower = text.lower()
    for pattern, symbol in SYMBOL_MAP.items():
        if re.search(pattern, text_lower):
            return symbol
    return "OTHERS"

def analyze_sentiment(text: str) -> str:
    text_lower = text.lower()
    words = set(re.findall(r'\w+', text_lower))
    score = 0
    for w in words:
        if w in UP_KEYWORDS: score += 1
        elif w in DOWN_KEYWORDS: score -= 1
    if score > 0: return "up"
    elif score < 0: return "down"
    return "neutral"

def analyze_narrative_risk(text: str, sentiment: str) -> dict:
    """
    Returns dict containing comprehensive risk analysis:
    {
        risk_level, inversion_summary, why_shown, 
        iri_score, trapped_persona, expectation_gap, feed_icon
    }
    """
    text_lower = text.lower()
    
    # 1. Check High Risk Keywords (Security/Regulation FUD)
    for kw in HIGH_RISK_KEYWORDS:
        if kw in text_lower:
            return {
                "risk_level": "HIGH",
                "inversion_summary": f"Critical headline keyword '{kw}' detected. High probability of retail panic selling.",
                "why_shown": "High misinterpretation risk",
                "iri_score": 5,
                "trapped_persona": "Panic sellers reacting to headlines without checking on-chain movement.",
                "expectation_gap": "If true, price drops instantly on high volume. If price floats, it's FUD.",
                "inversion_hint": pick_hint_for_text(text, "high"),
                "feed_icon": "⚠️"
            }

    # 2. Check Conflict Keywords (Analyst Opinions/Rumors)
    for kw in CONFLICT_KEYWORDS:
        if kw in text_lower:
            return {
                "risk_level": "MEDIUM",
                "inversion_summary": f"Speculative language ({kw}) detected. Narrative often precedes actual capital flow.",
                "why_shown": "Narrative ≠ Capital Flow",
                "iri_score": 3,
                "trapped_persona": "Early longs betting on unconfirmed rumors.",
                 "expectation_gap": "Watch for spot buying to confirm. If only perps pump, it's a trap.",
                 "inversion_hint": pick_hint_for_text(text, "medium"),
                "feed_icon": "🧠"
            }

    # 3. Sentiment Inversion Logic (Simple Heuristic for V1)
    if sentiment == 'up':
        return {
            "risk_level": "LOW",
            "inversion_summary": "Positive momentum. Be aware of 'Sell the News' if price has already run up.",
            "why_shown": "Confirmation Bias check",
            "iri_score": 1,
            "trapped_persona": "Late FOMO buyers entering at local tops.",
                "expectation_gap": "This signal validates past price action, not future confirmation.",
                "inversion_hint": pick_hint_for_text(text, "low"),
            "feed_icon": "ℹ️"
        }
    
    if sentiment == 'down':
        return {
            "risk_level": "LOW",
            "inversion_summary": "Negative sentiment. Check if bad news is already priced in.",
            "why_shown": "Oversold verification",
            "iri_score": 2,
            "trapped_persona": "Late shorters after the move has happened.",
                "expectation_gap": "Review volume absorption. Acting now increases probability of confirmation bias.",
                "inversion_hint": pick_hint_for_text(text, "low"),
            "feed_icon": "ℹ️"
        }

    return {
        "risk_level": "LOW",
        "inversion_summary": "Neutral update. Monitor for volume anomalies.",
        "why_shown": "Contextual awareness",
        "iri_score": 1,
        "trapped_persona": "Over-traders looking for signals in noise.",
        "expectation_gap": "No immediate action expected.",
        "inversion_hint": pick_hint_for_text(text, "low"),
        "feed_icon": "ℹ️"
    }


def process_promotion(limit: int = 50):
    db = SessionLocal()
    try:
        # 1. Get IDs already promoted
        promoted_stmt = select(InversionFeed.source_id).where(InversionFeed.source_id.is_not(None))
        existing_source_ids = set(db.scalars(promoted_stmt).all())

        # 2. Get Recent Information Events with Enrichment
        results = (
            db.query(InformationEvent, InformationEventEnrichment)
            .outerjoin(InformationEventEnrichment, InformationEvent.id == InformationEventEnrichment.information_event_id)
            .order_by(InformationEvent.observed_at.desc())
            .limit(limit * 2) 
            .all()
        )

        count = 0
        redis_client = get_redis()
        
        for ev, enrichment in results:
            if count >= limit:
                break
            
            if ev.id in existing_source_ids:
                continue

            # Core Heuristics
            full_text = ev.title + " " + (ev.body_excerpt or "")
            symbol = extract_symbol(full_text)
            sentiment = analyze_sentiment(ev.title)
            
            # Risk Analysis (The Jewish Logic Layer)
            risk_data = analyze_narrative_risk(ev.title, sentiment)
            
            # Override with AI enrichment if available (Expectation Gap V2)
            if enrichment and enrichment.narrative_analysis:
                na = enrichment.narrative_analysis
                # Use AI insights if present
                if na.get("expected_mechanism"):
                    risk_data["expectation_gap"] = na["expected_mechanism"]
                if na.get("trapped_persona"):
                    risk_data["trapped_persona"] = na["trapped_persona"]
                
                # Refine Inversion Summary with invalidation signal
                if na.get("invalidation_signal"):
                    # We keep the summary punchy, maybe prepend validaton failure
                    risk_data["inversion_summary"] = f"Trap Signal: {na['invalidation_signal']}"

                # Use AI-determined sentiment/risk if high confidence
                if enrichment.confidence and enrichment.confidence > 0.7:
                    if enrichment.sentiment == 'bullish':
                        risk_data["risk_level"] = "LOW"
                    elif enrichment.sentiment == 'bearish':
                        risk_data["risk_level"] = "HIGH"
                    risk_data["iri_score"] = int(enrichment.confidence * 5)  # 0.8 -> 4, 0.9 -> 4

            
            # Map Risk Level to 'direction' field temporarily for backward compat compatibility
            # Let's use 'direction' for Risk Level (HIGH, MED, LOW) as requested in Plan.
            
            risk_level = risk_data["risk_level"]
            risk_code = risk_level.lower() 

            feed_payload = {
                "title": ev.title,
                "source": ev.source_ref,
                "url": ev.canonical_url or ev.external_ref,
                # New Inversion Fields
                "narrative_risk": risk_level, 
                "inversion_summary": risk_data["inversion_summary"],
                "why_shown": risk_data["why_shown"],
                "iri_score": risk_data.get("iri_score", 1),
                "trapped_persona": risk_data.get("trapped_persona", "N/A"),
                "expectation_gap": risk_data.get("expectation_gap", "N/A"),
                "inversion_hint": risk_data.get("inversion_hint", ""),
                "feed_icon": risk_data.get("feed_icon", "ℹ️"),
                "sentiment_original": sentiment
            }

            feed = InversionFeed(
                source_id=ev.id,
                external_id=f"auto-{ev.id}",
                symbol=symbol,
                feed_type="narrative_risk", # Changed from news-analysis
                direction=risk_code, 
                value=None, 
                confidence=min(1.0, max(0.0, (feed_payload.get("iri_score", 3) / 5.0))),  # Risk Index to 0-1 scale
                payload=feed_payload,
                status="processed" # Immediately ready
            )
            
            db.add(feed)
            db.commit()
            db.refresh(feed)
            
            existing_source_ids.add(ev.id)
            count += 1
            
            # Realtime Publish
            if redis_client:
                msg = {
                    "id": str(feed.id),
                    "symbol": feed.symbol,
                    "feed_type": feed.feed_type,
                    "direction": feed.direction, # now holds risk level
                    "confidence": float(feed.confidence),
                    "created_at": feed.created_at.isoformat(),
                    "payload": feed_payload # Send full payload for UI to render
                }
                redis_client.publish("inversion:updates", json.dumps(msg))

        logger.info(f"Promoted {count} events with Narrative Risk analysis.")

    except Exception as e:
        logger.error(f"Error in promotion job: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    
    process_promotion(args.limit)
