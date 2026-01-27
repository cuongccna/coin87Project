"""Market intelligence endpoints (read-only).

Provides a decision-grade dashboard summary derived from existing coin87
decision-risk primitives (snapshots + risk-linked information events).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import enforce_rate_limit, enforce_read_only_access, get_db_session
from app.repositories.market_intel_repo import MarketIntelRepository
from app.repositories.narrative_repo import NarrativeRepository
from app.schemas.market_intel import (
    InformationReliabilityResponse,
    InformationReliabilityState,
    InformationSignal,
    ReliabilityLevel,
    InformationCategory
)
from app.security.auth import require_roles
from app.security.roles import Role


UTC = timezone.utc
Asset = Literal["BTC", "ETH", "MARKET"]

router = APIRouter(
    dependencies=[
        Depends(enforce_read_only_access),
        Depends(require_roles(Role.READ_ONLY, Role.PM, Role.CIO, Role.RISK)),
        Depends(enforce_rate_limit),
    ]
)


def _score_to_level(score_0_100: int) -> ReliabilityLevel:
    if score_0_100 >= 80:
        return "high"
    if score_0_100 >= 60:
        return "medium"
    if score_0_100 >= 40:
        return "low"
    return "unverified"


def _category_mapping(repo_cat: str) -> InformationCategory:
    if repo_cat == "macro":
        return "event"
    return "narrative"  # default fallthrough


@router.get("/intel", response_model=InformationReliabilityResponse)
async def get_market_intel(asset: Asset = "MARKET", db: Session = Depends(get_db_session)) -> InformationReliabilityResponse:
    """Get information reliability dashboard summary.
    
    Provides a high-level view of information trust state (NOT price state).
    """
    now = datetime.now(tz=UTC)
    repo = MarketIntelRepository(db)
    narrative_repo = NarrativeRepository(db)

    market = await repo.get_market_summary(now=now)
    # Fetch active narratives count for the "State" object
    active_narratives = await narrative_repo.list_active_narratives(limit=100)
    
    news = await repo.list_news(now=now, limit=30, asset=asset)

    return InformationReliabilityResponse(
        state=InformationReliabilityState(
            overall_reliability=_score_to_level(market.score),
            confirmation_rate=market.confidence, # Using confidence as proxy for confirmation rate
            contradiction_rate=max(0, 100 - market.confidence),
            active_narratives_count=len(active_narratives)
        ),
        signals=[
            InformationSignal(
                title=n.title,
                reliability_score=n.score, # Repo returns 0-10 float
                reliability_level=_score_to_level(int(n.score * 10)),
                confirmation_count=max(1, int(n.confidence / 20)), # Rough proxy
                persistence_hours=int(n.confidence / 10), # Rough proxy for persistence
                category=_category_mapping(n.category),
                narrative_id=n.narrative_id,
            )
            for n in news
        ],
    )

