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

export function reportHref(influencerId: string, reportId: string): string {
  return `/report/${encodeURIComponent(influencerId)}?reportId=${encodeURIComponent(reportId)}`;
}
