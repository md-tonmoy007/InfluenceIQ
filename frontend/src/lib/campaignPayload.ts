import type { BriefQuery } from "@/lib/briefQuery";
import { briefDefaults } from "@/data/briefDefaults";
import { parseCampaignGoals } from "@/lib/brandProfile";
import type { CampaignBriefPayload } from "@/types/campaign";

const PLATFORM_KEYWORDS: Array<{ keyword: string; value: string }> = [
  { keyword: "youtube", value: "youtube" },
  { keyword: "tiktok", value: "tiktok" },
  { keyword: "instagram", value: "instagram" },
  { keyword: "facebook", value: "facebook" },
];

const titleize = (value: string) =>
  value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());

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
    budget_min: brief.budgetMin,
    budget_max: brief.budgetMax,
    currency: brief.currency,
    notes: brief.notes,
  };
};

export const buildDiscoverBriefSnapshot = (
  brief: CampaignBriefPayload,
  campaignName: string
): Record<string, unknown> => ({
  brand_name: brief.brand,
  campaign_name: campaignName,
  goals: brief.goals,
  goal: brief.goals.join(", "),
  ages: brief.ages,
  gender: brief.gender,
  language: "English",
  locations: brief.locations,
  interests: brief.interests ?? [],
  platforms: brief.platforms,
  tier: brief.tier,
  budget_text: brief.budget,
  notes: brief.notes ?? "",
});

export const parseBriefSnapshot = (
  snapshot: Record<string, unknown> | null | undefined,
  campaign?: {
    product?: string;
    niche?: string;
    goals?: string | null;
    budget_range?: string | null;
    preferred_platforms?: string[] | null;
  }
): BriefQuery => {
  const snap = snapshot ?? {};
  const snapshotGoals = Array.isArray(snap.goals) ? (snap.goals as string[]) : null;
  const goals =
    (snapshotGoals?.length ? snapshotGoals : null) ??
    (typeof snap.goal === "string" && snap.goal
      ? parseCampaignGoals(snap.goal).length
        ? parseCampaignGoals(snap.goal)
        : snap.goal.split(",").map((part) => part.trim()).filter(Boolean)
      : null) ??
    (campaign?.goals ? parseCampaignGoals(campaign.goals) : briefDefaults.goals);

  const locs = Array.isArray(snap.locations)
    ? (snap.locations as string[])
    : briefDefaults.locs;

  const rawPlatforms = Array.isArray(snap.platforms)
    ? (snap.platforms as string[])
    : campaign?.preferred_platforms ?? briefDefaults.platforms.map((p) => p.toLowerCase());

  return {
    brand:
      (typeof snap.brand_name === "string" && snap.brand_name) ||
      briefDefaults.brand,
    product: campaign?.product || briefDefaults.product,
    category: campaign?.niche || briefDefaults.category,
    goals,
    ages: Array.isArray(snap.ages) ? (snap.ages as string[]) : briefDefaults.ages,
    gender: typeof snap.gender === "string" ? snap.gender : briefDefaults.gender,
    locs,
    platforms: rawPlatforms.map((platform) => titleize(String(platform))),
    tier: typeof snap.tier === "string" ? snap.tier : briefDefaults.tier,
    budget:
      (typeof snap.budget_text === "string" && snap.budget_text) ||
      campaign?.budget_range ||
      briefDefaults.budget,
  };
};

const parseBudgetFromText = (
  budgetText: string | undefined,
  fallbackMin: number,
  fallbackMax: number,
  fallbackCurrency: string
): { budgetMin: number; budgetMax: number; currency: string } => {
  if (!budgetText) {
    return { budgetMin: fallbackMin, budgetMax: fallbackMax, currency: fallbackCurrency };
  }
  const currencyMatch = budgetText.match(/\b([A-Z]{3})\b/);
  const currency = currencyMatch?.[1] ?? fallbackCurrency;
  const numbers = budgetText.match(/[\d,]+/g)?.map((n) => Number(n.replace(/,/g, ""))) ?? [];
  if (numbers.length >= 2) {
    return { budgetMin: numbers[0], budgetMax: numbers[1], currency };
  }
  if (numbers.length === 1) {
    return { budgetMin: fallbackMin, budgetMax: numbers[0], currency };
  }
  return { budgetMin: fallbackMin, budgetMax: fallbackMax, currency: fallbackCurrency };
};

export const briefFormFromSnapshot = (
  snapshot: Record<string, unknown> | null | undefined,
  campaign: {
    product: string;
    niche: string;
    goals?: string | null;
    budget_range?: string | null;
    campaign_name?: string | null;
  }
): BriefFormPayload => {
  const snap = snapshot ?? {};
  const parsed = parseBriefSnapshot(snapshot, {
    product: campaign.product,
    niche: campaign.niche,
    goals: campaign.goals,
    budget_range: campaign.budget_range,
  });

  const budgetMin =
    typeof snap.budget_min === "number" ? snap.budget_min : undefined;
  const budgetMax =
    typeof snap.budget_max === "number" ? snap.budget_max : undefined;
  const currency =
    typeof snap.currency === "string" ? snap.currency : undefined;

  const budget = parseBudgetFromText(
    typeof snap.budget_text === "string" ? snap.budget_text : campaign.budget_range ?? undefined,
    budgetMin ?? 2500,
    budgetMax ?? 12000,
    currency ?? "USD"
  );

  return {
    brand: parsed.brand,
    product: campaign.product,
    category: campaign.niche,
    campaign:
      (typeof snap.campaign_name === "string" && snap.campaign_name) ||
      campaign.campaign_name ||
      "",
    goals: parsed.goals,
    ages: parsed.ages,
    gender: parsed.gender,
    lang: typeof snap.language === "string" ? snap.language : "English",
    locs: parsed.locs,
    interests: Array.isArray(snap.interests) ? (snap.interests as string[]) : [],
    budgetMin: budget.budgetMin,
    budgetMax: budget.budgetMax,
    currency: budget.currency,
    platforms: Array.isArray(snap.platforms)
      ? (snap.platforms as string[]).map((p) => titleize(p))
      : parsed.platforms,
    tier: parsed.tier,
    notes: typeof snap.notes === "string" ? snap.notes : "",
  };
};
