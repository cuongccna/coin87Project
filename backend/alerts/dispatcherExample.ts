/**
 * Example Dispatch Flow for Coin87 Alert System
 *
 * Demonstrates:
 * 1. Alert Engine evaluation
 * 2. Building contexts from snapshot
 * 3. Dispatching to Telegram
 */

import { evaluateAlerts } from "./alertEngine";
import { InMemoryAlertStore } from "./alertStore";
import type { AlertConfig, MarketIntelSnapshot } from "./alertTypes";
import {
  dispatchAlerts,
  loadDispatchConfig,
  type AlertContext,
  type MarketContext,
  type NewsContext,
  type WhaleContext,
} from "./alertDispatcher";
import { InMemoryDispatcherStore } from "./dispatcherState";

// Example snapshot (would come from backend API)
const exampleSnapshot: MarketIntelSnapshot = {
  market: {
    score: 82,
    bias: "bullish",
    confidence: 72,
  },
  news: [
    {
      id: "news-btc-etf-2026-01-27",
      title: "Major ETF inflow signals institutional accumulation",
      score: 8.7,
      bias: "bullish",
      confidence: 78,
    },
  ],
  whale: {
    netFlow: 2265,
  },
  timestamp: Date.now(),
};

// Alert Engine config
const alertConfig: AlertConfig = {
  MARKET_SCORE_THRESHOLD: 80,
  HIGH_IMPACT_NEWS_SCORE: 8.5,
  WHALE_NETFLOW_THRESHOLD: 2000,
  COOLDOWN_MINUTES: 30,
};

/**
 * Build contexts from snapshot for alert formatting
 */
function buildContexts(
  snapshot: MarketIntelSnapshot,
  asset: string,
): Map<string, AlertContext> {
  const contexts = new Map<string, AlertContext>();

  // Market context
  const marketContext: MarketContext = {
    asset,
    score: snapshot.market.score,
    bias: snapshot.market.bias,
    confidence: snapshot.market.confidence,
  };
  contexts.set("MARKET_STATE_ALERT", marketContext);

  // Whale context
  const whaleContext: WhaleContext = {
    asset,
    netFlow: snapshot.whale.netFlow,
  };
  contexts.set("WHALE_ACTIVITY_ALERT", whaleContext);

  // News contexts (one per news item)
  for (const news of snapshot.news) {
    const newsContext: NewsContext = {
      asset,
      title: news.title,
      bias: news.bias,
      category: "onchain", // Would come from backend
      newsId: news.id,
    };
    // Key by news title (matches alert message content)
    contexts.set(`news:High-impact news score ${news.score.toFixed(1)}.\n${news.title}`, newsContext);
  }

  return contexts;
}

/**
 * Main dispatch flow
 */
async function runDispatchFlow() {
  console.log("=== Coin87 Alert Dispatcher Example ===\n");

  // Initialize stores
  const alertStore = new InMemoryAlertStore();
  const dispatcherStore = new InMemoryDispatcherStore();

  // Load config (from env or defaults)
  const dispatchConfig = loadDispatchConfig();

  // Check if Telegram is configured
  if (!dispatchConfig.telegram.botToken) {
    console.log("⚠️  TELEGRAM_BOT_TOKEN not set. Running in dry-run mode.\n");
  }

  // First run: initialize state (no alerts on startup)
  console.log("1. First evaluation (initializing state)...");
  const result1 = evaluateAlerts(exampleSnapshot, alertConfig, alertStore);
  console.log(`   Alerts generated: ${result1.alerts.length}`);

  // Simulate state change (score crosses threshold)
  const snapshot2: MarketIntelSnapshot = {
    ...exampleSnapshot,
    market: { ...exampleSnapshot.market, score: 85 },
    timestamp: Date.now() + 1000,
  };

  console.log("\n2. Second evaluation (score crossed threshold)...");
  const result2 = evaluateAlerts(snapshot2, alertConfig, alertStore);
  console.log(`   Alerts generated: ${result2.alerts.length}`);

  if (result2.alerts.length > 0) {
    console.log("   Alert types:", result2.alerts.map((a) => a.type).join(", "));

    // Build contexts
    const contexts = buildContexts(snapshot2, "BTC");

    // Dispatch to Telegram
    console.log("\n3. Dispatching to Telegram...");
    const dispatchResults = await dispatchAlerts(
      result2.alerts,
      contexts,
      dispatchConfig,
      dispatcherStore,
    );

    for (const dr of dispatchResults) {
      if (dr.dispatched) {
        console.log(`   ✅ Dispatched: ${dr.alertType}`);
        console.log(`   Message ID: ${dr.telegramResult?.messageId || "N/A"}`);
      } else {
        console.log(`   ❌ Not dispatched: ${dr.alertType}`);
        console.log(`   Reason: ${dr.reason}`);
      }
    }
  }

  // Demonstrate rate limiting
  console.log("\n4. Testing rate limit (immediate re-dispatch)...");
  const result3 = evaluateAlerts(
    { ...snapshot2, timestamp: Date.now() + 2000 },
    alertConfig,
    alertStore,
  );
  console.log(`   Alerts from engine: ${result3.alerts.length}`);

  if (result3.alerts.length > 0) {
    const contexts = buildContexts(snapshot2, "BTC");
    const dispatchResults = await dispatchAlerts(
      result3.alerts,
      contexts,
      dispatchConfig,
      dispatcherStore,
    );

    for (const dr of dispatchResults) {
      console.log(`   ${dr.dispatched ? "✅" : "❌"} ${dr.alertType}: ${dr.reason || "OK"}`);
    }
  } else {
    console.log("   Engine correctly suppressed duplicate alerts.");
  }

  console.log("\n=== Flow Complete ===");
}

// Run if executed directly
runDispatchFlow().catch(console.error);
