import type { BrandProfile } from "@/lib/api";

export const CATEGORY_OPTIONS = [
  "Fashion & Apparel",
  "Outdoor & Activewear",
  "Beauty & Skincare",
  "Food & Beverage",
  "Tech & Gadgets",
  "Health & Wellness",
  "Travel & Hospitality",
  "Home & Lifestyle",
  "Gaming & Entertainment",
  "Finance & Fintech",
] as const;

/** @deprecated Use CATEGORY_OPTIONS */
export const INDUSTRY_OPTIONS = CATEGORY_OPTIONS;

export const COMPANY_SIZE_OPTIONS = ["1–10", "11–50", "51–200", "201–1000", "1000+"] as const;

export const COUNTRY_OPTIONS = [
  "United States",
  "Canada",
  "United Kingdom",
  "India",
  "Bangladesh",
  "Global",
] as const;

export const CAMPAIGN_GOAL_OPTIONS = [
  {
    id: "awareness",
    label: "Brand Awareness",
    description: "Maximize reach & impressions",
  },
  {
    id: "launch",
    label: "Product Launch",
    description: "Drive buzz on a new drop",
  },
  {
    id: "sales",
    label: "Sales Conversion",
    description: "Track clicks & purchases",
  },
  {
    id: "event",
    label: "Event Promotion",
    description: "Fill seats & RSVPs",
  },
  {
    id: "ltp",
    label: "Long-term Partnership",
    description: "Build ongoing creator relationships",
  },
] as const;

/** @deprecated Use CAMPAIGN_GOAL_OPTIONS */
export const GOAL_OPTIONS = CAMPAIGN_GOAL_OPTIONS;

export const PLATFORM_OPTIONS = [
  { id: "instagram", label: "Instagram", desc: "Reels, carousels, stories" },
  { id: "tiktok", label: "TikTok", desc: "Short-form, trending" },
  { id: "youtube", label: "YouTube", desc: "Long-form, Shorts" },
  { id: "facebook", label: "Facebook", desc: "Reels, communities" },
] as const;

export const BUDGET_MIN = 500;
export const BUDGET_MAX = 50000;
export const BUDGET_STEP = 500;
export const DEFAULT_MONTHLY_BUDGET = 12500;

const GOAL_ID_TO_LABEL: Record<string, string> = Object.fromEntries(
  CAMPAIGN_GOAL_OPTIONS.map((goal) => [goal.id, goal.label])
);

const GOAL_LABEL_TO_ID: Record<string, string> = Object.fromEntries(
  CAMPAIGN_GOAL_OPTIONS.map((goal) => [goal.label, goal.id])
);

const LEGACY_CATEGORY_MAP: Record<string, string> = {
  "Outdoor & activewear": "Outdoor & Activewear",
  "Beauty & skincare": "Beauty & Skincare",
  "Food & beverage": "Food & Beverage",
  "Tech & SaaS": "Tech & Gadgets",
  "Fashion & apparel": "Fashion & Apparel",
  "Fitness & wellness": "Health & Wellness",
  "Travel & hospitality": "Travel & Hospitality",
  "Gaming & entertainment": "Gaming & Entertainment",
};

const PLATFORM_LABELS: Record<string, string> = Object.fromEntries(
  PLATFORM_OPTIONS.map((platform) => [platform.id, platform.label])
);

export const brandGoalIdToLabel = (goalId: string): string | null =>
  GOAL_ID_TO_LABEL[goalId] ?? null;

export const brandGoalIdsToLabels = (goalIds: string[]): string[] =>
  goalIds
    .map(brandGoalIdToLabel)
    .filter((label): label is string => label !== null);

export const brandGoalLabelsToIds = (labels: string[]): string[] =>
  labels
    .map((label) => GOAL_LABEL_TO_ID[label])
    .filter((id): id is string => Boolean(id));

/** @deprecated Use brandGoalIdToLabel */
export const onboardingGoalToBriefGoal = brandGoalIdToLabel;

export const onboardingPlatformToBriefPlatform = (platform: string): string | null =>
  PLATFORM_LABELS[platform.toLowerCase()] ?? null;

export const normalizeCategory = (value: string): string => {
  const trimmed = value.trim();
  if (!trimmed) return "";
  if ((CATEGORY_OPTIONS as readonly string[]).includes(trimmed)) {
    return trimmed;
  }
  return LEGACY_CATEGORY_MAP[trimmed] ?? trimmed;
};

export const budgetSliderPercent = (budget: number): number =>
  ((budget - BUDGET_MIN) / (BUDGET_MAX - BUDGET_MIN)) * 100;

export const briefDefaultsFromBrandProfile = (
  profile: BrandProfile
): {
  brand: string;
  category: string;
  goals: string[];
  platforms: string[];
  budgetMax: number;
} => {
  const goals = brandGoalIdsToLabels(profile.goals ?? []);

  const platforms =
    profile.platforms
      ?.map(onboardingPlatformToBriefPlatform)
      .filter((p): p is string => p !== null) ?? [];

  const budgetMax = profile.monthly_budget ?? 12000;

  return {
    brand: profile.brand_name,
    category: normalizeCategory(profile.industry ?? ""),
    goals,
    platforms,
    budgetMax,
  };
};
