export type CampaignBriefPayload = {
  brand: string;
  product: string;
  category: string;
  goals: string[];
  ages: string[];
  gender: string;
  locations: string[];
  platforms: string[];
  tier: string;
  budget: string;
  interests?: string[];
  notes?: string;
  query?: string;
};
