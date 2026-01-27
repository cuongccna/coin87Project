import type {
  DecisionEnvironmentResponse,
  DecisionRiskEventResponse,
  NarrativeResponse,
  NarrativeDetailResponse,
  DecisionHistoryItemResponse,
} from "./types";
import type { InformationReliabilityResponse } from "./marketTypes";

const API_BASE_URL = process.env.C87_API_BASE_URL;
const API_TOKEN = process.env.C87_UI_BEARER_TOKEN;

function assertEnv() {
  if (!API_BASE_URL) throw new Error("Missing env C87_API_BASE_URL (set in frontend/.env.local).");
  if (!API_TOKEN) throw new Error("Missing env C87_UI_BEARER_TOKEN (set in frontend/.env.local).");
}

type FetchOpts = { revalidateSeconds?: number };

async function apiGet<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  assertEnv();
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${API_TOKEN}`,
      "Content-Type": "application/json",
      "X-Request-Id": crypto.randomUUID(),
    },
    next: { revalidate: opts.revalidateSeconds ?? 300 },
  });

  if (!res.ok) throw new Error(`HTTP_${res.status}`);
  return (await res.json()) as T;
}

export const api = {
  getDecisionEnvironment: (revalidateSeconds?: number) =>
    apiGet<DecisionEnvironmentResponse>("/v1/decision/environment", {
      revalidateSeconds,
    }),

  getDecisionEnvironmentAt: (isoTimestamp: string, revalidateSeconds?: number) =>
    apiGet<DecisionEnvironmentResponse>(
      `/v1/decision/environment/${encodeURIComponent(isoTimestamp)}`,
      { revalidateSeconds },
    ),

  listRiskEvents: (
    params: { min_severity?: number; decision_type?: string; at_time?: string },
    revalidateSeconds?: number,
  ) => {
    const q = new URLSearchParams();
    if (params.min_severity != null) q.set("min_severity", String(params.min_severity));
    if (params.decision_type) q.set("decision_type", params.decision_type);
    if (params.at_time) q.set("at_time", params.at_time);
    return apiGet<DecisionRiskEventResponse[]>(
      `/v1/decision/risk-events?${q.toString()}`,
      { revalidateSeconds },
    );
  },

  listNarratives: (
    params: { min_saturation?: number; active_only?: boolean },
    revalidateSeconds?: number,
  ) => {
    const q = new URLSearchParams();
    if (params.min_saturation != null) q.set("min_saturation", String(params.min_saturation));
    if (params.active_only != null) q.set("active_only", params.active_only ? "true" : "false");
    return apiGet<NarrativeResponse[]>(`/v1/decision/narratives?${q.toString()}`, {
      revalidateSeconds,
    });
  },

  getNarrative: (id: string, revalidateSeconds?: number) =>
    apiGet<NarrativeDetailResponse>(`/v1/decision/narratives/${encodeURIComponent(id)}`, {
      revalidateSeconds,
    }),

  listDecisionHistory: (
    params: { start_time: string; end_time: string },
    revalidateSeconds?: number,
  ) => {
    const q = new URLSearchParams(params);
    return apiGet<DecisionHistoryItemResponse[]>(`/v1/decision/history?${q.toString()}`, {
      revalidateSeconds,
    });
  },

  getDecisionHistoryItem: (contextId: string, revalidateSeconds?: number) =>
    apiGet<DecisionHistoryItemResponse>(`/v1/decision/history/${encodeURIComponent(contextId)}`, {
      revalidateSeconds,
    }),

  getNarrativeDetail: (id: string, revalidateSeconds?: number) =>
    apiGet<NarrativeDetailResponse>(`/v1/decision/narratives/${encodeURIComponent(id)}`, {
      revalidateSeconds,
    }),

  /**
   * Fetches the market intelligence reliability assessment for the dashboard.
   */
  getInformationReliability: (asset: string, revalidateSeconds?: number) =>
    apiGet<InformationReliabilityResponse>(`/v1/market/intel?asset=${encodeURIComponent(asset)}`, {
      revalidateSeconds,
    }),
};

