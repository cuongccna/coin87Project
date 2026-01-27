/**
 * Alert Dispatcher for Coin87
 *
 * Connects Alert Engine output → Telegram delivery
 *
 * Rules:
 * - Global cooldown: 30 minutes (configurable)
 * - Same alert type cannot fire twice within cooldown
 * - Same news ID cannot be dispatched twice EVER
 * - Max 1 alert dispatched per evaluation cycle
 */

declare const process: { env: Record<string, string | undefined> };

import type { Alert, AlertType } from "./alertTypes";
import type { DispatcherStateStore } from "./dispatcherState";
import type { TelegramConfig, SendResult } from "./telegramClient";
import { sendTelegramMessage } from "./telegramClient";

// Allowed alert types (locked)
const ALLOWED_TYPES: Set<AlertType> = new Set([
  "MARKET_STATE_ALERT",
  "HIGH_IMPACT_NEWS_ALERT",
  "WHALE_ACTIVITY_ALERT",
]);

export type DispatchConfig = {
  cooldownMinutes: number;
  telegram: TelegramConfig;
};

export type DispatchResult = {
  dispatched: boolean;
  alertType?: AlertType;
  telegramResult?: SendResult;
  reason?: string;
};

// Category-based Key Risk templates (must match UI exactly)
const KEY_RISK_TEMPLATES: Record<string, string[]> = {
  MARKET_STATE_ALERT: [
    "Momentum may weaken if volume does not follow.",
    "Score crossing may be temporary without confirmation.",
  ],
  HIGH_IMPACT_NEWS_ALERT_sentiment: [
    "Crowded positioning may reduce follow-through.",
    "Sentiment strength lacks volume confirmation.",
  ],
  HIGH_IMPACT_NEWS_ALERT_macro: [
    "Policy uncertainty may increase short-term volatility.",
    "Macro headline risk could reverse direction quickly.",
  ],
  HIGH_IMPACT_NEWS_ALERT_onchain: [
    "Large flows may reflect positioning rather than conviction.",
    "On-chain activity could be short-term rebalancing.",
  ],
  WHALE_ACTIVITY_ALERT: [
    "Large flows may reflect short-term positioning.",
    "Whale activity does not guarantee directional move.",
  ],
};

function getKeyRisk(alert: Alert, category?: string): string {
  const key = category
    ? `${alert.type}_${category}`
    : alert.type;

  const templates = KEY_RISK_TEMPLATES[key] || KEY_RISK_TEMPLATES[alert.type];
  if (!templates || templates.length === 0) {
    return "Monitor for confirmation before acting.";
  }

  // Deterministic selection based on score
  const idx = Math.floor((alert.score || 0) * 10) % templates.length;
  return templates[idx];
}

