import "server-only";

import type { MarketIntelResponse } from "./marketTypes";
import { headers } from "next/headers";

const API_TOKEN = process.env.C87_UI_BEARER_TOKEN;
const MARKET_INTEL_URL = process.env.C87_MARKET_INTEL_URL;
const API_BASE_URL = process.env.C87_API_BASE_URL;

function requestOrigin(): string | null {
  try {
    const h = headers();
    const host = h.get("x-forwarded-host") ?? h.get("host");
    if (!host) return null;
    const proto = h.get("x-forwarded-proto") ?? "http";
    return `${proto}://${host}`;
  } catch {
    return null;
  }
}

function buildMarketIntelUrl(asset: string) {
  // Prefer explicit backend URL.
  const base = MARKET_INTEL_URL ?? (API_BASE_URL ? `${API_BASE_URL.replace(/\/$/, "")}/v1/market/intel` : null);
  if (base) {
    const u = new URL(base);
    u.searchParams.set("asset", asset);
    
    return u.toString();
  }

  // Local dev fallback: Next.js route handler (still backend-driven JSON; no frontend scoring).
  const path = `/api/market/intel?asset=${encodeURIComponent(asset)}`;
  return path;
  return path;
}

export async function fetchMarketIntel(asset: string, revalidateSeconds = 60): Promise<MarketIntelResponse> {
  const u = buildMarketIntelUrl(asset);
  const url = u.startsWith("/") ? `${requestOrigin() ?? "http://localhost:3000"}${u}` : u;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (API_TOKEN) headers.Authorization = `Bearer ${API_TOKEN}`;

  const controller = new AbortController();
  const timeoutMs = Number.parseInt(process.env.C87_MARKET_INTEL_TIMEOUT_MS ?? "8000", 10);
  const timeout = setTimeout(() => controller.abort(), Number.isFinite(timeoutMs) ? timeoutMs : 8000);

  const res = await fetch(url, {
    method: "GET",
    headers,
    next: { revalidate: revalidateSeconds },
    signal: controller.signal,
  });
  clearTimeout(timeout);
  if (!res.ok) throw new Error(`HTTP_${res.status}`);
  return (await res.json()) as MarketIntelResponse;
}

