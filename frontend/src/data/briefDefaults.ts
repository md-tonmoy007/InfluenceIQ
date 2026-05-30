export type BriefDefaults = {
  brand: string;
  product: string;
  category: string;
  goal: string;
  ages: string[];
  gender: string;
  locs: string[];
  platforms: string[];
  tier: string;
  budget: string;
};

export const briefDefaults: BriefDefaults = {
  brand: "Northwind Outdoor",
  product: "SS26 Trail Capsule",
  category: "Outdoor & Activewear",
  goal: "Product Launch",
  ages: ["18–24", "25–34"],
  gender: "All",
  locs: ["USA", "Canada"],
  platforms: ["Instagram", "YouTube"],
  tier: "Established",
  budget: "$2,500 – $12,000 USD",
};
