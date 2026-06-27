export type CampaignWeights = {
  relevance: number;
  credibility: number;
  engagement: number;
  sentiment: number;
  brand_safety: number;
};

export const DEFAULT_CAMPAIGN_WEIGHTS: CampaignWeights = {
  relevance: 0.2,
  credibility: 0.2,
  engagement: 0.15,
  sentiment: 0.15,
  brand_safety: 0.15,
};
