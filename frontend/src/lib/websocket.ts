export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "";

export const getCampaignWebSocketUrl = (campaignId: string) => {
  if (!WS_BASE_URL) {
    throw new Error("WebSocket integration pending backend contract");
  }

  return `${WS_BASE_URL.replace(/\/$/, "")}/ws/campaign/${encodeURIComponent(
    campaignId
  )}`;
};
