import { NextResponse } from "next/server";

// Locked data contract for Alert Engine (Phase 2) and compatible with dashboard rendering.
type MarketIntelSnapshot = {
  market: { score: number; bias: "bullish" | "bearish" | "neutral"; confidence: number };
  news: Array<{ id: string; title: string; score: number; bias: string; confidence: number }>;
  whale: { netFlow: number };
  timestamp: number;
};

function buildSnapshot(asset: string): MarketIntelSnapshot {
  const now = Date.now();

  if (asset === "BTC") {
    return {
      market: { score: 78, bias: "bullish", confidence: 72 },
      news: [
        { id: "btc_etf_inflow_001", title: "ETF BTC inflow +$1.2B", score: 9.1, bias: "bullish", confidence: 78 },
        { id: "btc_funding_002", title: "Funding rate stabilizes after squeeze", score: 6.9, bias: "neutral", confidence: 61 },
        { id: "btc_macro_003", title: "Macro liquidity conditions tighten", score: 8.6, bias: "bearish", confidence: 66 },
        { id: "btc_sentiment_004", title: "Sentiment resets; risk of crowded positioning", score: 6.2, bias: "neutral", confidence: 58 }
      ],
      whale: { netFlow: 10500 },
      timestamp: now,
    };
  }

  if (asset === "ETH") {
    return {
      market: { score: 64, bias: "neutral", confidence: 60 },
      news: [
        { id: "eth_l2_001", title: "L2 activity shifts; fees normalize", score: 6.8, bias: "neutral", confidence: 59 },
        { id: "eth_staking_002", title: "Staking flows steady; limited near-term pressure", score: 7.2, bias: "neutral", confidence: 62 },
        { id: "eth_reg_003", title: "Regulatory headline introduces short-term uncertainty", score: 8.7, bias: "bearish", confidence: 67 }
      ],
      whale: { netFlow: 4200 },
      timestamp: now,
    };
  }

  // MARKET
  return {
    market: { score: 72, bias: "neutral", confidence: 63 },
    news: [
      { id: "mkt_liquidity_001", title: "Liquidity conditions shift; volatility regime risk", score: 8.5, bias: "neutral", confidence: 65 },
      { id: "mkt_macro_002", title: "Macro surprise increases cross-asset correlation", score: 8.9, bias: "bearish", confidence: 70 },
      { id: "mkt_sentiment_003", title: "Sentiment reverts toward neutral", score: 6.3, bias: "neutral", confidence: 56 }
    ],
    whale: { netFlow: 9800 },
    timestamp: now,
  };
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const asset = (searchParams.get("asset") ?? "MARKET").toUpperCase();

  const snapshot = buildSnapshot(asset);
  return NextResponse.json(snapshot, {
    headers: { "Cache-Control": "no-store" },
  });
}

