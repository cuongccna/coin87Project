"""Read-only market intelligence repository.

IMPORTANT:
- Uses only existing decision-risk primitives (snapshots + risk events + information events).
- Produces deterministic, UI-facing summary values.
- No DB writes; no session mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.decision_environment_snapshot import DecisionEnvironmentSnapshot
from app.models.decision_risk_event import DecisionRiskEvent
from app.models.information_event import InformationEvent
from app.models.narrative_cluster import narrative_memberships
from app.repositories.base import BaseRepository


UTC = timezone.utc
MarketBias = Literal["bullish", "bearish", "neutral"]
NewsCategory = Literal["onchain", "macro", "sentiment"]
Asset = Literal["BTC", "ETH", "MARKET"]

# Keywords for asset-based filtering (case-insensitive)
ASSET_KEYWORDS: dict[str, list[str]] = {
    "BTC": ["bitcoin", "btc", "saylor", "microstrategy", "lightning network", "halving"],
    "ETH": ["ethereum", "eth", "vitalik", "layer 2", "l2", "eip-", "beacon", "staking"],
}


@dataclass(frozen=True, slots=True)
class MarketSummaryDTO:
    bias: MarketBias
    score: int
    confidence: int
    short_term_trend: Optional[str]


@dataclass(frozen=True, slots=True)
class NewsItemDTO:
    title: str
    score: float
    bias: MarketBias
    confidence: int
    impact: str
    category: NewsCategory
    narrative_id: Optional[str] = None


class MarketIntelRepository(BaseRepository[object]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    async def _latest_snapshots(self, limit: int = 5) -> list[DecisionEnvironmentSnapshot]:
        stmt = (
            select(DecisionEnvironmentSnapshot)
            .order_by(DecisionEnvironmentSnapshot.snapshot_time.desc())
            .limit(limit)
        )
        rows = (await self._execute(stmt)).scalars().all()
        return list(rows)

    @staticmethod
    def _score_from_snapshot(snap: DecisionEnvironmentSnapshot) -> int:
        # Deterministic mapping from "decision safety" state -> score 0..100.
        base = {"CLEAN": 85, "CAUTION": 65, "CONTAMINATED": 45}.get(str(snap.environment_state), 60)
        penalty = min(max(int(snap.risk_density), 0), 15) * 2
        return max(0, min(100, int(base - penalty)))

    @staticmethod
    def _bias_from_snapshot(snap: DecisionEnvironmentSnapshot) -> MarketBias:
        # Conservative: only label bearish when environment is contaminated.
        if str(snap.environment_state) == "CONTAMINATED":
            return "bearish"
        if str(snap.environment_state) == "CLEAN" and int(snap.risk_density) <= 1:
            return "bullish"
        return "neutral"

    @staticmethod
    def _confidence_from_snapshot(snap: DecisionEnvironmentSnapshot, *, now: datetime) -> int:
        # Conservative confidence: decays with staleness and risk density.
        staleness_min = max(0, int((now - snap.snapshot_time).total_seconds() // 60))
        base = 78
        base -= min(staleness_min, 240) // 10  # -0..-24
        base -= min(max(int(snap.risk_density), 0), 10) * 2
        return max(30, min(90, int(base)))

    @staticmethod
    def _trend_from_scores(scores_desc: list[int]) -> Optional[str]:
        # scores_desc: most recent first.
        if len(scores_desc) < 3:
            return None
        a, b, c = scores_desc[0], scores_desc[1], scores_desc[2]
        if a > b > c:
            return "improving"
        if a < b < c:
            return "deteriorating"
        return "stable"

    async def get_market_summary(self, *, now: datetime) -> MarketSummaryDTO:
        snaps = await self._latest_snapshots(limit=5)
        if not snaps:
            # No snapshots yet: safest neutral defaults.
            return MarketSummaryDTO(bias="neutral", score=50, confidence=40, short_term_trend=None)

        latest = snaps[0]
        score_latest = self._score_from_snapshot(latest)
        scores_desc = [self._score_from_snapshot(s) for s in snaps]
        return MarketSummaryDTO(
            bias=self._bias_from_snapshot(latest),
            score=score_latest,
            confidence=self._confidence_from_snapshot(latest, now=now),
            short_term_trend=self._trend_from_scores(scores_desc),
        )

    @staticmethod
    def _news_score_from_severity(severity: int) -> float:
        # Map severity 1..5 -> score 0..10 with high-impact at severity>=4.
        sev = max(1, min(5, int(severity)))
        return round(5.0 + (sev - 1) * 1.25, 1)  # 5.0, 6.3, 7.5, 8.8, 10.0

    @staticmethod
    def _news_confidence_from_severity(severity: int) -> int:
        sev = max(1, min(5, int(severity)))
        return max(45, min(90, 40 + sev * 10))

    @staticmethod
    def _news_category_from_risk_type(risk_type: str) -> NewsCategory:
        # Deterministic coarse category mapping.
        if risk_type == "STRUCTURAL_DECISION_RISK":
            return "macro"
        return "sentiment"

    @staticmethod
    def _matches_asset(title: str, asset: Asset) -> bool:
        """Check if title matches asset keywords. MARKET matches all."""
        if asset == "MARKET":
            return True
        keywords = ASSET_KEYWORDS.get(asset, [])
        if not keywords:
            return True
        title_lower = title.lower()
        return any(kw.lower() in title_lower for kw in keywords)

    async def list_news(self, *, now: datetime, limit: int = 30, asset: Asset = "MARKET") -> list[NewsItemDTO]:
        # Use risk-linked items only to avoid fabricating scores for low-impact news.
        window_start = now - timedelta(days=2)
        # Fetch more rows to allow for filtering, then slice to limit
        fetch_limit = limit * 3 if asset != "MARKET" else limit
        stmt = (
            select(DecisionRiskEvent, InformationEvent, narrative_memberships.c.narrative_id)
            .join(InformationEvent, InformationEvent.id == DecisionRiskEvent.information_event_id)
            .outerjoin(narrative_memberships, narrative_memberships.c.decision_risk_event_id == DecisionRiskEvent.id)
            .where(DecisionRiskEvent.detected_at >= window_start)
            .order_by(DecisionRiskEvent.severity.desc(), DecisionRiskEvent.detected_at.desc())
            .limit(fetch_limit)
        )
        rows = (await self._execute(stmt)).all()

        out: list[NewsItemDTO] = []
        for risk, info, nid in rows:
            # Filter by asset
            if not self._matches_asset(info.title, asset):
                continue
            # Enum safety: prefer `.value` if present for clean API output.
            risk_type = getattr(risk.risk_type, "value", str(risk.risk_type))
            posture = getattr(risk.recommended_posture, "value", str(risk.recommended_posture))
            out.append(
                NewsItemDTO(
                    title=info.title,
                    score=self._news_score_from_severity(int(risk.severity)),
                    bias="neutral",
                    confidence=self._news_confidence_from_severity(int(risk.severity)),
                    impact=f"Decision risk: {risk_type}. Severity {int(risk.severity)}/5. Posture {posture}.",
                    category=self._news_category_from_risk_type(risk_type),
                    narrative_id=str(nid) if nid else None,
                )
            )
            if len(out) >= limit:
                break
        return out

