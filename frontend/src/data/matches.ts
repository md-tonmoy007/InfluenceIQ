export type ShortlistMatch = {
  rank: number;
  name: string;
  handle: string;
  platform: "instagram" | "youtube" | "tiktok" | "facebook";
  avatar: string;
  avBg: string;
  match: number;
  followers: string;
  engagement: string;
  avgViews: string;
  rate: string;
  tier: "Rising" | "Established" | "Premium";
  tags: string[];
  verified: boolean;
  reason: string;
};

export const shortlistMatches: ShortlistMatch[] = [
  {
    rank: 1,
    name: "Maya Greene",
    handle: "@mayagreene",
    platform: "instagram",
    avatar: "MG",
    avBg: "linear-gradient(135deg,#6a4cff,#c054ff)",
    match: 96,
    followers: "412K",
    engagement: "5.2%",
    avgViews: "124K",
    rate: "$2,400",
    tier: "Established",
    tags: ["Outdoor", "Trail running", "Sustainability"],
    verified: true,
    reason:
      "<em>Hyper-aligned audience</em> — 78% of her followers are women 25–34 in the US/Canada, with strong outdoor & sustainability interest.",
  },
  {
    rank: 2,
    name: "Jordan Chen",
    handle: "@runwithjordan",
    platform: "youtube",
    avatar: "JC",
    avBg: "linear-gradient(135deg,#14b8d4,#2563eb)",
    match: 94,
    followers: "198K",
    engagement: "4.1%",
    avgViews: "88K",
    rate: "$1,950",
    tier: "Established",
    tags: ["Trail running", "Endurance", "Gear reviews"],
    verified: true,
    reason:
      "<em>Authentic gear-review voice</em> — long-form trail-running content with 92% PNW + Rockies viewership. Past launches drove 6.3× ROAS.",
  },
  {
    rank: 3,
    name: "Ava Thompson",
    handle: "@avamoves",
    platform: "instagram",
    avatar: "AT",
    avBg: "linear-gradient(135deg,#2bb673,#5ad6a0)",
    match: 91,
    followers: "156K",
    engagement: "8.9%",
    avgViews: "62K",
    rate: "$1,400",
    tier: "Established",
    tags: ["Strength", "Daily routine", "Outdoor"],
    verified: false,
    reason:
      "<em>Exceptional engagement</em> — 8.9% ER on Reels, double the category benchmark. Story-driven posts match your \"no haul\" preference.",
  },
  {
    rank: 4,
    name: "Marcus Webb",
    handle: "@webb.travels",
    platform: "instagram",
    avatar: "MW",
    avBg: "linear-gradient(135deg,#06b6d4,#3b82f6)",
    match: 88,
    followers: "112K",
    engagement: "5.5%",
    avgViews: "48K",
    rate: "$1,050",
    tier: "Established",
    tags: ["Adventure", "Slow travel", "PNW"],
    verified: false,
    reason:
      "<em>Geo-perfect</em> — Pacific Northwest base, audience skews 70% North America. Rate sits comfortably under your mid-range cap.",
  },
  {
    rank: 5,
    name: "Sofia Reyes",
    handle: "@sofreyes",
    platform: "instagram",
    avatar: "SR",
    avBg: "linear-gradient(135deg,#ff7a59,#ff4d8a)",
    match: 87,
    followers: "287K",
    engagement: "6.8%",
    avgViews: "104K",
    rate: "$2,200",
    tier: "Established",
    tags: ["Pilates", "Activewear", "Wellness"],
    verified: true,
    reason:
      "<em>Adjacent-fit reach</em> — wellness + activewear overlap broadens reach beyond core trail audience without diluting brand tone.",
  },
];
