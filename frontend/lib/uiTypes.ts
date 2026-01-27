export type ReliabilityStatus = "STRONG" | "MODERATE" | "WEAK" | "NOISE";
export type NarrativeState = "EMERGING" | "ACTIVE" | "SATURATED" | "FADING" | "DORMANT";

export interface NarrativeExplanation {
  consensus_level: "high" | "medium" | "low";
  source_diversity: "broad" | "limited" | "single";
  is_steady: boolean; // True if information has persisted/stabilized
  has_contradictions: boolean;
}

export interface NarrativeSummary {
  id: string;
  topic: string;
  state: NarrativeState;
  last_updated: string; // ISO
  first_seen_at: string; // ISO
  reliability_score: number; // 0-10 (internal use for sorting)
  reliability_label: ReliabilityStatus;
  is_ignored?: boolean; // Phase 7 Output: Explicitly suppressed/deprioritized
  explanation_metadata?: NarrativeExplanation;
}

export interface ClusterItem {
  id: string;
  summary: string;
  source_count: number;
  reliability: ReliabilityStatus;
  timestamp: string;
}

export interface HomeSnapshot {
  active_narratives_count: number;
  clarity_score: number; // 0-100
  last_updated_at: string;
}
