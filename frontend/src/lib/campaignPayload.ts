import type { BriefQuery } from "@/lib/briefQuery";
import { briefDefaults } from "@/data/briefDefaults";
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

// A currency amount like "$2k", "2,000 USD", "500 dollars".
const CURRENCY_AMOUNT =
  "[$₹€£¥]\\s?\\d[\\d,.]*\\s?[kKmM]?" +
  "|\\d[\\d,.]*\\s?[kKmM]?\\s?(?:usd|dollars?|bucks|inr|rupees?|eur|euros?|gbp|pounds?)";
const AMOUNT_RANGE = `(?:${CURRENCY_AMOUNT})(?:\\s*(?:-|to|–)\\s*(?:${CURRENCY_AMOUNT}))?`;
// Matches "$2k budget", "2k dollar budget", "with a $500-$2000 budget",
// and "budget of $10,000" in either order around the word "budget".
const BUDGET_PHRASE = new RegExp(
  `\\s*(?:,|with a|on a|for a|of|at)?\\s*${AMOUNT_RANGE}\\s*budget\\b` +
    `|\\bbudget\\s*(?:of|:)?\\s*${AMOUNT_RANGE}`,
  "gi"
);

/**
 * Search engines can't be queried for "influencers under $X budget" — there's
 * no such index. Strip budget/monetary phrases out of free text before it
 * becomes the campaign's searchable `description`. Budget itself is still
 * captured separately via the structured `budget` field.
 */
export const stripBudgetMentions = (text: string): string =>
  text
    .replace(BUDGET_PHRASE, "")
    .replace(/^(?:for|and|with|of)\s+/i, "")
    .replace(/\s*,\s*$/, "")
    .replace(/\s{2,}/g, " ")
    .trim();

export const buildCampaignPayloadFromQuery = (query: string): CampaignBriefPayload => {
  const normalizedQuery = query.trim();
  const lowered = normalizedQuery.toLowerCase();
  const platforms = PLATFORM_KEYWORDS.filter(({ keyword }) => lowered.includes(keyword)).map(
    ({ value }) => value
  );
  const description = stripBudgetMentions(normalizedQuery) || normalizedQuery;

  return {
    brand: "Discover Search",
    description,
    locations: [],
    platforms: platforms.length ? platforms : ["youtube", "tiktok"],
    tier: "No Preference",
    budget: "Flexible",
    notes: normalizedQuery,
  };
};

export type BriefFormPayload = {
  brand: string;
  description: string;
  campaign: string;
  locs: string[];
  budgetMin: number;
  budgetMax: number;
  currency: string;
  platforms: string[];
  tier: string;
};

export const buildBriefSnapshot = (brief: BriefFormPayload): Record<string, unknown> => {
  const budgetText = `${brief.currency === "BDT" ? "৳" : "$"}${brief.budgetMin.toLocaleString()} – ${
    brief.currency === "BDT" ? "৳" : "$"
  }${brief.budgetMax.toLocaleString()} ${brief.currency}`;

  return {
    brand_name: brief.brand,
    campaign_name: brief.campaign || brief.description.slice(0, 120),
    locations: brief.locs,
    platforms: brief.platforms.map((platform) => platform.toLowerCase()),
    tier: brief.tier,
    budget_text: budgetText,
    budget_min: brief.budgetMin,
    budget_max: brief.budgetMax,
    currency: brief.currency,
    notes: brief.description,
  };
};

export const buildDiscoverBriefSnapshot = (
  brief: CampaignBriefPayload,
  campaignName: string
): Record<string, unknown> => ({
  brand_name: brief.brand,
  campaign_name: campaignName,
  locations: brief.locations,
  platforms: brief.platforms,
  tier: brief.tier,
  budget_text: brief.budget,
  notes: brief.notes,
});

export const parseBriefSnapshot = (
  snapshot: Record<string, unknown> | null | undefined,
  campaign?: {
    searchQuery?: string | null;
    product?: string | null;
    budget_range?: string | null;
    preferred_platforms?: string[] | null;
  }
): BriefQuery => {
  const snap = snapshot ?? {};

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
    description: campaign?.searchQuery || campaign?.product || briefDefaults.description,
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
    searchQuery?: string | null;
    product?: string | null;
    budget_range?: string | null;
    campaign_name?: string | null;
  }
): BriefFormPayload => {
  const snap = snapshot ?? {};
  const parsed = parseBriefSnapshot(snapshot, {
    searchQuery: campaign.searchQuery,
    product: campaign.product,
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
    description: parsed.description,
    campaign:
      (typeof snap.campaign_name === "string" && snap.campaign_name) ||
      campaign.campaign_name ||
      "",
    locs: parsed.locs,
    budgetMin: budget.budgetMin,
    budgetMax: budget.budgetMax,
    currency: budget.currency,
    platforms: Array.isArray(snap.platforms)
      ? (snap.platforms as string[]).map((p) => titleize(p))
      : parsed.platforms,
    tier: parsed.tier,
  };
};
