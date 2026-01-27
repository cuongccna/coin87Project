import type { Alert, AlertConfig, MarketIntelSnapshot } from "./alertTypes";
import type { AlertStore } from "./alertStore";
import { evalHighImpactNewsAlert, evalMarketStateAlert, evalWhaleActivityAlert } from "./alertRules";

export type AlertEngineResult = {
  alerts: Alert[];
};

/**
 * Deterministic, backend-driven alert evaluation.
 *
 * - Stateless function + external store.
 * - Edge-triggered (threshold crossings / first-seen high-impact news / whale delta spikes).
 * - Rate-limited + deduplicated.
 * - No side effects except store writes.
 */
export function evaluateAlerts(
  snapshot: MarketIntelSnapshot,
  config: AlertConfig,
  store: AlertStore,
): AlertEngineResult {
  const state0 = store.getState();

  // Deterministic order: market -> whale -> news (so "state" changes can be prioritized).
  const out: Alert[] = [];

  const m = evalMarketStateAlert(snapshot, config, state0);
  if (m.alert) out.push(m.alert);

  const w = evalWhaleActivityAlert(snapshot, config, m.nextState);
  if (w.alert) out.push(w.alert);

  const n = evalHighImpactNewsAlert(snapshot, config, w.nextState);
  out.push(...n.alerts);

  // Persist final state.
  store.setState(n.nextState);

  return { alerts: out };
}

