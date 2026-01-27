import { InMemoryAlertStore } from "./alertStore";
import { evaluateAlerts } from "./alertEngine";
import type { AlertConfig, MarketIntelSnapshot } from "./alertTypes";

const ALERT_CONFIG: AlertConfig = {
  MARKET_SCORE_THRESHOLD: 80,
  HIGH_IMPACT_NEWS_SCORE: 8.5,
  WHALE_NETFLOW_THRESHOLD: 2000,
  COOLDOWN_MINUTES: 30,
};

const store = new InMemoryAlertStore();

function run(s: MarketIntelSnapshot) {
  const { alerts } = evaluateAlerts(s, ALERT_CONFIG, store);
  for (const a of alerts) {
    // Example usage: print alert payload (no integrations here).
    // eslint-disable-next-line no-console
    console.log(JSON.stringify(a));
  }
}

const t0 = Date.now();

run({
  market: { score: 72, bias: "neutral", confidence: 61 },
  news: [],
  whale: { netFlow: 10_000 },
  timestamp: t0,
});

run({
  market: { score: 81, bias: "bullish", confidence: 72 },
  news: [
    { id: "hash_etf_inflow_001", title: "ETF BTC inflow accelerates", score: 9.1, bias: "bullish", confidence: 78 },
  ],
  whale: { netFlow: 10_050 },
  timestamp: t0 + 60_000,
});

run({
  market: { score: 82, bias: "bullish", confidence: 73 },
  news: [
    // Same id => deduped
    { id: "hash_etf_inflow_001", title: "ETF BTC inflow accelerates", score: 9.1, bias: "bullish", confidence: 78 },
    // New high-impact item => eligible (but limited to 1 per cooldown window)
    { id: "hash_macro_002", title: "Macro liquidity surprise", score: 8.6, bias: "neutral", confidence: 65 },
  ],
  whale: { netFlow: 12_500 }, // delta spike => whale alert (subject to cooldown)
  timestamp: t0 + 2 * 60_000,
});

