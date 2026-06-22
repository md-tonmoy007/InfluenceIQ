import type { InfluencerRecommendation } from "@/types/influencer";

export type SupportedPlatform = "instagram" | "youtube" | "tiktok" | "facebook";

// Metrics the pipeline does not capture (follower count, true engagement rate,
// dollar rate) arrive as 0/"" and are shown as a dash rather than a fake value.
export const DASH = "—";

export const normalizePlatform = (value: string): SupportedPlatform => {
  const lowered = value.toLowerCase();
  if (lowered === "youtube" || lowered === "tiktok" || lowered === "facebook") {
    return lowered;
  }
  return "instagram";
};

export const formatCompactNumber = (value: number) =>
  new Intl.NumberFormat(undefined, {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);

export const formatPercent = (value: number) => `${value.toFixed(1)}%`;

export const titleize = (value: string) =>
  value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());

export const avatarFromName = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("") || "IQ";

export const estimateViews = (followers: number, engagementRate: number) =>
  Math.max(0, Math.round(followers * Math.max(engagementRate, 1) * 0.04));

export const tierFromFollowers = (followers: number) => {
  if (followers <= 0) return DASH;
  if (followers >= 500_000) return "Premium";
  if (followers >= 50_000) return "Established";
  return "Rising";
};

export const gradientByPlatform: Record<SupportedPlatform, string> = {
  instagram: "linear-gradient(135deg,#6a4cff,#c054ff)",
  youtube: "linear-gradient(135deg,#ef4444,#f97316)",
  tiktok: "linear-gradient(135deg,#111827,#06b6d4)",
  facebook: "linear-gradient(135deg,#2563eb,#60a5fa)",
};

export const hostLabel = (rawUrl: string) => {
  try {
    return new URL(rawUrl).hostname.replace(/^www\./, "");
  } catch {
    return rawUrl;
  }
};

export const extractTags = (item: InfluencerRecommendation) => {
  const tags: string[] = [];
  tags.push(titleize(item.platform));
  Object.entries(item.subScores)
    .filter(([key, value]) => key !== "data_source_count" && value >= 75)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .forEach(([key]) => tags.push(titleize(key)));
  if (!item.brandSafetyFlags.length) {
    tags.push("Brand safe");
  }
  item.citations.slice(0, 2).forEach((citation) => tags.push(hostLabel(citation)));
  return Array.from(new Set(tags)).slice(0, 4);
};

export const extractCategory = (item: InfluencerRecommendation) => {
  const metadata = item.sourcePayload.metadata;
  if (typeof metadata === "object" && metadata && typeof (metadata as Record<string, unknown>).category === "string") {
    return String((metadata as Record<string, unknown>).category);
  }
  const tags = extractTags(item);
  return tags.slice(0, 2).join(" · ") || "Creator";
};

export const extractLocation = (item: InfluencerRecommendation) => {
  const sourcePayload = item.sourcePayload;
  const directLocation = sourcePayload.location;
  if (typeof directLocation === "string" && directLocation.trim()) {
    return directLocation;
  }

  const identity = sourcePayload.identity;
  if (typeof identity === "object" && identity && typeof (identity as Record<string, unknown>).location === "string") {
    return String((identity as Record<string, unknown>).location);
  }

  return "Location unavailable";
};

export const estimateRateNumber = (item: InfluencerRecommendation) => {
  if (typeof item.rate === "string") {
    const numeric = Number.parseInt(item.rate.replace(/[^0-9]/g, ""), 10);
    if (Number.isFinite(numeric)) {
      return numeric;
    }
  }
  return Math.max(250, Math.round(item.followers * 0.01));
};

// Display wrappers that degrade to a dash when the underlying metric is absent.
export const displayFollowers = (item: InfluencerRecommendation) =>
  item.followers > 0 ? formatCompactNumber(item.followers) : DASH;

export const displayViews = (item: InfluencerRecommendation) =>
  item.followers > 0
    ? formatCompactNumber(estimateViews(item.followers, item.engagementRate))
    : DASH;

export const displayEngagement = (item: InfluencerRecommendation) =>
  item.engagementRate > 0 ? formatPercent(item.engagementRate) : DASH;

export const displayRate = (item: InfluencerRecommendation) =>
  item.followers > 0 || item.rate
    ? `$${estimateRateNumber(item).toLocaleString()}`
    : DASH;
