import type { BrandProfile } from "@/lib/api";

export const INDUSTRY_OPTIONS = [
  "Outdoor & activewear",
  "Beauty & skincare",
  "Food & beverage",
  "Tech & SaaS",
  "Fashion & apparel",
  "Fitness & wellness",
  "Travel & hospitality",
  "Gaming & entertainment",
] as const;

export const COMPANY_SIZE_OPTIONS = ["1–10", "11–50", "51–200", "201–1000", "1000+"] as const;

export const COUNTRY_OPTIONS = [
  "United States",
  "Canada",
  "United Kingdom",
  "India",
  "Bangladesh",
  "Global",
] as const;

export const GOAL_OPTIONS = [
  { id: "awareness", label: "Brand Awareness" },
  { id: "launch", label: "Product Launch" },
  { id: "sales", label: "Sales" },
  { id: "event", label: "Event Promotion" },
  { id: "ltp", label: "Long-term Partnership" },
] as const;

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

const BRIEF_GOAL_LABELS: Record<string, string> = {
  awareness: "Brand Awareness",
  launch: "Product Launch",
  sales: "Sales Conversion",
  event: "Event Promotion",
  ltp: "Long-term Partnership",
};

export const onboardingGoalToBriefGoal = (goal: string): string | null =>
  BRIEF_GOAL_LABELS[goal] ?? null;

const PLATFORM_LABELS: Record<string, string> = Object.fromEntries(
  PLATFORM_OPTIONS.map((platform) => [platform.id, platform.label])
);

export const onboardingPlatformToBriefPlatform = (platform: string): string | null =>
  PLATFORM_LABELS[platform.toLowerCase()] ?? null;

export const budgetSliderPercent = (budget: number): number =>
  ((budget - BUDGET_MIN) / (BUDGET_MAX - BUDGET_MIN)) * 100;

export const briefDefaultsFromBrandProfile = (
  profile: BrandProfile
): {
  brand: string;
  category: string;
  goal: string;
  platforms: string[];
  budgetMax: number;
} => {
  const firstGoal = profile.goals?.[0];
  const goal = firstGoal ? onboardingGoalToBriefGoal(firstGoal) ?? "" : "";

  const platforms =
    profile.platforms
      ?.map(onboardingPlatformToBriefPlatform)
      .filter((p): p is string => p !== null) ?? [];

  const budgetMax = profile.monthly_budget ?? 12000;

  return {
    brand: profile.brand_name,
    category: profile.industry ?? "",
    goal,
    platforms,
    budgetMax,
  };
};
