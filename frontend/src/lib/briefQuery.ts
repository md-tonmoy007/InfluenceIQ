import { briefDefaults } from "../data/briefDefaults";

export type BriefQuery = {
  brand: string;
  description: string;
  locs: string[];
  platforms: string[];
  tier: string;
  budget: string;
};

type SearchParamInput = URLSearchParams | Record<string, string | string[] | undefined>;

const readParam = (source: SearchParamInput, key: string) => {
  if (typeof (source as URLSearchParams).get === "function") {
    return (source as URLSearchParams).get(key) ?? "";
  }
  const record = source as Record<string, string | string[] | undefined>;
  const value = record[key];
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
};

const parseList = (value: string, fallback: string[]) => {
  const source = value || fallback.join(",");
  return source.split(",").filter(Boolean);
};

export const parseBriefSearchParams = (searchParams: SearchParamInput): BriefQuery => {
  const brand = readParam(searchParams, "brand") || briefDefaults.brand;
  const description = readParam(searchParams, "q") || briefDefaults.description;
  const locs = parseList(readParam(searchParams, "locs"), briefDefaults.locs);
  const platforms = parseList(
    readParam(searchParams, "platforms"),
    briefDefaults.platforms
  );
  const tier = readParam(searchParams, "tier") || briefDefaults.tier;
  const budget = readParam(searchParams, "budget") || briefDefaults.budget;

  return {
    brand,
    description,
    locs,
    platforms,
    tier,
    budget,
  };
};

export const buildBriefSearchParams = (brief: BriefQuery) => {
  const params = new URLSearchParams();
  params.set("brand", brief.brand);
  params.set("q", brief.description);
  params.set("locs", brief.locs.join(","));
  params.set("platforms", brief.platforms.join(","));
  params.set("tier", brief.tier);
  params.set("budget", brief.budget);
  return params;
};
