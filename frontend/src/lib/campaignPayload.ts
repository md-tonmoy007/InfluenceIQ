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
    goals: normalizedQuery ? [normalizedQuery] : ["Find relevant creators"],
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

export type BriefFormPayload = {
  brand: string;
  product: string;
  category: string;
  goals: string[];
  ages: string[];
  gender: string;
  lang: string;
  locs: string[];
  interests: string[];
  budgetMin: number;
  budgetMax: number;
  currency: string;
  platforms: string[];
  tier: string;
  notes: string;
  campaign: string;
};

export const buildBriefSnapshot = (brief: BriefFormPayload): Record<string, unknown> => {
  const budgetText = `${brief.currency === "BDT" ? "৳" : "$"}${brief.budgetMin.toLocaleString()} – ${
    brief.currency === "BDT" ? "৳" : "$"
  }${brief.budgetMax.toLocaleString()} ${brief.currency}`;

  return {
    brand_name: brief.brand,
    campaign_name: brief.campaign || brief.product,
    goals: brief.goals,
    goal: brief.goals.join(", "),
    ages: brief.ages,
    gender: brief.gender,
    language: brief.lang,
    locations: brief.locs,
    interests: brief.interests,
    platforms: brief.platforms.map((platform) => platform.toLowerCase()),
    tier: brief.tier,
    budget_text: budgetText,
    notes: brief.notes,
  };
};
