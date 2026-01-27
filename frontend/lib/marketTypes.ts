/**
 * Information Reliability Types
 * 
 * Coin87 Core Philosophy:
 * - Does NOT predict price
 * - Does NOT generate trading signals
 * - Evaluates INFORMATION RELIABILITY over time
 */

export type ReliabilityLevel = "high" | "medium" | "low" | "unverified";
export type InformationCategory = "narrative" | "event" | "correction" | "rumor";

export type InformationReliabilityResponse = {
  state: {
    overall_reliability: ReliabilityLevel;
    confirmation_rate: number; // 0–100, % of information confirmed by multiple sources
    contradiction_rate: number; // 0–100, % of information that has been contradicted
    active_narratives_count: number;
  };
  signals: Array<{
    title: string;
    reliability_score: number; // 0–10
    reliability_level: ReliabilityLevel;
    confirmation_count: number; // Number of sources confirming
    persistence_hours: number; // How long this information has persisted
    category: InformationCategory;
    narrative_id?: string;
    // Optional analyst-mode fields (backend-provided)
    breakdown?: {
      source_reliability: number; // 0–100
      cross_confirmation: number; // 0–100
      temporal_persistence: number; // 0–100
    };
    analysis_notes?: string;
  }>;
};

// Legacy aliases for migration - TO BE REMOVED
export type MarketBias = ReliabilityLevel;
export type NewsBias = ReliabilityLevel;
export type NewsCategory = InformationCategory;
export type MarketIntelResponse = InformationReliabilityResponse;

