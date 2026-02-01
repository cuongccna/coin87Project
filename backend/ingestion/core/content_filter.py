"""Pre-Filter Layer - Loại bỏ nội dung spam/low-value trước khi xem xét detailed fetch.

Philosophy: RSS = sensor, không phải reader.
Mục tiêu: Giảm 60-70% items cần detailed fetch.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger("coin87.ingestion.filter")


class FilterDecision(str, Enum):
    """Kết quả quyết định filter."""
    PASS = "pass"              # Đủ chất lượng để xem xét
    REJECT_SPAM = "reject_spam"            # Spam rõ ràng
    REJECT_LOW_VALUE = "reject_low_value"  # Nội dung giá trị thấp
    REJECT_PROMOTIONAL = "reject_promotional"  # Nội dung quảng cáo
    REJECT_DUPLICATE = "reject_duplicate"      # Duplicate pattern


@dataclass
class FilterResult:
    """Kết quả pre-filter."""
    decision: FilterDecision
    reason: str
    score_penalty: float = 0.0  # Penalty điểm cho scorer (0.0 - 1.0)


# Patterns spam/promotional
SPAM_TITLE_PATTERNS = [
    r"price prediction",
    r"price alert",
    r"top \d+",
    r"best \d+",
    r"how to (buy|sell|trade)",
    r"beginner['\s]s? guide",
    r"ultimate guide",
    r"step by step",
    r"make money",
    r"get rich",
    r"guaranteed",
    r"click here",
    r"limited offer",
    r"act now",
    r"don't miss",
    r"exclusive deal",
]

# Patterns low-value
LOW_VALUE_PATTERNS = [
    r"meme (coin|token)",
    r"shit ?coin",
    r"pump and dump",
    r"to the moon",
    r"hodl",
    r"wen lambo",
    r"giveaway",
    r"airdrop alert",
]

# Patterns promotional
PROMOTIONAL_PATTERNS = [
    r"sponsored",
    r"partner content",
    r"brought to you by",
    r"in collaboration with",
    r"advertisement",
]

# Categories/tags spam (nếu RSS có)
SPAM_CATEGORIES = {
    "sponsored",
    "advertisement",
    "promotional",
    "partner-content",
    "press-release",
}


class ContentFilter:
    """Pre-filter cho RSS items dựa trên heuristics."""

    def __init__(self):
        # Compile regex patterns một lần
        self._spam_patterns = [re.compile(p, re.IGNORECASE) for p in SPAM_TITLE_PATTERNS]
        self._low_value_patterns = [re.compile(p, re.IGNORECASE) for p in LOW_VALUE_PATTERNS]
        self._promo_patterns = [re.compile(p, re.IGNORECASE) for p in PROMOTIONAL_PATTERNS]

    def check(
        self,
        title: str,
        summary: Optional[str] = None,
        categories: Optional[list[str]] = None,
        url: Optional[str] = None,
    ) -> FilterResult:
        """
        Kiểm tra nội dung có đáng xem xét không.
        
        Args:
            title: Title của item
            summary: Summary/excerpt (optional)
            categories: RSS categories/tags (optional)
            url: Canonical URL (optional)
            
        Returns:
            FilterResult với decision và reason
        """
        # 1. Check title length
        if len(title) < 40:
            return FilterResult(
                decision=FilterDecision.REJECT_LOW_VALUE,
                reason=f"Title quá ngắn ({len(title)} chars < 40)",
                score_penalty=0.5,
            )

        # 2. Check spam patterns in title
        for pattern in self._spam_patterns:
            if pattern.search(title):
                return FilterResult(
                    decision=FilterDecision.REJECT_SPAM,
                    reason=f"Title chứa spam pattern: {pattern.pattern}",
                    score_penalty=1.0,
                )

        # 3. Check low-value patterns
        for pattern in self._low_value_patterns:
            if pattern.search(title):
                return FilterResult(
                    decision=FilterDecision.REJECT_LOW_VALUE,
                    reason=f"Title chứa low-value pattern: {pattern.pattern}",
                    score_penalty=0.7,
                )

        # 4. Check promotional patterns (in title or summary)
        full_text = title
        if summary:
            full_text += " " + summary[:200]  # Chỉ check 200 chars đầu của summary
            
        for pattern in self._promo_patterns:
            if pattern.search(full_text):
                return FilterResult(
                    decision=FilterDecision.REJECT_PROMOTIONAL,
                    reason=f"Nội dung promotional: {pattern.pattern}",
                    score_penalty=0.8,
                )

        # 5. Check spam categories
        if categories:
            spam_cats = set(cat.lower().replace(" ", "-") for cat in categories) & SPAM_CATEGORIES
            if spam_cats:
                return FilterResult(
                    decision=FilterDecision.REJECT_PROMOTIONAL,
                    reason=f"Category spam: {', '.join(spam_cats)}",
                    score_penalty=0.9,
                )

        # 6. Check URL spam patterns (optional)
        if url:
            # Các domain spam/aggregator chất lượng thấp
            spam_domains = ["prweb.com", "prnewswire.com", "businesswire.com"]
            for domain in spam_domains:
                if domain in url.lower():
                    return FilterResult(
                        decision=FilterDecision.REJECT_PROMOTIONAL,
                        reason=f"URL từ press release service: {domain}",
                        score_penalty=0.6,
                    )

        # 7. Check all-caps spam
        if title.isupper() and len(title) > 20:
            return FilterResult(
                decision=FilterDecision.REJECT_SPAM,
                reason="Title all-caps (spam indicator)",
                score_penalty=0.8,
            )

        # PASS - đủ chất lượng để xem xét
        return FilterResult(
            decision=FilterDecision.PASS,
            reason="Passed pre-filter checks",
            score_penalty=0.0,
        )


# Singleton instance
_filter_instance: Optional[ContentFilter] = None


def get_filter() -> ContentFilter:
    """Get singleton filter instance."""
    global _filter_instance
    if _filter_instance is None:
        _filter_instance = ContentFilter()
    return _filter_instance
