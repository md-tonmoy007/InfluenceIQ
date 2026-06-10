import type { CampaignBriefPayload } from "@/types/campaign";
import type { InfluencerRecommendation } from "@/types/influencer";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

type BackendCampaign = {
  campaign_id: string;
  brand: string;
  product: string;
  category: string;
  goal: string;
  status: string;
  created_at: string;
  payload: Record<string, unknown>;
  pipeline_state: CampaignState;
  influencer_count: number;
  partial_results_available: boolean;
  error?: string | null;
};

type BackendInfluencer = {
  id: string;
  name: string;
  handle: string;
  platform: string;
  followers: number;
  engagementRate: number;
  matchScore: number;
  trustGrade: "A+" | "A" | "B" | "C" | "D";
  brandSafetyFlags: string[];
  citations: string[];
  rate: string;
  sub_scores?: Record<string, number>;
  score_payload?: Record<string, unknown>;
  source_payload?: Record<string, unknown>;
};

type BackendInfluencerList = {
  items: BackendInfluencer[];
  total: number;
  limit: number;
  offset: number;
  filters: Record<string, string | number>;
  sort: { by: string; direction: string };
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
  filters: Record<string, string | number>;
  sort: { by: string; direction: string };
};

const apiUrl = (path: string) => `${API_BASE_URL.replace(/\/$/, "")}${path}`;

const requestJson = async <T>(path: string, init?: RequestInit): Promise<T> => {
  if (!API_BASE_URL) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured");
  }

  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
};

const mapCampaign = (campaign: BackendCampaign): CampaignSummary => ({
  campaignId: campaign.campaign_id,
  brand: campaign.brand,
  product: campaign.product,
  category: campaign.category,
  goal: campaign.goal,
  status: campaign.status,
  createdAt: campaign.created_at,
  payload: campaign.payload,
  pipelineState: campaign.pipeline_state,
  influencerCount: campaign.influencer_count,
  partialResultsAvailable: campaign.partial_results_available,
  error: campaign.error,
});

const mapInfluencer = (item: BackendInfluencer): InfluencerRecommendation => ({
  id: item.id,
  name: item.name,
  handle: item.handle,
  platform: item.platform,
  followers: item.followers,
  engagementRate: item.engagementRate,
  matchScore: item.matchScore,
  trustGrade: item.trustGrade,
  brandSafetyFlags: item.brandSafetyFlags,
  citations: item.citations,
  rate: item.rate,
  subScores: item.sub_scores ?? {},
  scorePayload: item.score_payload ?? {},
  sourcePayload: item.source_payload ?? {},
});

export const createCampaign = async (
  payload: CampaignBriefPayload
): Promise<{ campaignId: string; status: string }> => {
  const response = await requestJson<{ campaign_id: string; status: string }>(
    "/api/campaigns",
    {
      method: "POST",
      body: JSON.stringify(payload),
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
  return {
    items: response.items.map(mapInfluencer),
    total: response.total,
    limit: response.limit,
    offset: response.offset,
    filters: response.filters,
    sort: response.sort,
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
}): Promise<{ user: CurrentUser }> =>
  requestJson<{ user: CurrentUser }>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const login = async (payload: {
  email: string;
  password: string;
}): Promise<{ user: CurrentUser }> =>
  requestJson<{ user: CurrentUser }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const logout = async (): Promise<{ status: string }> =>
  requestJson<{ status: string }>("/api/auth/logout", {
    method: "POST",
  });

export const getMe = async (): Promise<CurrentUser> =>
  requestJson<CurrentUser>("/api/auth/me");
