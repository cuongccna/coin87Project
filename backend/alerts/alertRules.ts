import type { Alert, AlertConfig, AlertType, MarketIntelSnapshot } from "./alertTypes";
import type { AlertState, MarketBand } from "./alertStore";

function minutesToMs(m: number) {
  return Math.max(0, Math.floor(m * 60_000));
}

function isCoolingDown(state: AlertState, type: AlertType, now: number, cooldownMinutes: number): boolean {
  const last = state.lastAlertAtByType.get(type);
  if (last == null) return false;
  return now - last < minutesToMs(cooldownMinutes);
}

function marketBand(score: number, threshold: number): MarketBand {
  return score >= threshold ? "above" : "below";
}

function clampScore10(v: number): number {
  if (!Number.isFinite(v)) return 0;
  return Math.max(0, Math.min(10, v));
}

function formatTwoLines(line1: string, line2?: string): string {
  if (!line2) return line1;
  return `${line1}\n${line2}`;
}

export function evalMarketStateAlert(
  snapshot: MarketIntelSnapshot,
  config: AlertConfig,
  state: AlertState,
): { alert: Alert | null; nextState: AlertState } {
  const now = snapshot.timestamp;
  const threshold = config.MARKET_SCORE_THRESHOLD;
  const currentBand = marketBand(snapshot.market.score, threshold);

  // Initialize band without alert on the first observation to avoid "startup spam".
  if (state.lastMarketBandSeen == null) {
    const next: AlertState = { ...state, lastMarketBandSeen: currentBand };
    return { alert: null, nextState: next };
  }

  const prevBand = state.lastMarketBandSeen;
  const crossed = prevBand !== currentBand;

  // Always update the seen band deterministically.
  let next: AlertState = { ...state, lastMarketBandSeen: currentBand };

  if (!crossed) return { alert: null, nextState: next };
  if (isCoolingDown(state, "MARKET_STATE_ALERT", now, config.COOLDOWN_MINUTES)) return { alert: null, nextState: next };

  const direction = currentBand === "above" ? "crossed above" : "crossed below";
  const title = "Market state threshold crossed";
  const message = formatTwoLines(
    `Market score ${direction} ${threshold}.`,
    `Bias is ${snapshot.market.bias} with ${snapshot.market.confidence}% confidence.`,
  );

  const alert: Alert = {
    type: "MARKET_STATE_ALERT",
    severity: "medium",
    title,
    message,
    score: snapshot.market.score,
    createdAt: now,
  };

  next = {
    ...next,
    lastMarketScoreAlerted: snapshot.market.score,
    lastAlertAtByType: new Map(next.lastAlertAtByType).set("MARKET_STATE_ALERT", now),
  };

  return { alert, nextState: next };
}

export function evalHighImpactNewsAlert(
  snapshot: MarketIntelSnapshot,
  config: AlertConfig,
  state: AlertState,
): { alerts: Alert[]; nextState: AlertState } {
  const now = snapshot.timestamp;
  const threshold = config.HIGH_IMPACT_NEWS_SCORE;

  // Deterministic: stable filter + sort by score desc, tie by id.
  const candidates = snapshot.news
    .map((n) => ({ ...n, score: clampScore10(n.score) }))
    .filter((n) => n.score >= threshold)
    .sort((a, b) => (b.score !== a.score ? b.score - a.score : a.id.localeCompare(b.id)));

  const nextAlerted = new Set(state.alertedNewsIds);
  const out: Alert[] = [];

  for (const n of candidates) {
    if (nextAlerted.has(n.id)) continue;
    if (isCoolingDown(state, "HIGH_IMPACT_NEWS_ALERT", now, config.COOLDOWN_MINUTES)) break;

    // Alert once per news item (id must be backend hash: title+source+timestamp).
    nextAlerted.add(n.id);
    out.push({
      type: "HIGH_IMPACT_NEWS_ALERT",
      severity: "high",
      title: "High impact news signal",
      message: formatTwoLines(`High-impact news score ${n.score.toFixed(1)}.`, n.title),
      score: n.score,
      createdAt: now,
    });

    // Strict fatigue control: at most 1 news alert per cooldown window.
    break;
  }

  const next: AlertState = {
    ...state,
    alertedNewsIds: nextAlerted,
    lastAlertAtByType: out.length
      ? new Map(state.lastAlertAtByType).set("HIGH_IMPACT_NEWS_ALERT", now)
      : new Map(state.lastAlertAtByType),
  };

  return { alerts: out, nextState: next };
}

export function evalWhaleActivityAlert(
  snapshot: MarketIntelSnapshot,
  config: AlertConfig,
  state: AlertState,
): { alert: Alert | null; nextState: AlertState } {
  const now = snapshot.timestamp;
  const threshold = config.WHALE_NETFLOW_THRESHOLD;
  const current = snapshot.whale.netFlow;
  const prev = state.lastWhaleNetFlowSeen;

  // Always update seen value.
  let next: AlertState = { ...state, lastWhaleNetFlowSeen: current };

  if (prev == null) return { alert: null, nextState: next };

  const delta = current - prev;
  const spike = Math.abs(delta) >= threshold;
  if (!spike) return { alert: null, nextState: next };

  // Whale alert uses the mandatory whale-specific timestamp + per-type cooldown.
  const whaleCooldownMs = minutesToMs(config.COOLDOWN_MINUTES);
  if (state.lastWhaleAlertAt != null && now - state.lastWhaleAlertAt < whaleCooldownMs) {
    return { alert: null, nextState: next };
  }
  if (isCoolingDown(state, "WHALE_ACTIVITY_ALERT", now, config.COOLDOWN_MINUTES)) {
    return { alert: null, nextState: next };
  }

  const direction = delta > 0 ? "inflow spike" : "outflow spike";
  const title = "Whale activity spike";
  const message = formatTwoLines(
    `Whale net flow ${direction}: Δ ${delta.toFixed(0)}.`,
    `Threshold: ${threshold}.`,
  );

  const alert: Alert = {
    type: "WHALE_ACTIVITY_ALERT",
    severity: "high",
    title,
    message,
    createdAt: now,
  };

  next = {
    ...next,
    lastWhaleAlertAt: now,
    lastAlertAtByType: new Map(next.lastAlertAtByType).set("WHALE_ACTIVITY_ALERT", now),
  };

  return { alert, nextState: next };
}

