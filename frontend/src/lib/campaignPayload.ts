import type { CampaignBriefPayload } from "@/types/campaign";

const PLATFORM_KEYWORDS: Array<{ keyword: string; value: string }> = [
  { keyword: "youtube", value: "youtube" },
  { keyword: "tiktok", value: "tiktok" },
  { keyword: "instagram", value: "instagram" },
  { keyword: "facebook", value: "facebook" },
];

export const buildCampaignPayloadFromQuery = (query: string): CampaignBriefPayload => {
  const normalizedQuery = query.trim();
  const lowered = normalizedQuery.toLowerCase();
  const platforms = PLATFORM_KEYWORDS.filter(({ keyword }) => lowered.includes(keyword)).map(
    ({ value }) => value
  );

  return {
    brand: "Discover Search",
    product: normalizedQuery.slice(0, 120) || "Creator search",
    category: "General",
    goal: normalizedQuery || "Find relevant creators",
    ages: [],
    gender: "All",
    locations: [],
    platforms: platforms.length ? platforms : ["youtube", "tiktok"],
    tier: "No Preference",
    budget: "Flexible",
    notes: normalizedQuery,
    query: normalizedQuery,
  };
};
