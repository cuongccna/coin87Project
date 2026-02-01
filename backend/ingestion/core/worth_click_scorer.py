"""Worth-Click Scoring - Quyết định có nên fetch detailed content hay không.

Rule-based scoring dựa trên:
- Tier của source (1-5)
- Priority (high/medium/low)
- Keyword matching (high-value signals)
- Time-based factors
- Filter result penalty
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone, time as dt_time
from typing import Optional

logger = logging.getLogger("coin87.ingestion.scorer")


@dataclass
class ScoringBreakdown:
    """Chi tiết cách tính score."""
    base_score: float
    tier_bonus: float
    priority_bonus: float
    keyword_bonus: float
    time_bonus: float
    filter_penalty: float
    final_score: float
    
    def __str__(self) -> str:
        return (
            f"Score={self.final_score:.1f} "
            f"(base={self.base_score:.1f} + tier={self.tier_bonus:.1f} + "
            f"priority={self.priority_bonus:.1f} + keyword={self.keyword_bonus:.1f} + "
            f"time={self.time_bonus:.1f} - penalty={self.filter_penalty:.1f})"
        )


# High-value keywords (regulatory, institutional, technical breakthroughs)
HIGH_VALUE_KEYWORDS = {
    # Regulatory & Legal
    "sec", "cftc", "regulation", "lawsuit", "settlement", "approval", "etf", 
    "compliance", "enforcement", "ruling", "court", "legal",
    
    # Institutional
    "institutional", "fund", "custody", "grayscale", "blackrock", "fidelity",
    "microstrategy", "tesla", "bank", "jpmorgan", "goldman",
    
    # Security & Exploits
    "hack", "exploit", "vulnerability", "breach", "attack", "stolen",
    "security", "audit", "bug", "critical",
    
    # Technical & Protocol
    "upgrade", "fork", "mainnet", "testnet", "proposal", "eip", "bip",
    "consensus", "node", "validator", "staking",
    
    # Market Structure
    "liquidity", "volume", "derivatives", "futures", "options", "otc",
    "market maker", "exchange listing", "delisting",
    
    # Macro
    "inflation", "federal reserve", "interest rate", "treasury", "bond",
    "central bank", "monetary policy", "sanctions",
}

# Medium-value keywords (market events, launches)
MEDIUM_VALUE_KEYWORDS = {
    "launch", "announcement", "partnership", "integration", "acquisition",
    "funding", "investment", "raise", "series", "ipo",
    "price", "rally", "crash", "surge", "drop", "high", "low",
    "adoption", "usage", "tvl", "defi", "nft", "layer 2",
}


class WorthClickScorer:
    """Rule-based scorer để quyết định có fetch detailed content không."""
    
    def __init__(self, worth_click_threshold: float = 5.0):
        """
        Args:
            worth_click_threshold: Ngưỡng score để quyết định fetch (default: 5.0)
        """
        self.threshold = worth_click_threshold
        
        # Compile keyword patterns
        self._high_value_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(k) for k in HIGH_VALUE_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self._medium_value_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(k) for k in MEDIUM_VALUE_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
    
    def score(
        self,
        title: str,
        summary: Optional[str],
        source_tier: int,
        source_priority: str,
        published_time: Optional[datetime] = None,
        filter_penalty: float = 0.0,
        worth_click_keywords: Optional[list[str]] = None,
    ) -> ScoringBreakdown:
        """
        Tính worth-click score cho một RSS item.
        
        Args:
            title: Title của item
            summary: Summary/excerpt (optional)
            source_tier: Tier của source (1-5)
            source_priority: Priority (high/medium/low)
            published_time: Thời gian publish (optional)
            filter_penalty: Penalty từ content filter (0.0-1.0)
            worth_click_keywords: Custom keywords từ source config (optional)
            
        Returns:
            ScoringBreakdown với final_score và chi tiết
        """
        # 1. Base score (mọi item đều có)
        base_score = 2.0
        
        # 2. Tier bonus (quan trọng nhất)
        tier_bonus = self._calculate_tier_bonus(source_tier)
        
        # 3. Priority bonus
        priority_bonus = self._calculate_priority_bonus(source_priority)
        
        # 4. Keyword bonus
        full_text = title
        if summary:
            full_text += " " + summary[:500]  # Chỉ check 500 chars đầu
            
        keyword_bonus = self._calculate_keyword_bonus(full_text, worth_click_keywords)
        
        # 5. Time-based bonus (market hours, freshness)
        time_bonus = self._calculate_time_bonus(published_time)
        
        # 6. Final score
        final_score = max(0.0, min(10.0, (
            base_score + 
            tier_bonus + 
            priority_bonus + 
            keyword_bonus + 
            time_bonus - 
            filter_penalty
        )))
        
        return ScoringBreakdown(
            base_score=base_score,
            tier_bonus=tier_bonus,
            priority_bonus=priority_bonus,
            keyword_bonus=keyword_bonus,
            time_bonus=time_bonus,
            filter_penalty=filter_penalty,
            final_score=final_score,
        )
    
    def should_fetch_detailed(self, score: ScoringBreakdown) -> bool:
        """Quyết định có nên fetch detailed content không."""
        return score.final_score >= self.threshold
    
    def _calculate_tier_bonus(self, tier: int) -> float:
        """Tier 1 = highest bonus, Tier 5 = lowest."""
        tier_bonuses = {
            1: 3.0,  # Major news sources
            2: 1.5,  # Aggregators, on-chain
            3: 0.5,  # Protocol/technical
            4: 0.0,  # Social sentiment
            5: -1.0, # Telegram (penalty)
        }
        return tier_bonuses.get(tier, 0.0)
    
    def _calculate_priority_bonus(self, priority: str) -> float:
        """Priority bonus."""
        priority_bonuses = {
            "high": 1.0,
            "medium": 0.5,
            "low": 0.0,
        }
        return priority_bonuses.get(priority.lower(), 0.0)
    
    def _calculate_keyword_bonus(
        self, 
        text: str, 
        custom_keywords: Optional[list[str]] = None
    ) -> float:
        """Keyword matching bonus."""
        bonus = 0.0
        
        # High-value keywords
        high_matches = len(self._high_value_pattern.findall(text))
        if high_matches > 0:
            bonus += min(2.0, high_matches * 0.5)  # Max +2.0
        
        # Medium-value keywords
        medium_matches = len(self._medium_value_pattern.findall(text))
        if medium_matches > 0:
            bonus += min(1.0, medium_matches * 0.3)  # Max +1.0
        
        # Custom keywords từ source config
        if custom_keywords:
            for kw in custom_keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE):
                    bonus += 0.5
        
        return min(3.0, bonus)  # Cap tổng keyword bonus ở 3.0
    
    def _calculate_time_bonus(self, published_time: Optional[datetime]) -> float:
        """Time-based bonus."""
        if not published_time:
            return 0.0
        
        bonus = 0.0
        now = datetime.now(timezone.utc)
        
        # 1. Freshness bonus (càng mới càng tốt)
        age_hours = (now - published_time).total_seconds() / 3600
        if age_hours < 1:
            bonus += 1.0  # Rất mới (< 1h)
        elif age_hours < 6:
            bonus += 0.5  # Mới (< 6h)
        
        # 2. Market hours bonus (UTC 13:00-21:00 = US market hours)
        # Crypto markets 24/7 nhưng US hours vẫn có volume cao nhất
        pub_hour = published_time.hour
        if 13 <= pub_hour <= 21:
            bonus += 0.5
        
        return bonus


# Singleton instance
_scorer_instance: Optional[WorthClickScorer] = None


def get_scorer(threshold: float = 5.0) -> WorthClickScorer:
    """Get singleton scorer instance."""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = WorthClickScorer(worth_click_threshold=threshold)
    return _scorer_instance
