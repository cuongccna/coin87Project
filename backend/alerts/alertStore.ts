import type { AlertType } from "./alertTypes";

export type MarketBand = "above" | "below";

export type AlertState = {
  // Mandatory persisted items (phase 2)
  lastMarketScoreAlerted: number | null;
  alertedNewsIds: Set<string>;
  lastWhaleAlertAt: number | null;

  // Extra internal state to support deterministic edge triggers (allowed; still in-memory).
  lastMarketBandSeen: MarketBand | null;
  lastWhaleNetFlowSeen: number | null;
  lastAlertAtByType: Map<AlertType, number>;
};

export interface AlertStore {
  getState(): AlertState;
  setState(next: AlertState): void;
}

export function createInitialState(): AlertState {
  return {
    lastMarketScoreAlerted: null,
    alertedNewsIds: new Set<string>(),
    lastWhaleAlertAt: null,
    lastMarketBandSeen: null,
    lastWhaleNetFlowSeen: null,
    lastAlertAtByType: new Map<AlertType, number>(),
  };
}

export class InMemoryAlertStore implements AlertStore {
  private state: AlertState;

  constructor(initial?: Partial<Pick<AlertState, "lastMarketScoreAlerted" | "lastWhaleAlertAt">>) {
    const base = createInitialState();
    this.state = {
      ...base,
      ...initial,
    };
  }

  getState(): AlertState {
    // Return a safe copy to preserve determinism and prevent external mutation.
    return {
      lastMarketScoreAlerted: this.state.lastMarketScoreAlerted,
      alertedNewsIds: new Set(this.state.alertedNewsIds),
      lastWhaleAlertAt: this.state.lastWhaleAlertAt,
      lastMarketBandSeen: this.state.lastMarketBandSeen,
      lastWhaleNetFlowSeen: this.state.lastWhaleNetFlowSeen,
      lastAlertAtByType: new Map(this.state.lastAlertAtByType),
    };
  }

  setState(next: AlertState): void {
    // Store a defensive copy.
    this.state = {
      lastMarketScoreAlerted: next.lastMarketScoreAlerted,
      alertedNewsIds: new Set(next.alertedNewsIds),
      lastWhaleAlertAt: next.lastWhaleAlertAt,
      lastMarketBandSeen: next.lastMarketBandSeen,
      lastWhaleNetFlowSeen: next.lastWhaleNetFlowSeen,
      lastAlertAtByType: new Map(next.lastAlertAtByType),
    };
  }
}

