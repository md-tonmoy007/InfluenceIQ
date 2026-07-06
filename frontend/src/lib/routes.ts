export const routes = {
  landing: "/",
  signup: "/signup",
  login: "/login",
  onboarding: "/onboarding",
  dashboard: "/dashboard",
  discover: "/discover",
  discoverTable: "/discover/table",
  lists: "/lists",
  briefs: "/briefs",
  newBrief: "/briefs/new",
  matching: "/matching",
  shortlist: "/shortlist",
  profile: "/profile/lila-park",
  settings: "/settings",
} as const;

export function shortlistHref(campaignId: string): string {
  return `/shortlist?campaignId=${encodeURIComponent(campaignId)}`;
}

export function campaignHref(campaignId: string, status: string): string {
  if (status === "draft") {
    return `/briefs/new?campaignId=${encodeURIComponent(campaignId)}`;
  }
  return shortlistHref(campaignId);
}

export function discoverHref(campaignId: string): string {
  return `/discover?campaignId=${encodeURIComponent(campaignId)}`;
}

export function reportHref(influencerId: string, reportId: string, campaignId?: string): string {
  const params = new URLSearchParams({ reportId });
  if (campaignId) params.set("campaignId", campaignId);
  return `/report/${encodeURIComponent(influencerId)}?${params.toString()}`;
}

export function reportRunHref(influencerId: string, runId: string, campaignId?: string): string {
  const params = new URLSearchParams({ runId });
  if (campaignId) params.set("campaignId", campaignId);
  return `/report/${encodeURIComponent(influencerId)}?${params.toString()}`;
}
