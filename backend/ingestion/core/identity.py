"""
Identity & Proxy Profile Manager for Coin87.

COIN87 MANIFESTO LOCK:
"On Information, Trust, and Silence"

This module ensures Coin87 appears as a small set of consistent, 
human-like visitors rather than a rotating swarm of bots.

Design Principles:
- Consistency: Same Headers + UA + IP for long durations.
- Affinity: Bind identities to proxies to simulate "one person, one connection".
- Restraint: Rotate only when forced by blocks or natural expiry.
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# --- BROWSER FINGERPRINTS ---
# Realistic, consistent browser profiles.
# DO NOT generate random headers; use known good sets.

COMMON_HEADERS_CHROME_WIN = {
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
}

COMMON_HEADERS_FIREFOX_MAC = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "DNT": "1",
}


class ProfileStatus(str, Enum):
    ACTIVE = "active"
    COOLING_DOWN = "cooling_down"
    RETIRED = "retired"


class ProxyProfile(BaseModel):
    """
    Represents a long-lived proxy connection.
    In a real system, this would hold the proxy URL with sticky session ID.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proxy_url: Optional[str] = None  # None implies direct connection (local IP)
    region: str = "us"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    
    model_config = ConfigDict(frozen=True)


class IdentityProfile(BaseModel):
    """
    Represents a consistent browser identity.
    Includes User-Agent and specific Headers that MUST travel together.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Browser Fingerprint
    browser_family: str  # e.g. "chrome", "firefox"
    os_family: str       # e.g. "windows", "macos"
    headers: Dict[str, str]
    
    # State
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: ProfileStatus = ProfileStatus.ACTIVE
    
    # Affinity (One-to-One with Proxy)
    proxy_profile: Optional[ProxyProfile] = None

    class Config:
        validate_assignment = True


class ProfileManager:
    """
    Manages the lifecycle of Identities and Proxies.
    Ensures consistency and affinity.
    """
    
    def __init__(self):
        # In-memory store for active profiles. 
        # In production, this persists to DB/Redis.
        self._profiles: Dict[str, IdentityProfile] = {}
        
        # Mapping source_id -> profile_id
        self._source_assignments: Dict[str, str] = {}
        
    def get_profile_for_source(self, source_id: str, current_profile_id: Optional[str] = None) -> IdentityProfile:
        """
        Retrieve the assigned profile for a source.
        
        Args:
            source_id: The source needing identity.
            current_profile_id: The ID currently stored in SourceState (for persistence continuity).
        
        Creates a new one ONLY if:
        1. No profile assigned/found.
        2. Assigned profile is retired/expired.
        """
        # 1. Try to recover from passed ID (persistence)
        if current_profile_id and source_id not in self._source_assignments:
             # In a real DB-backed system, we'd load the profile here.
             # mocked: If we don't have it in memory, we assume it's lost/expired unless we can reconstruct.
             # For this simulation, if we don't know it, we unfortunately have to create new or 
             # (better) assume the state store passed us valid data? 
             # We can't return a full object from an ID if we don't have the object data.
             # ASSUMPTION: ProfileManager is the source of truth for Profile DATA. SourceState only holds the ID reference.
             pass

        # 2. Check internal assignment
        profile_id = self._source_assignments.get(source_id) or current_profile_id
        profile = self._profiles.get(profile_id) if profile_id else None
        
        # Check validity
        if profile:
            if profile.status == ProfileStatus.RETIRED:
                logger.info(f"Identity {profile.id} retired. Rotating.")
                profile = None
            elif profile.proxy_profile and datetime.now(timezone.utc) > profile.proxy_profile.expires_at:
                logger.info(f"Proxy for {profile.id} expired. Rotating session.")
                # We rotate the whole identity to be safe when IP changes significantly
                # Or we could keep UA and get new Proxy. Manifesto suggests consistency.
                # Let's retire the identity to avoid "Same User, New IP" flagging.
                self.retire_profile(profile.id, reason="proxy_expired")
                profile = None

        if not profile:
            profile = self._create_new_identity()
            self._profiles[profile.id] = profile
            self._source_assignments[source_id] = profile.id
            logger.info(f"Assigned new identity {profile.id} to {source_id}")
            
        return profile

    def retire_profile(self, profile_id: str, reason: str):
        """Mark a profile as retired. It will be replaced on next fetch."""
        if profile_id in self._profiles:
            self._profiles[profile_id].status = ProfileStatus.RETIRED
            logger.warning(f"Retired profile {profile_id}. Reason: {reason}")

    def report_block(self, source_id: str, is_hard_block: bool):
        """
        Handle consequences of a block on the specific identity.
        """
        profile_id = self._source_assignments.get(source_id)
        if not profile_id:
            return
            
        if is_hard_block:
            # Burnt identity. Retire immediately.
            self.retire_profile(profile_id, reason="hard_block")
        else:
            # Soft block. Might keep identity but cool it down?
            # For now, we trust the NetworkClient to handle temporal cooldowns.
            # But if a profile gets flagged often, we should retire it.
            # Implementation: This would track strikes against the profile.
            pass

    def _create_new_identity(self) -> IdentityProfile:
        """Create a fresh identity with a sticky proxy session."""
        
        # 1. Select Browser Template
        # Randomly choose between Chrome/Win and Firefox/Mac
        # In reality, this sets weights based on global usage stats
        is_chrome = random.choice([True, False])
        
        if is_chrome:
            family = "chrome"
            os_fam = "windows"
            headers = COMMON_HEADERS_CHROME_WIN.copy()
        else:
            family = "firefox"
            os_fam = "macos"
            headers = COMMON_HEADERS_FIREFOX_MAC.copy()
            
        # 2. Assign Proxy
        # Simulate a sticky residential proxy session
        # Lifetime: 24 - 72 hours
        session_lifetime = random.randint(24, 72)
        proxy = ProxyProfile(
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=session_lifetime),
            # proxy_url="http://user:pass@residential-entry-point:port" 
        )
        
        return IdentityProfile(
            browser_family=family,
            os_family=os_fam,
            headers=headers,
            proxy_profile=proxy
        )
