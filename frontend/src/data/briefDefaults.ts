export type BriefDefaults = {
  brand: string;
  description: string;
  locs: string[];
  platforms: string[];
  tier: string;
  budget: string;
};

export const briefDefaults: BriefDefaults = {
  brand: "Northwind Outdoor",
  description: "SS26 Trail Capsule, an outdoor & activewear product launch",
  locs: ["USA", "Canada"],
  platforms: ["Instagram", "YouTube"],
  tier: "Established",
  budget: "$2,500 – $12,000 USD",
};
