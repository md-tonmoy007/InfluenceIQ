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
  product: string | null;
  niche: string | null;
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
  campaign_name: string | null;
  entry_point: string | null;
  search_query: string | null;
  brief_snapshot: Record<string, unknown> | null;
  created_at: string;
  updated_at: string | null;
  influencer_count: number | null;
  top_match_score: number | null;
  last_activity_at: string | null;
  shortlisted_count: number | null;
  contracted_count: number | null;
};

// GET /api/campaigns/{id} returns flat CampaignResponse + pipeline_state.
type BackendCampaign = BackendCampaignResponse & {
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
  primary_platform?: string | null;
  primary_handle?: string | null;
  follower_count?: number | null;
  engagement_rate?: number | null;
  avg_views?: number | null;
  primary_category?: string | null;
  primary_location?: string | null;
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
  role?: string | null;
  timezone?: string | null;
};

export type CampaignSummary = {
  campaignId: string;
  brand: string;
  product: string | null;
  category: string | null;
  goal: string;
  status: string;
  createdAt: string;
  campaignName: string | null;
  entryPoint: string | null;
  searchQuery: string | null;
  briefSnapshot: Record<string, unknown> | null;
  preferredPlatforms: string[] | null;
  budgetRange: string | null;
  shortlistedCount: number;
  contractedCount: number;
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

// ---------------------------------------------------------------------------
// Workspace summary types (GET /api/workspace/summary)
// ---------------------------------------------------------------------------

export type WorkspaceViewer = {
  user_id: string;
  name: string;
  email: string;
  company_name: string;
  role: string | null;
  timezone: string;
};

export type WorkspaceGreeting = {
  text: string;
  date_label: string;
  timestamp: string;
};

export type WorkspaceHeroCounts = {
  active_campaigns: number;
  completed_campaigns: number;
  draft_campaigns: number;
  failed_campaigns: number;
  saved_lists: number;
};

export type WorkspaceStats = {
  indexed_influencers: number;
  categories_covered: number;
  avg_match_score_30d: number;
};

export type WorkspaceRecentSearch = {
  campaign_id: string;
  label: string;
  product: string | null;
  niche: string | null;
  goal: string | null;
  status: string;
  entry_point: string | null;
  created_at: string;
  updated_at: string | null;
  started_at: string | null;
  completed_at: string | null;
};

export type WorkspaceSidebarCounts = {
  briefs: number;
  saved_lists: number;
  discover: number;
};

export type WorkspaceUpgradeUsage = {
  plan: string;
  limit: number;
  used: number;
  remaining: number;
};

export type WorkspaceSummary = {
  viewer: WorkspaceViewer;
  greeting: WorkspaceGreeting;
  hero_counts: WorkspaceHeroCounts;
  stats_cards: WorkspaceStats;
  recent_searches: WorkspaceRecentSearch[];
  sidebar_counts: WorkspaceSidebarCounts;
  upgrade_usage: WorkspaceUpgradeUsage;
};

// ---------------------------------------------------------------------------
// Campaign list + facet types
// ---------------------------------------------------------------------------

export type CampaignListItem = {
  id: string;
  product: string | null;
  niche: string | null;
  goals: string | null;
  status: string;
  campaign_name: string | null;
  entry_point: string | null;
  search_query: string | null;
  brief_snapshot: Record<string, unknown> | null;
  created_at: string;
  updated_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  failure_reason: string | null;
  preferred_platforms: string[] | null;
  budget_range: string | null;
  influencer_count: number | null;
  top_match_score: number | null;
  last_activity_at: string | null;
  shortlisted_count: number | null;
  contracted_count: number | null;
};

export type CampaignListResult = {
  items: CampaignListItem[];
  total: number;
  limit: number;
  offset: number;
};

export type CampaignFacet = { value: string; count: number };

export type CampaignFacets = {
  campaign_id: string;
  platforms: CampaignFacet[];
  trust_grades: CampaignFacet[];
  categories: CampaignFacet[];
  locations: CampaignFacet[];
  follower_tiers: CampaignFacet[];
  total: number;
};

// ---------------------------------------------------------------------------
// Saved list types
// ---------------------------------------------------------------------------

export type SavedListSummary = {
  id: string;
  name: string;
  status: "active" | "draft";
  created_at: string;
  updated_at: string;
  item_count: number;
  avg_match_score: number | null;
  platform_mix: Array<{ platform: string; count: number }>;
  total_followers: number;
  avg_engagement: number | null;
};

export type SavedListInfluencer = {
  id: string;
  canonical_name: string;
  primary_platform: string | null;
  primary_handle: string | null;
  primary_category: string | null;
  primary_location: string | null;
  follower_count: number | null;
  engagement_rate: number | null;
  avg_views: number | null;
  platforms: Record<string, string>;
};

export type SavedListItem = {
  id: string;
  influencer_id: string;
  source_campaign_id: string | null;
  match_score_snapshot: number | null;
  added_at: string;
  influencer: SavedListInfluencer | null;
};

export type SavedListDetail = SavedListSummary & {
  items: SavedListItem[];
};

export class RerunOutreachError extends Error {
  readonly code = "rerun_has_outreach" as const;

  constructor(message: string) {
    super(message);
    this.name = "RerunOutreachError";
  }
}

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

  // On 401, try a single token refresh then retry — but only for
  // authenticated endpoints. Auth endpoints (login/signup) intentionally
  // return 401 for bad credentials, and we must surface that to the caller
  // rather than bouncing the page to /login.
  const isAuthEndpoint =
    path === "/api/auth/login" || path === "/api/auth/signup";
  if (response.status === 401 && !isAuthEndpoint) {
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
      // Backend wraps errors in an ErrorEnvelope
      // (backend/api/schemas/errors.py): { error: { code, message, ... } }.
      // Fall back to FastAPI's default { detail } for non-wrapped responses,
      // then to { message }, then to the raw body.
      const envelope = body as {
        error?: { message?: string };
        detail?: string | { code?: string; message?: string };
        message?: string;
      };
      const detail = envelope.detail;
      if (
        typeof detail === "object" &&
        detail !== null &&
        detail.code === "rerun_has_outreach"
      ) {
        throw new RerunOutreachError(
          detail.message ??
            "This will replace current match results. Saved list items and contracts are kept."
        );
      }
      message =
        envelope.error?.message ??
        (typeof detail === "string" ? detail : undefined) ??
        (typeof detail === "object" && detail !== null && detail.message
          ? detail.message
          : undefined) ??
        envelope.message ??
        (typeof detail === "object" ? JSON.stringify(detail) : undefined) ??
        JSON.stringify(body);
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

  // 204 No Content (and other empty-body success codes) have no
  // JSON to parse. The settings page uses 204 for change-password,
  // delete-account, and revoke-api-key, so the caller should
  // receive `undefined` rather than a parse failure.
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
};

const requestVoid = async (path: string, init?: RequestInit): Promise<void> => {
  await requestJson<null>(path, init);
};

const mapCampaign = (response: BackendCampaign): CampaignSummary => {
  const { pipeline_state: state, ...campaign } = response;
  const snapshot = campaign.brief_snapshot ?? {};
  const brandName =
    (typeof snapshot.brand_name === "string" && snapshot.brand_name) ||
    campaign.product ||
    campaign.search_query ||
    "Untitled campaign";

  return {
    campaignId: campaign.id,
    brand: brandName,
    product: campaign.product,
    category: campaign.niche,
    goal: campaign.goals ?? "",
    status: campaign.status,
    createdAt: campaign.created_at,
    campaignName: campaign.campaign_name,
    entryPoint: campaign.entry_point,
    searchQuery: campaign.search_query,
    briefSnapshot: campaign.brief_snapshot,
    preferredPlatforms: campaign.preferred_platforms,
    budgetRange: campaign.budget_range,
    shortlistedCount: campaign.shortlisted_count ?? 0,
    contractedCount: campaign.contracted_count ?? 0,
    payload: {
      target_audience: campaign.target_audience,
      preferred_platforms: campaign.preferred_platforms,
      budget_range: campaign.budget_range,
      weights: campaign.weights,
      brief_snapshot: campaign.brief_snapshot,
    },
    pipelineState: state ?? {},
    influencerCount:
      campaign.influencer_count ??
      (state?.influencer_count as number | undefined) ??
      (state?.influencers_found as number | undefined) ??
      0,
    partialResultsAvailable: state?.partial_results_available ?? false,
    error: campaign.failure_reason ?? (state?.error as string | undefined),
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
    handle: platformHandle || item.primary_handle || "@unknown",
    platform: item.primary_platform || platformKey || "instagram",
    // Best-effort metrics from the persisted Influencer row; stay 0
    // when the pipeline didn't capture them so the UI keeps rendering
    // "—" rather than fabricating numbers.
    followers: item.follower_count ?? 0,
    engagementRate: item.engagement_rate ?? 0,
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

export type CampaignCreateOptions = {
  /** Origin of the campaign submission. */
  entryPoint: "brief_form" | "discover_search" | "topbar_search";
  /** Display label for the workspace shell (briefs, dashboard). */
  campaignName?: string;
  /** Raw text describing the campaign/product, drives influencer search. */
  searchQuery: string;
  /** Typed brief form fields, persisted for UI display. */
  briefSnapshot?: Record<string, unknown> | null;
  /** When false, create a draft without starting the pipeline. */
  startPipeline?: boolean;
  weights?: {
    relevance: number;
    credibility: number;
    engagement: number;
    sentiment: number;
    brand_safety: number;
  };
};

export type CampaignDraftUpdateBody = {
  search_query?: string;
  preferred_platforms?: string[] | null;
  budget_range?: string | null;
  campaign_name?: string | null;
  brief_snapshot?: Record<string, unknown> | null;
};

const buildCampaignRequestBody = (
  brief: CampaignBriefPayload,
  options: CampaignCreateOptions
): Record<string, unknown> => {
  const body: Record<string, unknown> = {
    search_query: options.searchQuery,
    preferred_platforms: brief.platforms.length ? brief.platforms : null,
    budget_range: brief.budget || null,
    entry_point: options.entryPoint,
    start_pipeline: options.startPipeline !== false,
  };

  if (options.campaignName) body.campaign_name = options.campaignName;
  if (options.briefSnapshot) body.brief_snapshot = options.briefSnapshot;
  if (options.weights) body.weights = options.weights;

  return body;
};

export const createCampaign = async (
  brief: CampaignBriefPayload,
  options: CampaignCreateOptions
): Promise<{ campaignId: string; status: string }> => {
  const response = await requestJson<{ campaign_id: string; status: string }>(
    "/api/campaigns",
    {
      method: "POST",
      body: JSON.stringify(buildCampaignRequestBody(brief, options)),
    }
  );
  return {
    campaignId: response.campaign_id,
    status: response.status,
  };
};

export const createCampaignDraft = async (
  brief: CampaignBriefPayload,
  options: Omit<CampaignCreateOptions, "startPipeline">
): Promise<{ campaignId: string; status: string }> =>
  createCampaign(brief, { ...options, startPipeline: false });

export const updateCampaignDraft = async (
  campaignId: string,
  body: CampaignDraftUpdateBody
): Promise<CampaignListItem> =>
  requestJson<CampaignListItem>(
    `/api/campaigns/${encodeURIComponent(campaignId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(body),
    }
  );

export const submitCampaign = async (
  campaignId: string
): Promise<{ campaignId: string; status: string }> => {
  const response = await requestJson<{ campaign_id: string; status: string }>(
    `/api/campaigns/${encodeURIComponent(campaignId)}/submit`,
    { method: "POST" }
  );
  return {
    campaignId: String(response.campaign_id),
    status: response.status,
  };
};

export const duplicateCampaign = async (
  campaignId: string
): Promise<{ campaignId: string; status: string }> => {
  const response = await requestJson<{ id: string; campaign_id?: string; status: string }>(
    `/api/campaigns/${encodeURIComponent(campaignId)}/duplicate`,
    { method: "POST" }
  );
  return {
    campaignId: String(response.campaign_id ?? response.id),
    status: response.status,
  };
};

export const rerunCampaign = async (
  campaignId: string,
  options?: { startPipeline?: boolean; confirmOutreach?: boolean }
): Promise<{ campaignId: string; status: string; pipelineState?: CampaignState }> => {
  const startPipeline = options?.startPipeline !== false;
  const params = new URLSearchParams({ start_pipeline: String(startPipeline) });
  const headers: Record<string, string> = {};
  if (options?.confirmOutreach) {
    headers["X-Confirm-Rerun"] = "true";
  }

  const response = await requestJson<{
    campaign_id: string;
    status: string;
    pipeline_state?: CampaignState;
  }>(`/api/campaigns/${encodeURIComponent(campaignId)}/rerun?${params.toString()}`, {
    method: "POST",
    headers,
  });

  return {
    campaignId: String(response.campaign_id),
    status: response.status,
    pipelineState: response.pipeline_state,
  };
};

export const deleteCampaign = async (campaignId: string): Promise<void> => {
  await requestVoid(`/api/campaigns/${encodeURIComponent(campaignId)}`, {
    method: "DELETE",
  });
};

export type CampaignContract = {
  id: string;
  campaign_id: string;
  influencer_id: string;
  status: string;
  notes: string | null;
  created_at: string;
};

export const listCampaignContracts = async (
  campaignId: string
): Promise<{ items: CampaignContract[]; total: number }> =>
  requestJson<{ items: CampaignContract[]; total: number }>(
    `/api/campaigns/${encodeURIComponent(campaignId)}/contracts`
  );

export const addCampaignContract = async (
  campaignId: string,
  influencerId: string,
  options?: { status?: string; notes?: string }
): Promise<CampaignContract> =>
  requestJson<CampaignContract>(
    `/api/campaigns/${encodeURIComponent(campaignId)}/contracts`,
    {
      method: "POST",
      body: JSON.stringify({
        influencer_id: influencerId,
        status: options?.status ?? "contracted",
        notes: options?.notes ?? null,
      }),
    }
  );

export const removeCampaignContract = async (
  campaignId: string,
  influencerId: string
): Promise<void> =>
  requestVoid(
    `/api/campaigns/${encodeURIComponent(campaignId)}/contracts/${encodeURIComponent(influencerId)}`,
    { method: "DELETE" }
  );

export const getCampaign = async (campaignId: string): Promise<CampaignSummary> => {
  const response = await requestJson<BackendCampaign>(
    `/api/campaigns/${encodeURIComponent(campaignId)}`
  );
  return mapCampaign(response);
};

export const getCampaignState = async (campaignId: string): Promise<CampaignState> =>
  requestJson<CampaignState>(`/api/campaigns/${encodeURIComponent(campaignId)}/state`);

export const cancelCampaign = async (campaignId: string): Promise<Record<string, unknown>> =>
  requestJson<Record<string, unknown>>(
    `/api/campaigns/${encodeURIComponent(campaignId)}/cancel`,
    { method: "POST" }
  );

export const getInfluencerProfile = async (influencerId: string): Promise<Record<string, unknown>> =>
  requestJson<Record<string, unknown>>(`/api/influencers/${encodeURIComponent(influencerId)}`);

export const getInfluencerScores = async (influencerId: string): Promise<Array<Record<string, unknown>>> =>
  requestJson<Array<Record<string, unknown>>>(`/api/influencers/${encodeURIComponent(influencerId)}/scores`);

export const getInfluencerSafetyFlags = async (influencerId: string): Promise<Array<Record<string, unknown>>> =>
  requestJson<Array<Record<string, unknown>>>(`/api/influencers/${encodeURIComponent(influencerId)}/safety`);

export const getInfluencerVerifications = async (
  influencerId: string
): Promise<Array<Record<string, unknown>>> =>
  requestJson<Array<Record<string, unknown>>>(
    `/api/influencers/${encodeURIComponent(influencerId)}/verifications`
  );

export const triggerDeepAnalysis = async (
  influencerId: string,
  campaignId: string,
  commentTarget = 2000
): Promise<Record<string, unknown>> =>
  requestJson<Record<string, unknown>>(
    `/api/influencers/${encodeURIComponent(influencerId)}/deep-analysis?campaign_id=${encodeURIComponent(campaignId)}&comment_target=${commentTarget}`,
    { method: "POST" }
  );

export const getDeepAnalysisStatus = async (
  influencerId: string,
  runId: string
): Promise<Record<string, unknown>> =>
  requestJson<Record<string, unknown>>(
    `/api/influencers/${encodeURIComponent(influencerId)}/deep-analysis/${encodeURIComponent(runId)}`
  );

export const getDeepAnalysisReport = async (
  influencerId: string,
  reportId: string
): Promise<Record<string, unknown>> =>
  requestJson<Record<string, unknown>>(
    `/api/influencers/${encodeURIComponent(influencerId)}/reports/${encodeURIComponent(reportId)}`
  );

export const getLatestDeepAnalysis = async (
  influencerId: string,
  campaignId: string
): Promise<Record<string, unknown>> =>
  requestJson<Record<string, unknown>>(
    `/api/influencers/${encodeURIComponent(influencerId)}/deep-analysis/latest?campaign_id=${encodeURIComponent(campaignId)}`
  );

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

export const listCampaigns = async (
  params?: { status?: string; entryPoint?: string; limit?: number; offset?: number }
): Promise<CampaignListResult> => {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.entryPoint) search.set("entry_point", params.entryPoint);
  if (params?.limit) search.set("limit", String(params.limit));
  if (params?.offset) search.set("offset", String(params.offset));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return requestJson<CampaignListResult>(`/api/campaigns${suffix}`);
};

export const getCampaignFacets = async (
  campaignId: string
): Promise<CampaignFacets> =>
  requestJson<CampaignFacets>(
    `/api/campaigns/${encodeURIComponent(campaignId)}/facets`
  );

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

/** Like getMe, but returns null for unauthenticated users without redirecting. */
export const getMeOptional = async (): Promise<CurrentUser | null> => {
  if (!API_BASE_URL) return null;

  const fetchMe = async (token?: string | null): Promise<Response> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;
    return fetch(apiUrl("/api/auth/me"), {
      method: "GET",
      credentials: "include",
      headers,
      cache: "no-store",
    });
  };

  let response = await fetchMe(getAccessToken());
  if (response.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      response = await fetchMe(newToken);
    } else {
      return null;
    }
  }

  if (!response.ok) return null;
  return response.json() as Promise<CurrentUser>;
};

export type OnboardingPayload = {
  brand_name: string;
  industry?: string | null;
  company_size?: string | null;
  country?: string | null;
  goals?: string[] | null;
  platforms?: string[] | null;
  monthly_budget?: number | null;
};

export type BrandProfile = OnboardingPayload & {
  id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
};

export const submitOnboarding = async (
  payload: OnboardingPayload
): Promise<BrandProfile> =>
  requestJson<BrandProfile>("/api/onboarding", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const getOnboarding = async (): Promise<BrandProfile> =>
  requestJson<BrandProfile>("/api/onboarding");

// ---------------------------------------------------------------------------
// Settings: profile, password, account deletion
// ---------------------------------------------------------------------------

export const updateProfile = async (payload: {
  name?: string;
  role?: string | null;
  timezone?: string | null;
}): Promise<CurrentUser> =>
  requestJson<CurrentUser>("/api/auth/me", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

export const changePassword = async (payload: {
  current_password: string;
  new_password: string;
}): Promise<void> => {
  await requestJson<null>("/api/auth/change-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
};

export const deleteAccount = async (): Promise<void> => {
  await requestJson<null>("/api/auth/me", {
    method: "DELETE",
  });
};

// ---------------------------------------------------------------------------
// Settings: notifications
// ---------------------------------------------------------------------------

export type NotificationPreferences = {
  id: string;
  user_id: string;
  shortlist_ready: boolean;
  creator_replied: boolean;
  weekly_digest: boolean;
  product_updates: boolean;
  updated_at: string;
};

export const getNotificationPreferences = async (): Promise<NotificationPreferences> =>
  requestJson<NotificationPreferences>("/api/settings/notifications");

export const updateNotificationPreferences = async (
  payload: Omit<NotificationPreferences, "id" | "user_id" | "updated_at">
): Promise<NotificationPreferences> =>
  requestJson<NotificationPreferences>("/api/settings/notifications", {
    method: "PUT",
    body: JSON.stringify(payload),
  });

// ---------------------------------------------------------------------------
// Settings: integrations (Slack / HubSpot stubs)
// ---------------------------------------------------------------------------

export type IntegrationProvider = "slack" | "hubspot";

export type IntegrationStatus = {
  provider: IntegrationProvider;
  connected: boolean;
  connected_at: string | null;
};

export const getIntegrations = async (): Promise<IntegrationStatus[]> =>
  requestJson<IntegrationStatus[]>("/api/settings/integrations");

export const connectIntegration = async (
  provider: IntegrationProvider
): Promise<IntegrationStatus> =>
  requestJson<IntegrationStatus>(
    `/api/settings/integrations/${provider}/connect`,
    { method: "POST" }
  );

export const disconnectIntegration = async (
  provider: IntegrationProvider
): Promise<IntegrationStatus> =>
  requestJson<IntegrationStatus>(
    `/api/settings/integrations/${provider}/disconnect`,
    { method: "POST" }
  );

// ---------------------------------------------------------------------------
// Settings: API keys
// ---------------------------------------------------------------------------

export type ApiKey = {
  id: string;
  key_prefix: string;
  created_at: string;
  revoked_at: string | null;
};

export type ApiKeyCreated = ApiKey & {
  // Plaintext key, returned once on creation. Never store this
  // past the lifetime of the success banner.
  key: string;
};

export const getApiKeys = async (): Promise<ApiKey[]> =>
  requestJson<ApiKey[]>("/api/settings/api-keys");

export const createApiKey = async (): Promise<ApiKeyCreated> =>
  requestJson<ApiKeyCreated>("/api/settings/api-keys", {
    method: "POST",
  });

export const revokeApiKey = async (id: string): Promise<void> => {
  await requestJson<null>(`/api/settings/api-keys/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
};

// ---------------------------------------------------------------------------
// Settings: subscription (Stripe Billing via /api/billing)
// ---------------------------------------------------------------------------

export type PlanId = "starter" | "pro" | "scale";
export type BillingInterval = "month" | "year";

export type Subscription = {
  plan: string;
  status: string | null;
  billing_interval: BillingInterval | null;
  trial_end: string | null;
  current_period_end: string | null;
  has_payment_method: boolean;
  updated_at: string;
};

export const getSubscription = async (): Promise<Subscription> =>
  requestJson<Subscription>("/api/settings/subscription");

export const createCheckoutSession = async (
  plan: "pro",
  interval: BillingInterval
): Promise<{ checkout_url: string }> =>
  requestJson<{ checkout_url: string }>("/api/billing/checkout", {
    method: "POST",
    body: JSON.stringify({ plan, interval }),
  });

export const createBillingPortalSession = async (): Promise<{ portal_url: string }> =>
  requestJson<{ portal_url: string }>("/api/billing/portal", {
    method: "POST",
  });

// ---------------------------------------------------------------------------
// Workspace (dashboard summary, activity feed)
// ---------------------------------------------------------------------------

export const getWorkspaceSummary = async (): Promise<WorkspaceSummary> =>
  requestJson<WorkspaceSummary>("/api/workspace/summary");

export type WorkspaceActivityItem = {
  kind: "campaign" | "list";
  id: string;
  label: string;
  status: string;
  niche?: string;
  entry_point?: string | null;
  created_at: string;
};

export const getWorkspaceActivity = async (
  limit = 20
): Promise<WorkspaceActivityItem[]> =>
  requestJson<WorkspaceActivityItem[]>(
    `/api/workspace/activity?limit=${encodeURIComponent(String(limit))}`
  );

// ---------------------------------------------------------------------------
// Saved lists
// ---------------------------------------------------------------------------

export const listSavedLists = async (): Promise<SavedListSummary[]> =>
  requestJson<SavedListSummary[]>("/api/lists");

export const createSavedList = async (payload: {
  name: string;
  status?: "active" | "draft";
}): Promise<SavedListSummary> =>
  requestJson<SavedListSummary>("/api/lists", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const getSavedList = async (id: string): Promise<SavedListDetail> =>
  requestJson<SavedListDetail>(`/api/lists/${encodeURIComponent(id)}`);

export const updateSavedList = async (
  id: string,
  payload: { name?: string; status?: "active" | "draft" }
): Promise<SavedListSummary> =>
  requestJson<SavedListSummary>(`/api/lists/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

export const deleteSavedList = async (id: string): Promise<void> => {
  await requestVoid(`/api/lists/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
};

export const addListItem = async (
  listId: string,
  payload: {
    influencer_id: string;
    source_campaign_id?: string | null;
    match_score_snapshot?: number | null;
  }
): Promise<{ list: SavedListSummary; added: SavedListItem[]; skipped: Array<Record<string, unknown>> }> =>
  requestJson(`/api/lists/${encodeURIComponent(listId)}/items`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const addListItems = async (
  listId: string,
  items: Array<{
    influencer_id: string;
    source_campaign_id?: string | null;
    match_score_snapshot?: number | null;
  }>
): Promise<{ list: SavedListSummary; added: SavedListItem[]; skipped: Array<Record<string, unknown>> }> =>
  requestJson(`/api/lists/${encodeURIComponent(listId)}/items:batch`, {
    method: "POST",
    body: JSON.stringify({ items }),
  });

export const removeListItem = async (
  listId: string,
  itemId: string
): Promise<void> => {
  await requestVoid(
    `/api/lists/${encodeURIComponent(listId)}/items/${encodeURIComponent(itemId)}`,
    { method: "DELETE" }
  );
};
