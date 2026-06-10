export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "";

export const getCampaignWebSocketUrl = (
  campaignId: string,
  options?: { lastEventId?: number }
) => {
  if (!WS_BASE_URL) {
    throw new Error("NEXT_PUBLIC_WS_BASE_URL is not configured");
  }

  const url = new URL(
    `${WS_BASE_URL.replace(/\/$/, "")}/ws/campaign/${encodeURIComponent(campaignId)}`
  );
  if (options?.lastEventId) {
    url.searchParams.set("last_event_id", String(options.lastEventId));
  }
  return url.toString();
};