function formatUtcTime(epochMs: number): string {
  const d = new Date(epochMs);
  const yyyy = d.getUTCFullYear();
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const min = String(d.getUTCMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd} ${hh}:${min} UTC`;
}

function formatNumber(n: number): string {
  if (n >= 0) return `+${n.toLocaleString("en-US")}`;
  return n.toLocaleString("en-US");
}

function capitalize(s: string): string {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

/**
 * Format MARKET_STATE_ALERT for Telegram
 */
function formatMarketStateAlert(alert: Alert, context: MarketContext): string {
  const keyRisk = getKeyRisk(alert);
  const time = formatUtcTime(alert.createdAt);

  return `🚨 COIN87 ALERT

Market state shift detected

Market: ${context.asset}
Score crossed: ${context.score}
Bias: ${capitalize(context.bias)}
Confidence: ${context.confidence}%

Key risk:
${keyRisk}

Time: ${time}`;
}

/**
 * Format HIGH_IMPACT_NEWS_ALERT for Telegram
 */
function formatHighImpactNewsAlert(alert: Alert, context: NewsContext): string {
  const keyRisk = getKeyRisk(alert, context.category);
  const time = formatUtcTime(alert.createdAt);

  return `🚨 COIN87 ALERT

High-impact market signal

${context.title}

Market: ${context.asset}
Impact: HIGH
Bias: ${capitalize(context.bias)}

Key risk:
${keyRisk}

Time: ${time}`;
}

/**
 * Format WHALE_ACTIVITY_ALERT for Telegram
 */
function formatWhaleActivityAlert(alert: Alert, context: WhaleContext): string {
  const keyRisk = getKeyRisk(alert);
  const time = formatUtcTime(alert.createdAt);

  return `🚨 COIN87 ALERT

Whale activity spike detected

Market: ${context.asset}
Net flow: ${formatNumber(context.netFlow)} ${context.asset}

Key risk:
${keyRisk}

Time: ${time}`;
}

// Context types for formatting
export type MarketContext = {
  asset: string;
  score: number;
  bias: string;
  confidence: number;
};

export type NewsContext = {
  asset: string;
  title: string;
  bias: string;
  category?: string;
  newsId: string;
};

export type WhaleContext = {
  asset: string;
  netFlow: number;
};

export type AlertContext = MarketContext | NewsContext | WhaleContext;

function isNewsContext(ctx: AlertContext): ctx is NewsContext {
  return "newsId" in ctx;
}

function isWhaleContext(ctx: AlertContext): ctx is WhaleContext {
  return "netFlow" in ctx;
}

/**
 * Format alert message for Telegram based on type
 */
function formatAlertMessage(alert: Alert, context: AlertContext): string {
  switch (alert.type) {
    case "MARKET_STATE_ALERT":
      return formatMarketStateAlert(alert, context as MarketContext);
    case "HIGH_IMPACT_NEWS_ALERT":
      return formatHighImpactNewsAlert(alert, context as NewsContext);
    case "WHALE_ACTIVITY_ALERT":
      return formatWhaleActivityAlert(alert, context as WhaleContext);
    default:
      throw new Error(`Unknown alert type: ${alert.type}`);
  }
}

/**
 * Dispatch a single alert to Telegram
 *
 * - Validates alert type
 * - Checks rate limits and deduplication
 * - Formats message
 * - Sends via Telegram client
 * - Records dispatch state
 */
export async function dispatchAlert(
  alert: Alert,
  context: AlertContext,
  config: DispatchConfig,
  store: DispatcherStateStore,
): Promise<DispatchResult> {
  const now = Date.now();
  const cooldownMs = config.cooldownMinutes * 60 * 1000;

  // Validate alert type
  if (!ALLOWED_TYPES.has(alert.type)) {
    return {
      dispatched: false,
      reason: `Alert type not allowed: ${alert.type}`,
    };
  }

  // Check rate limit
  if (!store.canDispatch(alert.type, now, cooldownMs)) {
    return {
      dispatched: false,
      alertType: alert.type,
      reason: "Rate limited (cooldown active)",
    };
  }

  // Check news deduplication
  if (alert.type === "HIGH_IMPACT_NEWS_ALERT" && isNewsContext(context)) {
    if (store.isNewsDispatched(context.newsId)) {
      return {
        dispatched: false,
        alertType: alert.type,
        reason: `News already dispatched: ${context.newsId}`,
      };
    }
  }

  // Format message
  const message = formatAlertMessage(alert, context);

  // Send to Telegram
  const telegramResult = await sendTelegramMessage(config.telegram, message);

  if (!telegramResult.ok) {
    return {
      dispatched: false,
      alertType: alert.type,
      telegramResult,
      reason: `Telegram send failed: ${telegramResult.error}`,
    };
  }

  // Record successful dispatch
  const newsId = isNewsContext(context) ? context.newsId : undefined;
  store.recordDispatch(alert.type, now, newsId);

  return {
    dispatched: true,
    alertType: alert.type,
    telegramResult,
  };
}

/**
 * Dispatch alerts from Alert Engine output
 *
 * - Processes at most 1 alert per call (strict fatigue control)
 * - Priority: MARKET_STATE_ALERT > WHALE_ACTIVITY_ALERT > HIGH_IMPACT_NEWS_ALERT
 */
export async function dispatchAlerts(
  alerts: Alert[],
  contexts: Map<string, AlertContext>,
  config: DispatchConfig,
  store: DispatcherStateStore,
): Promise<DispatchResult[]> {
  const results: DispatchResult[] = [];

  // Sort by priority (market > whale > news)
  const priorityOrder: AlertType[] = [
    "MARKET_STATE_ALERT",
    "WHALE_ACTIVITY_ALERT",
    "HIGH_IMPACT_NEWS_ALERT",
  ];

  const sortedAlerts = [...alerts].sort((a, b) => {
    const aIdx = priorityOrder.indexOf(a.type);
    const bIdx = priorityOrder.indexOf(b.type);
    return aIdx - bIdx;
  });

  // Dispatch at most 1 alert
  for (const alert of sortedAlerts) {
    const contextKey = alert.type === "HIGH_IMPACT_NEWS_ALERT"
      ? `news:${alert.message}` // Use message which contains title
      : alert.type;

    const context = contexts.get(contextKey) || contexts.get(alert.type);

    if (!context) {
      results.push({
        dispatched: false,
        alertType: alert.type,
        reason: "Missing context for alert",
      });
      continue;
    }

    const result = await dispatchAlert(alert, context, config, store);
    results.push(result);

    // Stop after first successful dispatch (strict fatigue control)
    if (result.dispatched) {
      break;
    }
  }

  return results;
}

/**
 * Load dispatch config from environment
 */
export function loadDispatchConfig(): DispatchConfig {
  const cooldownMinutes = parseInt(
    process.env.ALERT_COOLDOWN_MINUTES || "30",
    10
  );

  return {
    cooldownMinutes: Number.isFinite(cooldownMinutes) ? cooldownMinutes : 30,
    telegram: {
      botToken: process.env.TELEGRAM_BOT_TOKEN || "",
      channelId: process.env.TELEGRAM_CHANNEL_ID || "",
    },
  };
}
