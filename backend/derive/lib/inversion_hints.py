"""Inversion Hint Library v1

Provides short, neutral, timing-focused hints to help users avoid confirmation bias
and timing errors. Hints are <=20 words, neutral tone, avoid buy/sell/pump/dump.

Functions:
- pick_hint_for_text(text, risk_level): choose appropriate hint based on keywords
- pick_hint_by_category(category): return a hint from a named category
"""

import random
from typing import List

TIMING = [
    "This information aligns with recent price action, not future confirmation.",
    "Acting now likely reflects delayed response, not new insight.",
    "Price movement preceded the narrative, reducing informational edge.",
    "This update validates what already happened, not what comes next.",
    "Late reaction risk increases when headlines follow price.",
]

NARRATIVE_VS_CAPITAL = [
    "Narrative strength exceeds observable capital confirmation.",
    "Verbal conviction appears before measurable capital commitment.",
    "Language intensity is not matched by transaction evidence.",
    "Market storytelling is ahead of actual flow verification.",
    "Consensus narrative lacks proportional capital response.",
]

SENTIMENT_BIAS = [
    "High interpretive confidence may signal confirmation bias.",
    "Emotional clarity does not imply informational advantage.",
    "Certainty increases as ambiguity is selectively ignored.",
    "Negative framing can exaggerate perceived urgency.",
    "Positive consensus often reduces independent assessment.",
]

NOISE_VS_SIGNAL = [
    "This signal lacks differentiation from normal market noise.",
    "Statistical relevance remains unverified at current resolution.",
    "Observed movement falls within expected volatility range.",
    "Pattern recognition may exceed available evidence.",
    "No structural deviation detected beyond routine fluctuation.",
]

ALL_CATEGORIES = {
    "timing": TIMING,
    "narrative": NARRATIVE_VS_CAPITAL,
    "sentiment": SENTIMENT_BIAS,
    "noise": NOISE_VS_SIGNAL,
}

KEYWORD_MAP = {
    "timing": ["price", "volume", "spike", "run up", "sell the news", "priced in", "followed"],
    "narrative": ["analyst", "rumor", "report", "claim", "statement", "narrative"],
    "sentiment": ["panic", "fear", "greed", "confident", "certainty", "emotion"],
    "noise": ["noise", "routine", "normal", "volatility", "statistical", "pattern"],
}


def pick_hint_by_category(category: str) -> str:
    """Return a random hint from given category. Defaults to timing if unknown."""
    cat = category.lower() if category else "timing"
    hints = ALL_CATEGORIES.get(cat, TIMING)
    return random.choice(hints)


def pick_hint_for_text(text: str, risk_level: str = None) -> str:
    """Heuristic selection of hint category based on keywords present in text.

    If multiple categories match, prioritize timing -> narrative -> sentiment -> noise.
    If none match, fallback by risk_level mapping: MEDIUM->narrative, HIGH->sentiment, else timing.
    """
    t = (text or "").lower()
    matches: List[str] = []
    for cat, kws in KEYWORD_MAP.items():
        for kw in kws:
            if kw in t:
                matches.append(cat)
                break

    # Prioritize
    priority = ["timing", "narrative", "sentiment", "noise"]
    for p in priority:
        if p in matches:
            return pick_hint_by_category(p)

    # Fallback to risk_level mapping
    if risk_level:
        rl = (risk_level or "").lower()
        if rl == "high":
            return pick_hint_by_category("sentiment")
        if rl == "medium":
            return pick_hint_by_category("narrative")
    return pick_hint_by_category("timing")
