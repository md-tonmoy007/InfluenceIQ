import type { CampaignBriefPayload } from "@/types/campaign";
import type { InfluencerRecommendation } from "@/types/influencer";
import {
  getAccessToken,
  refreshAccessToken,
  clearTokens,
} from "@/lib/auth";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

// Mirrors backend CampaignResponse (backend/api/schemas/campaign.py).
type BackendCampaignResponse = {
  id: string;
  product: string;
  niche: string;
  goals: string | null;
  target_audience: string | null;
  preferred_platforms: string[] | null;
  budget_range: string | null;
  weights: Record<string, number> | null;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  failure_reason: string | null;
  created_at: string;
};

// GET /api/campaigns/{id} returns { campaign, pipeline_state }.
type BackendCampaign = {
  campaign: BackendCampaignResponse;
  pipeline_state: CampaignState;
};

type BackendSubScores = {
  relevance: number;
  credibility: number;
  engagement: number;
  sentiment: number;
  brand_safety: number;
};

type BackendCrawlSource = {
  url: string;
  title?: string | null;
  relevance_score?: number | null;
  status: string;
  mention_id?: string | null;
  mention?: Record<string, unknown> | null;
};

// Mirrors backend InfluencerResponse (backend/api/schemas/influencer.py).
type BackendInfluencer = {
  influencer_id: string;
  canonical_name: string;
  platforms: Record<string, string>;
  credentials?: string[] | null;
  mentions?: Array<Record<string, unknown>> | null;
  final_score?: number | null;
  sub_scores?: BackendSubScores | null;
  confidence?: string | null;
  data_source_count?: number;
  score_version?: string | null;
  computed_at?: string | null;
  signal_scores?: Record<string, number> | null;
  risk_category?: string | null;
  detection_category?: string | null;
  positive_reasons?: string[] | null;
  negative_reasons?: string[] | null;
  sources?: BackendCrawlSource[] | null;
};

// GET /api/campaigns/{id}/influencers returns keyset-paginated rows.
type BackendInfluencerList = {
  items: BackendInfluencer[];
  next_cursor: string | null;
  limit: number;
};

export type CurrentUser = {
  user_id: string;
  company_name: string;
  name: string;
  email: string;
};

export type CampaignSummary = {
  campaignId: string;
  brand: string;
  product: string;
  category: string;
  goal: string;
  status: string;
  createdAt: string;
  payload: Record<string, unknown>;
  pipelineState: CampaignState;
  influencerCount: number;
  partialResultsAvailable: boolean;
  error?: string | null;
};

export type CampaignState = {
  campaign_id?: string;
  status?: string;
  phase?: string;
  error?: string;
  influencer_count?: number;
  partial_results_available?: boolean;
  urls_discovered?: number;
  urls_scraped?: number;
  influencers_found?: number;
  scores_computed?: number;
  duration_seconds?: number;
  last_query?: string;
  last_score?: number;
  last_scored_influencer?: string;
  generated_query_count?: number;
  discovered_url_count?: number;
  brand_safety_checked?: boolean;
  [key: string]: unknown;
};

export type InfluencerListResult = {
  items: InfluencerRecommendation[];
  total: number;
  limit: number;
  offset: number;
  nextCursor: string | null;
  filters: Record<string, string | number>;
  sort: { by: string; direction: string };
};

const apiUrl = (path: string) => `${API_BASE_URL.replace(/\/$/, "")}${path}`;

