// Shared shape for a campaign's searchable brief, used both when quick-creating
// from a single text query and when submitting the full brief form.
export type CampaignBriefPayload = {
  brand: string;
  description: string;
  locations: string[];
  platforms: string[];
  tier: string;
  budget: string;
  notes: string;
};

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
