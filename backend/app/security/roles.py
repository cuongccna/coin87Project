"""Role model for institutional access control."""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """Institutional roles (ordered by privilege)."""

    READ_ONLY = "READ_ONLY"
    PM = "PM"
    CIO = "CIO"
    RISK = "RISK"


def is_role_allowed(subject_role: Role, allowed: set[Role]) -> bool:
    """Default-deny role check with explicit allow set."""
    return subject_role in allowed