const requestJson = async <T>(path: string, init?: RequestInit): Promise<T> => {
  if (!API_BASE_URL) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured");
  }

  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((init?.headers as Record<string, string>) ?? {}),
  };

  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: "include",
    headers,
    cache: "no-store",
  });

  // On 401, try a single token refresh then retry
  if (response.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.Authorization = `Bearer ${newToken}`;
      const retryResponse = await fetch(apiUrl(path), {
        ...init,
        credentials: "include",
        headers,
        cache: "no-store",
      });
      if (retryResponse.ok) {
        return retryResponse.json() as Promise<T>;
      }
    }
    clearTokens();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Session expired");
  }

  if (!response.ok) {
    let message: string;
    try {
      const body = await response.json();
      message = body.detail ?? body.message ?? JSON.stringify(body);
    } catch {
      message = await response.text().catch(() => "");
    }
    // Map status codes to readable messages when no detail is returned
    if (!message) {
      const statusMessages: Record<number, string> = {
        400: "Invalid request. Please check your input.",
        401: "Invalid email or password.",
        403: "You don't have permission to do that.",
        404: "Service unavailable. Please try again.",
        409: "An account with this email already exists.",
        422: "Please check your input and try again.",
        429: "Too many requests. Please wait a moment.",
        500: "Something went wrong. Please try again.",
      };
      message = statusMessages[response.status] ?? `Request failed (${response.status})`;
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
};

const mapCampaign = (response: BackendCampaign): CampaignSummary => {
  const { campaign, pipeline_state: state } = response;
  return {
    campaignId: campaign.id,
    // Backend has no separate brand field; surface product as the label.
    brand: campaign.product,
    product: campaign.product,
    category: campaign.niche,
    goal: campaign.goals ?? "",
    status: campaign.status,
    createdAt: campaign.created_at,
    payload: {
      target_audience: campaign.target_audience,
      preferred_platforms: campaign.preferred_platforms,
      budget_range: campaign.budget_range,
      weights: campaign.weights,
    },
    pipelineState: state ?? {},
    influencerCount:
      (state?.influencer_count as number | undefined) ??
      (state?.influencers_found as number | undefined) ??
      0,
    partialResultsAvailable: state?.partial_results_available ?? false,
    error: campaign.failure_reason ?? state?.error,
  };
};

// Mirrors the grade bounds in backend get_campaign_influencers (campaigns.py).
const gradeFromScore = (score: number): InfluencerRecommendation["trustGrade"] => {
  if (score >= 90) return "A+";
  if (score >= 80) return "A";
  if (score >= 70) return "B";
  if (score >= 60) return "C";
  return "D";
};

const mapInfluencer = (item: BackendInfluencer): InfluencerRecommendation => {
  const [platformKey, platformHandle] = Object.entries(item.platforms ?? {})[0] ?? ["", ""];
  const finalScore = item.final_score ?? 0;
  const subScores: Record<string, number> = item.sub_scores
    ? {
        relevance: item.sub_scores.relevance,
        credibility: item.sub_scores.credibility,
        engagement: item.sub_scores.engagement,
        sentiment: item.sub_scores.sentiment,
        brand_safety: item.sub_scores.brand_safety,
      }
    : {};
  return {
    id: item.influencer_id,
    name: item.canonical_name,
    handle: platformHandle || "@unknown",
    platform: platformKey || "instagram",
    // Follower count, true engagement rate, and dollar rate are not captured
    // by the pipeline; the UI degrades these gracefully (shows "—").
    followers: 0,
    engagementRate: 0,
    rate: "",
    matchScore: finalScore,
    trustGrade: gradeFromScore(finalScore),
    brandSafetyFlags: item.negative_reasons ?? [],
    citations: (item.sources ?? []).map((source) => source.url),
    subScores,
    scorePayload: {
      signal_scores: item.signal_scores ?? {},
      confidence: item.confidence,
      data_source_count: item.data_source_count,
      score_version: item.score_version,
      computed_at: item.computed_at,
      risk_category: item.risk_category,
      detection_category: item.detection_category,
      positive_reasons: item.positive_reasons ?? [],
      negative_reasons: item.negative_reasons ?? [],
    },
    sourcePayload: {
      sources: item.sources ?? [],
      platforms: item.platforms ?? {},
      credentials: item.credentials ?? [],
      mentions: item.mentions ?? [],
    },
  };
};

export const createCampaign = async (
  brief: CampaignBriefPayload
): Promise<{ campaignId: string; status: string }> => {
  // Translate the UI brief into the backend CampaignCreate contract.
  const targetAudience = [
    brief.ages.length ? `Ages: ${brief.ages.join(", ")}` : "",
    brief.gender && brief.gender !== "All" ? `Gender: ${brief.gender}` : "",
    brief.locations.length ? `Locations: ${brief.locations.join(", ")}` : "",
    brief.tier && brief.tier !== "No Preference" ? `Tier: ${brief.tier}` : "",
  ]
    .filter(Boolean)
    .join("; ");

  const body = {
    product: brief.product,
    industry: brief.category,
    goals: [brief.goal, brief.notes].filter(Boolean).join("\n\n") || null,
    target_audience: targetAudience || null,
    preferred_platforms: brief.platforms.length ? brief.platforms : null,
    budget_range: brief.budget || null,
  };

  const response = await requestJson<{ campaign_id: string; status: string }>(
    "/api/campaigns",
    {
      method: "POST",
      body: JSON.stringify(body),
    }
  );
  return {
    campaignId: response.campaign_id,
    status: response.status,
  };
};

export const getCampaign = async (campaignId: string): Promise<CampaignSummary> => {
  const response = await requestJson<BackendCampaign>(
    `/api/campaigns/${encodeURIComponent(campaignId)}`
  );
  return mapCampaign(response);
};

export const getCampaignState = async (campaignId: string): Promise<CampaignState> =>
  requestJson<CampaignState>(`/api/campaigns/${encodeURIComponent(campaignId)}/state`);

export const getCampaignInfluencers = async (
  campaignId: string,
  params?: URLSearchParams
): Promise<InfluencerListResult> => {
  const suffix = params && params.toString() ? `?${params.toString()}` : "";
  const response = await requestJson<BackendInfluencerList>(
    `/api/campaigns/${encodeURIComponent(campaignId)}/influencers${suffix}`
  );
  const items = response.items.map(mapInfluencer);
  return {
    items,
    total: items.length,
    limit: response.limit,
    offset: 0,
    nextCursor: response.next_cursor,
    filters: {},
    sort: { by: "match", direction: "desc" },
  };
};

export const getCampaignInfluencer = async (
  campaignId: string,
  influencerId: string
): Promise<InfluencerRecommendation | null> => {
  const params = new URLSearchParams({ limit: "200" });
  const response = await getCampaignInfluencers(campaignId, params);
  return response.items.find(item => item.id === influencerId) ?? null;
};

export const getBackendReadiness = async (): Promise<{ status: string }> =>
  requestJson<{ status: string }>("/ready");

export const signup = async (payload: {
  company_name: string;
  name: string;
  email: string;
  password: string;
}): Promise<{ user: CurrentUser; access_token: string; refresh_token: string }> =>
  requestJson<{ user: CurrentUser; access_token: string; refresh_token: string }>(
    "/api/auth/signup",
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );

export const login = async (payload: {
  email: string;
  password: string;
}): Promise<{ user: CurrentUser; access_token: string; refresh_token: string }> =>
  requestJson<{ user: CurrentUser; access_token: string; refresh_token: string }>(
    "/api/auth/login",
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );

export const logout = async (): Promise<{ status: string }> =>
  requestJson<{ status: string }>("/api/auth/logout", {
    method: "POST",
  });

export const getMe = async (): Promise<CurrentUser> =>
  requestJson<CurrentUser>("/api/auth/me");
