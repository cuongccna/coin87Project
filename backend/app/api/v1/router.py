"""API v1 root router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.decision_environment import router as decision_environment_router
from app.api.v1.decision_risk import router as decision_risk_router
from app.api.v1.institutional_memory import router as institutional_memory_router
from app.api.v1.market_intel import router as market_intel_router
from app.api.v1.narratives import router as narratives_router


router = APIRouter()
router.include_router(decision_environment_router, prefix="/decision", tags=["decision-environment"])
router.include_router(decision_risk_router, prefix="/decision", tags=["decision-risk"])
router.include_router(narratives_router, prefix="/decision", tags=["narratives"])
router.include_router(institutional_memory_router, prefix="/decision", tags=["institutional-memory"])
router.include_router(market_intel_router, prefix="/market", tags=["market-intel"])

