export type EnvironmentState = "CLEAN" | "CAUTION" | "CONTAMINATED";

export type DecisionEnvironmentResponse = {
  environment_state: EnvironmentState;
  dominant_risks: string[];
  risk_density: number;
  snapshot_time: string; // ISO
  guidance: string;
  data_stale?: boolean;
  staleness_seconds?: number | null;
};

export type DecisionRiskEventResponse = {
  risk_type: string;
  severity: number; // 1..5
  affected_decisions: string[];
  recommended_posture: "IGNORE" | "REVIEW" | "DELAY";
  detected_at: string; // ISO
  time_relevance: { valid_from: string; valid_to: string | null };
};

export type NarrativeResponse = {
  narrative_id: string;
  theme: string;
  saturation_level: number; // 1..5
  status: "ACTIVE" | "FADING" | "DORMANT";
  first_seen_at: string;
  last_seen_at: string;
};

