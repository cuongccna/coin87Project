import type {
  DecisionEnvironmentResponse,
  DecisionRiskEventResponse,
  NarrativeResponse,
  NarrativeDetailResponse,
  DecisionHistoryItemResponse,
} from "./types";
import type { InformationReliabilityResponse } from "./marketTypes";

/* Always use public env in App Router runtime */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL!;
const API_TOKEN = process.env.NEXT_PUBLIC_UI_BEARER_TOKEN!;

type FetchOpts = { revalidateSeconds?: number };

async function apiGet<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  if (!API_BASE_URL || !API_TOKEN) {
    throw new Error("Missing NEXT_PUBLIC_API_BASE_URL or NEXT_PUBLIC_UI_BEARER_TOKEN");
  }

  const url = `${API_BASE_URL}${path}`;

  const res = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${API_TOKEN}`,
      "Content-Type": "application/json",
    },
    cache: "no-store",   // 🚨 IMPORTANT: disable Next cache
  });

  if (!res.ok) throw new Error(`HTTP_${res.status}`);
  return res.json();
}

export const api = {
  getDecisionEnvironment: () =>
    apiGet<DecisionEnvironmentResponse>("/v1/decision/environment"),

  getDecisionEnvironmentAt: (isoTimestamp: string) =>
    apiGet<DecisionEnvironmentResponse>(
      `/v1/decision/environment/${encodeURIComponent(isoTimestamp)}`
    ),

  listRiskEvents: (params: { min_severity?: number; decision_type?: string; at_time?: string }) => {
    const q = new URLSearchParams();
    if (params.min_severity != null) q.set("min_severity", String(params.min_severity));
    if (params.decision_type) q.set("decision_type", params.decision_type);
    if (params.at_time) q.set("at_time", params.at_time);
    return apiGet<DecisionRiskEventResponse[]>(`/v1/decision/risk-events?${q.toString()}`);
  },

  listNarratives: (params: { min_saturation?: number; active_only?: boolean }) => {
    const q = new URLSearchParams();
    if (params.min_saturation != null) q.set("min_saturation", String(params.min_saturation));
    if (params.active_only != null) q.set("active_only", params.active_only ? "true" : "false");
    return apiGet<NarrativeResponse[]>(`/v1/decision/narratives?${q.toString()}`);
  },

  getNarrative: (id: string) =>
    apiGet<NarrativeDetailResponse>(`/v1/decision/narratives/${encodeURIComponent(id)}`),

  listDecisionHistory: (params: { start_time: string; end_time: string }) => {
    const q = new URLSearchParams(params);
    return apiGet<DecisionHistoryItemResponse[]>(`/v1/decision/history?${q.toString()}`);
  },


  getDecisionHistoryItem: (contextId: string, _revalidateSeconds?: number) =>
    apiGet<DecisionHistoryItemResponse>(`/v1/decision/history/${encodeURIComponent(contextId)}`),

  getNarrativeDetail: (id: string) =>
    apiGet<NarrativeDetailResponse>(`/v1/decision/narratives/${encodeURIComponent(id)}`),

  getInformationReliability: async (asset: string): Promise<InformationReliabilityResponse> => {
    const fallback: InformationReliabilityResponse = {
      state: {
        overall_reliability: "unverified",
        confirmation_rate: 0,
        contradiction_rate: 0,
        active_narratives_count: 0,
      },
      signals: [],
    };

    try {
      return await apiGet<InformationReliabilityResponse>(
        `/v1/market/intel?asset=${encodeURIComponent(asset)}`
      );
    } catch (err) {
      // During static generation the backend may be unavailable.
      // Fall back to a safe, unverified static state to allow build.
      // Keep the error visible in build logs for debugging.
      // eslint-disable-next-line no-console
      console.warn("Failed to fetch market intel, using fallback:", err);
      return fallback;
    }
  },
};
