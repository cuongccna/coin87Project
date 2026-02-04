"""AI Summarizer - Tóm tắt và phân tích nội dung sử dụng Google Gemini.

Không mock dữ liệu - tất cả phải thực tế.
Model configurable qua .env.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import json

import google.generativeai as genai

logger = logging.getLogger("coin87.ingestion.ai")


@dataclass
class ContentAnalysis:
    """Kết quả phân tích nội dung từ AI."""
    summary: str  # Tóm tắt 200 chars
    entities: List[str]  # Entities quan trọng (tokens, protocols, people, orgs)
    sentiment: str  # bullish|bearish|neutral
    confidence: float  # 0.0 - 1.0
    keywords: List[str]  # Keywords chính
    category: str  # Loại tin: regulation|technology|market|security|other
    reasoning: Optional[str] = None  # AI reasoning (debug)
    # Expectation Gap fields
    expected_mechanism: Optional[str] = None  # "Spot CVD spike > 5M within 1 hour"
    invalidation_signal: Optional[str] = None # "Price pumps but Open Interest drops"
    trapped_persona: Optional[str] = None     # "Late FOMO buyers"


class GeminiSummarizer:
    """Summarizer sử dụng Google Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        Initialize Gemini summarizer.
        
        Args:
            api_key: Gemini API key (default từ env GEMINI_API_KEY)
            model_name: Model name (default từ env GEMINI_MODEL hoặc 'gemini-1.5-flash')
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
        logger.info(f"Initialized Gemini summarizer with model: {self.model_name}")
    
    def analyze(
        self,
        title: str,
        content_text: str,
        url: Optional[str] = None,
        source_name: Optional[str] = None,
    ) -> ContentAnalysis:
        """
        Phân tích nội dung và trả về structured insights.
        
        Args:
            title: Title của bài viết
            content_text: Full text content
            url: Canonical URL (optional, for context)
            source_name: Tên source (optional, for context)
            
        Returns:
            ContentAnalysis với summary, entities, sentiment, etc.
        """
        # Truncate content nếu quá dài (Gemini có token limit)
        max_content_chars = 8000  # Conservative limit
        if len(content_text) > max_content_chars:
            content_text = content_text[:max_content_chars] + "..."
            logger.debug(f"Truncated content to {max_content_chars} chars")
        
        # Build prompt
        prompt = self._build_analysis_prompt(title, content_text, url, source_name)
        
        try:
            # Call Gemini API
            response = self.model.generate_content(prompt)
            
            if not response.text:
                logger.error("Gemini returned empty response")
                return self._fallback_analysis(title, content_text)
            
            # Parse structured response
            analysis = self._parse_response(response.text, title, content_text)
            return analysis
            
        except Exception as e:
            logger.exception(f"Gemini API error: {e}")
            return self._fallback_analysis(title, content_text)
    
    def _build_analysis_prompt(
        self,
        title: str,
        content: str,
        url: Optional[str],
        source: Optional[str],
    ) -> str:
        """Build structured prompt for Gemini."""
        context = ""
        if source:
            context += f"Source: {source}\n"
        if url:
            context += f"URL: {url}\n"
        
        prompt = f"""Analyze this crypto news article and provide structured insights.

{context}
Title: {title}

Content:
{content}

Provide your analysis in the following JSON format (strictly follow this structure):

{{
  "summary": "A concise 200-character summary of the key information",
  "entities": ["List", "of", "key", "entities", "tokens", "protocols", "people", "organizations"],
  "sentiment": "bullish|bearish|neutral",
  "confidence": 0.85,
  "keywords": ["key", "topics", "from", "article"],
  "category": "regulation|technology|market|security|other",
  "reasoning": "Brief explanation of your sentiment assessment",
  "expected_mechanism": "What MUST happen on-chain if this news is genuine? e.g., 'Spot CVD spike > 5M within 1 hour'",
  "invalidation_signal": "Signs that this is a trap/fakeout? e.g., 'Price pumps but Open Interest drops (Short covering only)'",
  "trapped_persona": "Who is likely to be trapped? e.g., 'Late FOMO buyers', 'Panic sellers'"
}}

Rules:
- summary: Max 200 chars, factual, no hype
- entities: Extract token names (BTC, ETH), protocols (Ethereum, Solana), key people/orgs
- sentiment: bullish (positive for crypto), bearish (negative), neutral
- confidence: 0.0-1.0 based on clarity and factual content
- keywords: 3-8 main topics
- category: Pick ONE most relevant category
- reasoning: 1-2 sentences explaining sentiment
- expected_mechanism: 1 sentence describing expected market reaction if true
- invalidation_signal: 1 sentence describing confirmation failure (the trap)
- trapped_persona: 1 short phrase identifying the victim of market inefficiency

Return ONLY the JSON, no additional text."""

        return prompt
    
    def _parse_response(self, response_text: str, title: str, content: str) -> ContentAnalysis:
        """Parse Gemini JSON response."""
        try:
            # Extract JSON from response (có thể có markdown code blocks)
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON directly
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No JSON found in response")
            
            data = json.loads(json_str)
            
            # Validate and extract fields
            return ContentAnalysis(
                summary=data.get("summary", title[:200])[:200],  # Ensure max 200 chars
                entities=data.get("entities", [])[:20],  # Max 20 entities
                sentiment=data.get("sentiment", "neutral"),
                confidence=max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
                keywords=data.get("keywords", [])[:10],  # Max 10 keywords
                category=data.get("category", "other"),
                reasoning=data.get("reasoning"),
                expected_mechanism=data.get("expected_mechanism"),
                invalidation_signal=data.get("invalidation_signal"),
                trapped_persona=data.get("trapped_persona"),
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse Gemini response: {e}. Response: {response_text[:500]}")
            return self._fallback_analysis(title, content)
    
    def _fallback_analysis(self, title: str, content: str) -> ContentAnalysis:
        """Fallback analysis nếu AI fails - heuristic-based."""
        logger.info("Using fallback heuristic analysis")
        
        # Simple keyword extraction
        words = re.findall(r'\b[A-Z][A-Za-z]+\b', content[:2000])  # Capitalized words
        entities = list(set(words))[:10]
        
        # Simple sentiment from keywords
        bullish_words = ["surge", "rally", "adoption", "growth", "bullish", "positive", "approval"]
        bearish_words = ["crash", "hack", "exploit", "ban", "lawsuit", "bearish", "negative", "decline"]
        
        content_lower = content.lower()
        bullish_count = sum(1 for w in bullish_words if w in content_lower)
        bearish_count = sum(1 for w in bearish_words if w in content_lower)
        
        if bullish_count > bearish_count:
            sentiment = "bullish"
            confidence = min(0.6, 0.3 + 0.1 * bullish_count)
        elif bearish_count > bullish_count:
            sentiment = "bearish"
            confidence = min(0.6, 0.3 + 0.1 * bearish_count)
        else:
            sentiment = "neutral"
            confidence = 0.4
        
        return ContentAnalysis(
            summary=title[:200],
            entities=entities,
            sentiment=sentiment,
            confidence=confidence,
            keywords=[],
            category="other",
            reasoning="Fallback heuristic analysis (AI unavailable)",
            expected_mechanism=None,
            invalidation_signal=None,
            trapped_persona=None,
        )


# Singleton instance
_summarizer_instance: Optional[GeminiSummarizer] = None


def get_summarizer() -> GeminiSummarizer:
    """Get singleton summarizer instance."""
    global _summarizer_instance
    if _summarizer_instance is None:
        _summarizer_instance = GeminiSummarizer()
    return _summarizer_instance
