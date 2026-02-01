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

export type NarrativeDetailResponse = NarrativeResponse & {
  linked_risks: Array<{
    risk_type: string;
    severity: number;
    recommended_posture: "IGNORE" | "REVIEW" | "DELAY";
    valid_from: string;
    valid_to: string | null;
    occurrence_count: number;
  }>;
};

export type DecisionHistoryItemResponse = {
  context: {
    context_id: string;
    context_type: string;
    context_time: string;
    description: string | null;
  };
  decision_environment_at_time: DecisionEnvironmentResponse | null;
  impacts: Array<{
    recorded_at: string;
    environment_snapshot_id: string | null;
    qualitative_outcome: string;
    learning_flags: string[];
  }>;
};
