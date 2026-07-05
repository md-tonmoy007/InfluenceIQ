export type CampaignWeights = {
  relevance: number;
  credibility: number;
  engagement: number;
  sentiment: number;
  brand_safety: number;
};

export const DEFAULT_CAMPAIGN_WEIGHTS: CampaignWeights = {
  relevance: 0.3,
  credibility: 0.3,
  engagement: 0.2,
  sentiment: 0.1,
  brand_safety: 0.1,
};
