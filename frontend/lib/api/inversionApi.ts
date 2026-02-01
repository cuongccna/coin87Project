import type { InversionFeed, InversionFeedCreate, InversionFeedListResponse } from "./inversionTypes";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL!;
const API_TOKEN = process.env.NEXT_PUBLIC_UI_BEARER_TOKEN!;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!API_BASE_URL || !API_TOKEN) {
    throw new Error("Missing NEXT_PUBLIC_API_BASE_URL or NEXT_PUBLIC_UI_BEARER_TOKEN");
  }

  const url = `${API_BASE_URL}${path}`;

  const res = await fetch(url, {
    ...options,
    headers: {
      Authorization: `Bearer ${API_TOKEN}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`API error ${res.status}: ${res.statusText} - ${errorBody}`);
  }

  return res.json();
}

/**
 * Fetch inversion feeds with filtering.
 */
export async function fetchInversionFeeds(
  params?: {
    symbol?: string;
    status?: string;
    narrative_risk?: string;
    limit?: number;
    offset?: number;
    start?: string;
    end?: string;
  }
): Promise<InversionFeedListResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) {
        searchParams.append(k, String(v));
      }
    });
  }
  return request<InversionFeedListResponse>(`/v1/inversion-feeds/?${searchParams.toString()}`);
}

/**
 * Fetch a single feed.
 */
export async function fetchInversionFeed(id: string): Promise<InversionFeed> {
  return request<InversionFeed>(`/v1/inversion-feeds/${id}`);
}

/**
 * Create a new feed.
 */
export async function postInversionFeed(data: InversionFeedCreate): Promise<InversionFeed> {
  return request<InversionFeed>('/v1/inversion-feeds/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
