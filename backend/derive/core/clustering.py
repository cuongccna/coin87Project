"""AI-assisted information clustering module.

Responsibility:
- Analyze new text content against existing narrative clusters.
- Determine if text belongs to an existing cluster or forms a new one.
- Strictly enforcing FACTUAL similarity, ignoring sentiment/market impact.

Coin87 Philosophy:
- Does NOT predict price
- Does NOT generate trading signals
- Evaluates INFORMATION RELIABILITY over time
"""

from __future__ import annotations

import abc
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.models.narrative_cluster import NarrativeCluster


class ClusterDecisionResult(str, Enum):
    EXISTING_CLUSTER = "EXISTING_CLUSTER"
    NEW_CLUSTER = "NEW_CLUSTER"
    IGNORE_NOISE = "IGNORE_NOISE"


@dataclass(frozen=True)
class ExistingClusterSummary:
    """Minimal representation of an existing cluster for the LLM context."""
    id: str
    theme: str
    last_seen_iso: str


@dataclass(frozen=True)
class ClusteringResult:
    """Result of the AI clustering decision."""
    decision: ClusterDecisionResult
    cluster_id: Optional[uuid.UUID] = None  # If EXISTING_CLUSTER
    new_topic: Optional[str] = None         # If NEW_CLUSTER
    reasoning: Optional[str] = None         # Audit trail (why this decision?)
    confidence_score: float = 0.0           # 0.0 to 1.0


class LLMProviderInterface(abc.ABC):
    """Abstract interface for LLM provider (OpenAI, Anthropic, Local, etc.)."""
    
    @abc.abstractmethod
    async def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        """Send prompt to LLM and return raw string response."""


class ClusteringEngine:
    """Core logic for AI-assisted clustering."""

    def __init__(self, llm_provider: LLMProviderInterface):
        self.llm = llm_provider

    async def classify_content(
        self,
        text_content: str,
        existing_clusters: list[ExistingClusterSummary]
    ) -> ClusteringResult:
        """Classify new content against existing clusters.
        
        Refuses to ingest if content is noise.
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(text_content, existing_clusters)
        
        try:
            raw_response = await self.llm.chat_completion(system_prompt, user_prompt)
            return self._parse_llm_response(raw_response)
        except Exception as e:
            # Fallback or error handling - for now return noise to be safe
            return ClusteringResult(
                decision=ClusterDecisionResult.IGNORE_NOISE,
                reasoning=f"LLM Error: {str(e)}"
            )

    def _build_system_prompt(self) -> str:
        return """
You are the Information Reliability Engine for Coin87.
Your ONLY job is to cluster incoming text into factual information narratives.

Strict Rules:
1. FOCUS ONLY ON FACTUAL EVENTS AND CLAIMS.
2. IGNORE sentiment (bullish/bearish).
3. IGNORE price predictions or market impact analysis.
4. IGNORE trading advice or calls to action.
5. Group inputs that describe the SAME underlying event or situation, even if sources differ.

Output Format:
You must respond with valid JSON only. No other text.

Schema:
{
    "decision": "EXISTING_CLUSTER" | "NEW_CLUSTER" | "IGNORE_NOISE",
    "target_cluster_id": "uuid-string" (only if EXISTING_CLUSTER),
    "new_topic_summary": "short factual string" (only if NEW_CLUSTER),
    "reasoning": "short explanation of factual similarity",
    "confidence": 0.0 to 1.0
}

Decision Logic:
- EXISTING_CLUSTER: The new text refers to the exact same event/narrative as an active cluster.
- NEW_CLUSTER: The new text refers to a discrete, factual event not listed.
- IGNORE_NOISE: The text is purely opinion, price spam, promotional, or vague.
"""

    def _build_user_prompt(
        self,
        text: str,
        clusters: list[ExistingClusterSummary]
    ) -> str:
        cluster_list_text = "\n".join(
            [f"- ID: {c.id} | Topic: {c.theme}" for c in clusters]
        )
        
        if not cluster_list_text:
            cluster_list_text = "(No existing active clusters)"

        return f"""
Active Clusters:
{cluster_list_text}

New Input Text:
\"\"\"
{text}
\"\"\"

Analyze the input text. Does it match any Active Cluster factually?
If yes, map to EXISTING_CLUSTER.
If no, and it is a factual event, create NEW_CLUSTER with a concise, neutral topic name (max 5-7 words).
If it is opinion/spam/price-talk, select IGNORE_NOISE.
"""

    def _parse_llm_response(self, raw_json: str) -> ClusteringResult:
        """Parse strict JSON response from LLM."""
        try:
            # heuristic cleanup if LLM adds markdown blocks
            clean_json = raw_json.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            
            data = json.loads(clean_json)
            
            decision_str = data.get("decision", "IGNORE_NOISE")
            decision = ClusterDecisionResult.IGNORE_NOISE
            if decision_str == "EXISTING_CLUSTER":
                decision = ClusterDecisionResult.EXISTING_CLUSTER
            elif decision_str == "NEW_CLUSTER":
                decision = ClusterDecisionResult.NEW_CLUSTER
                
            cluster_id = None
            if decision == ClusterDecisionResult.EXISTING_CLUSTER:
                cid_str = data.get("target_cluster_id")
                if cid_str:
                    try:
                        cluster_id = uuid.UUID(cid_str)
                    except ValueError:
                        # Fallback if ID is invalid
                        decision = ClusterDecisionResult.NEW_CLUSTER # Safer fallback? Or Noise?
                        # Let's fallback to noise to prevent contamination
                        decision = ClusterDecisionResult.IGNORE_NOISE
                else:
                    decision = ClusterDecisionResult.IGNORE_NOISE

            return ClusteringResult(
                decision=decision,
                cluster_id=cluster_id,
                new_topic=data.get("new_topic_summary"),
                reasoning=data.get("reasoning"),
                confidence_score=float(data.get("confidence", 0.0))
            )
            
        except json.JSONDecodeError:
            return ClusteringResult(
                decision=ClusterDecisionResult.IGNORE_NOISE,
                reasoning="Failed to parse LLM JSON response"
            )


# Mock implementation for local testing/fallback
class MockLLMProvider(LLMProviderInterface):
    async def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        """Mock behavior: always thinks it's a new cluster unless keywords match."""
        # Simple heuristic for demonstration
        return json.dumps({
            "decision": "NEW_CLUSTER",
            "new_topic_summary": "Extracted Topic from text",
            "reasoning": "Mock execution default",
            "confidence": 0.95
        })
