export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "";

const resolveWsBaseUrl = (): string => {
  const configured = WS_BASE_URL.trim().replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}`;
  }
  return "";
};

export const getCampaignWebSocketUrl = (
  campaignId: string,
  options?: { lastEventId?: number }
) => {
  const baseUrl = resolveWsBaseUrl();
  if (!baseUrl) {
    throw new Error("NEXT_PUBLIC_WS_BASE_URL is not configured");
  }

  const url = new URL(
    `${baseUrl}/ws/campaign/${encodeURIComponent(campaignId)}`
  );
  if (options?.lastEventId) {
    url.searchParams.set("last_event_id", String(options.lastEventId));
  }
  return url.toString();
};
