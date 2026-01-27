"""Contradiction Detection Module.

Analyze relationship between new information and existing narrative clusters.
Determine if new information supports, contradicts, or corrects established facts.

Coin87 Philosophy:
- Factual consistency only
- Ignore sentiment/market impact
- "Correction" implies a specific intent to fix previous info
- "Contradiction" implies factual conflict (e.g., numbers differ)
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Optional

from derive.core.clustering import (
    ExistingClusterSummary,
    LLMProviderInterface, 
    ClusteringResult, # Reuse existing types if suitable or define parallel ones
)


class ConsistencyStatus(str, Enum):
    CONFIRMS = "CONFIRMS"      # Agrees with existing facts
    CONTRADICTS = "CONTRADICTS" # Factually conflicts with existing cluster
    CORRECTS = "CORRECTS"      # Explicitly corrects previous info (e.g. "Correction:", "Update:")
    UNRELATED = "UNRELATED"    # No factual overlap


@dataclass(frozen=True)
class ConsistencyResult:
    status: ConsistencyStatus
    cluster_id: Optional[str]
    reasoning: Optional[str]
    confidence: float


class ContradictionDetector:
    """AI-assisted contradiction detection."""

    def __init__(self, llm_provider: LLMProviderInterface):
        self.llm = llm_provider

    async def check_consistency(
        self,
        new_text: str,
        target_cluster: ExistingClusterSummary
    ) -> ConsistencyResult:
        """Check factual consistency against a specific cluster."""
        
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(new_text, target_cluster)
        
        try:
            raw_response = await self.llm.chat_completion(system_prompt, user_prompt)
            return self._parse_response(raw_response, target_cluster.id)
        except Exception as e:
            # Safe fallback
            return ConsistencyResult(
                status=ConsistencyStatus.UNRELATED,
                cluster_id=target_cluster.id,
                reasoning=f"Error: {str(e)}",
                confidence=0.0
            )

    def _build_system_prompt(self) -> str:
        return """
You are the Factual Consistency Engine for Coin87.
Your job is to compare new information against an established narrative.

Strict Rules:
1. FOCUS ONLY ON FACTS (numbers, dates, names, events).
2. Ignore sentiment opinions.
3. Compare the NEW TEXT against the CLUSTER TOPIC.

Output Labels:
- CONFIRMS: The new text repeats or supports the cluster facts.
- CONTRADICTS: The new text states facts that are mutually exclusive (e.g. "hacked" vs "safe").
- CORRECTS: The new text explicitly issues a correction (e.g. "Clarification:", "Update: It was not a hack").
- UNRELATED: The new text is about a different topic entirely.

Output JSON:
{
    "status": "CONFIRMS" | "CONTRADICTS" | "CORRECTS" | "UNRELATED",
    "reasoning": "brief explanation",
    "confidence": 0.0 to 1.0
}
"""

    def _build_user_prompt(self, text: str, cluster: ExistingClusterSummary) -> str:
        return f"""
Cluster Topic: "{cluster.theme}"

New Information:
\"\"\"
{text}
\"\"\"

Determine the factual relationship.
"""

    def _parse_response(self, raw_json: str, cluster_id: str) -> ConsistencyResult:
        import json
        try:
            clean_json = raw_json.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
                
            data = json.loads(clean_json)
            
            return ConsistencyResult(
                status=ConsistencyStatus(data.get("status", "UNRELATED")),
                cluster_id=cluster_id,
                reasoning=data.get("reasoning"),
                confidence=float(data.get("confidence", 0.0))
            )
        except (json.JSONDecodeError, ValueError):
            return ConsistencyResult(
                status=ConsistencyStatus.UNRELATED,
                cluster_id=cluster_id,
                reasoning="Parse failed",
                confidence=0.0
            )
