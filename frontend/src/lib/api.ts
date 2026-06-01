import type { CampaignBriefPayload } from "@/types/campaign";
import type { InfluencerRecommendation } from "@/types/influencer";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export const createCampaign = async (
  payload: CampaignBriefPayload
): Promise<{ campaignId: string }> => {
  void payload;
  throw new Error("API integration pending backend contract");
};

export const getCampaignInfluencers = async (
  campaignId: string
): Promise<InfluencerRecommendation[]> => {
  void campaignId;
  throw new Error("API integration pending backend contract");
};
