import { briefDefaults } from "../data/briefDefaults";

export type BriefQuery = {
  brand: string;
  product: string;
  category: string;
  goals: string[];
  ages: string[];
  gender: string;
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
  const product = readParam(searchParams, "product") || briefDefaults.product;
  const category = readParam(searchParams, "category") || briefDefaults.category;
  const goals = parseList(readParam(searchParams, "goals"), briefDefaults.goals);
  const ages = parseList(readParam(searchParams, "ages"), briefDefaults.ages);
  const gender = readParam(searchParams, "gender") || briefDefaults.gender;
  const locs = parseList(readParam(searchParams, "locs"), briefDefaults.locs);
  const platforms = parseList(
    readParam(searchParams, "platforms"),
    briefDefaults.platforms
  );
  const tier = readParam(searchParams, "tier") || briefDefaults.tier;
  const budget = readParam(searchParams, "budget") || briefDefaults.budget;

  return {
    brand,
    product,
    category,
    goals,
    ages,
    gender,
    locs,
    platforms,
    tier,
    budget,
  };
};

export const buildBriefSearchParams = (brief: BriefQuery) => {
  const params = new URLSearchParams();
  params.set("brand", brief.brand);
  params.set("product", brief.product);
  params.set("category", brief.category);
  params.set("goals", brief.goals.join(","));
  params.set("ages", brief.ages.join(","));
  params.set("gender", brief.gender);
  params.set("locs", brief.locs.join(","));
  params.set("platforms", brief.platforms.join(","));
  params.set("tier", brief.tier);
  params.set("budget", brief.budget);
  return params;
};
