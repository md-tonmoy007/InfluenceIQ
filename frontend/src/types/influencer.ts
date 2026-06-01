export type InfluencerRecommendation = {
  id: string;
  name: string;
  handle: string;
  platform: string;
  followers: number;
  engagementRate: number;
  matchScore: number;
  trustGrade: "A+" | "A" | "B" | "C" | "D";
  brandSafetyFlags: string[];
  citations: string[];
  rate: string;
};
