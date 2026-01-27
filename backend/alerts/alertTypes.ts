export type AlertType = "MARKET_STATE_ALERT" | "HIGH_IMPACT_NEWS_ALERT" | "WHALE_ACTIVITY_ALERT";

export type AlertSeverity = "high" | "medium";

export type MarketBias = "bullish" | "bearish" | "neutral";

// LOCKED input schema (do not change)
export type MarketIntelSnapshot = {
  market: {
    score: number;
    bias: MarketBias;
    confidence: number;
  };
  news: Array<{
    id: string; // backend-provided unique hash (e.g., title+source+timestamp)
    title: string;
    score: number;
    bias: string;
    confidence: number;
  }>;
  whale: {
    netFlow: number;
  };
  timestamp: number; // epoch ms
};

// Configurable thresholds (do not hard-code elsewhere)
export type AlertConfig = {
  MARKET_SCORE_THRESHOLD: number; // e.g. 80
  HIGH_IMPACT_NEWS_SCORE: number; // e.g. 8.5
  WHALE_NETFLOW_THRESHOLD: number; // e.g. 2000 (delta)
  COOLDOWN_MINUTES: number; // e.g. 30
};

export type Alert = {
  type: AlertType;
  severity: AlertSeverity;
  title: string;
  message: string; // max 2 lines
  score?: number;
  createdAt: number; // epoch ms
};

