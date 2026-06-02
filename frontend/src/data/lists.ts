export type SavedList = {
  id: string;
  name: string;
  status: "active" | "draft";
  count: number;
  created: string;
  reach: string;
  engagement: string;
  match: string;
  glow: string;
  avatars: Array<{ i: string; bg: string }>;
  mix: Array<{ p: "instagram" | "youtube" | "tiktok" | "facebook"; n: number }>;
};

export type SavedListRow = {
  name: string;
  handle: string;
  plat: "instagram" | "youtube" | "tiktok" | "facebook";
  avI: string;
  avBg: string;
  cat: string;
  fol: string;
  eng: string;
  rate: string;
  match: number;
};

export const savedLists: SavedList[] = [
  {
    id: "ramadan-2026",
    name: "Ramadan Campaign 2026",
    status: "active",
    count: 14,
    created: "Apr 22, 2026",
    reach: "3.42M",
    engagement: "6.1%",
    match: "89.6",
    glow: "glow-v",
    avatars: [
      { i: "MG", bg: "linear-gradient(135deg,#6a4cff,#c054ff)" },
      { i: "PS", bg: "linear-gradient(135deg,#f59e0b,#ef4444)" },
      { i: "ZM", bg: "linear-gradient(135deg,#7c3aed,#4338ca)" },
      { i: "LP", bg: "linear-gradient(135deg,#ec4899,#f472b6)" },
    ],
    mix: [
      { p: "instagram", n: 8 },
      { p: "tiktok", n: 4 },
      { p: "youtube", n: 2 },
    ],
  },
  {
    id: "ss26-trail",
    name: "SS26 Trail Capsule shortlist",
    status: "draft",
    count: 9,
    created: "May 02, 2026",
    reach: "1.81M",
    engagement: "5.4%",
    match: "92.1",
    glow: "glow-cy",
    avatars: [
      { i: "JC", bg: "linear-gradient(135deg,#14b8d4,#2563eb)" },
      { i: "AT", bg: "linear-gradient(135deg,#2bb673,#5ad6a0)" },
      { i: "MW", bg: "linear-gradient(135deg,#06b6d4,#3b82f6)" },
      { i: "MG", bg: "linear-gradient(135deg,#6a4cff,#c054ff)" },
    ],
    mix: [
      { p: "instagram", n: 5 },
      { p: "youtube", n: 4 },
    ],
  },
  {
    id: "gen-z-fintech",
    name: "Gen Z fintech — Q3 push",
    status: "active",
    count: 21,
    created: "Mar 18, 2026",
    reach: "5.07M",
    engagement: "7.8%",
    match: "87.2",
    glow: "glow-c",
    avatars: [
      { i: "TB", bg: "linear-gradient(135deg,#8b5cf6,#6366f1)" },
      { i: "KT", bg: "linear-gradient(135deg,#475569,#1e293b)" },
      { i: "HW", bg: "linear-gradient(135deg,#d97706,#fbbf24)" },
      { i: "AB", bg: "linear-gradient(135deg,#059669,#14b8a6)" },
    ],
    mix: [
      { p: "tiktok", n: 12 },
      { p: "instagram", n: 6 },
      { p: "youtube", n: 3 },
    ],
  },
];

export const savedListRows: SavedListRow[] = [
  {
    name: "Priya Sharma",
    handle: "@priyacooks",
    plat: "instagram",
    avI: "PS",
    avBg: "linear-gradient(135deg,#f59e0b,#ef4444)",
    cat: "Food · Plant-based",
    fol: "524K",
    eng: "7.3%",
    rate: "$3,100",
    match: 96,
  },
  {
    name: "Lila Park",
    handle: "@lilaglow",
    plat: "instagram",
    avI: "LP",
    avBg: "linear-gradient(135deg,#ec4899,#f472b6)",
    cat: "Beauty · K-beauty",
    fol: "341K",
    eng: "6.2%",
    rate: "$2,200",
    match: 94,
  },
  {
    name: "Zara Malik",
    handle: "@zaramaliktravels",
    plat: "instagram",
    avI: "ZM",
    avBg: "linear-gradient(135deg,#7c3aed,#4338ca)",
    cat: "Travel · South Asia",
    fol: "238K",
    eng: "5.8%",
    rate: "$1,650",
    match: 92,
  },
  {
    name: "Maya Greene",
    handle: "@mayagreene",
    plat: "instagram",
    avI: "MG",
    avBg: "linear-gradient(135deg,#6a4cff,#c054ff)",
    cat: "Lifestyle · Wellness",
    fol: "412K",
    eng: "5.2%",
    rate: "$2,400",
    match: 91,
  },
  {
    name: "Aiden Brooks",
    handle: "@aidencooks",
    plat: "tiktok",
    avI: "AB",
    avBg: "linear-gradient(135deg,#059669,#14b8a6)",
    cat: "Food · Vegan",
    fol: "93K",
    eng: "9.4%",
    rate: "$680",
    match: 89,
  },
  {
    name: "Hannah Wells",
    handle: "@hannahwellscloset",
    plat: "tiktok",
    avI: "HW",
    avBg: "linear-gradient(135deg,#d97706,#fbbf24)",
    cat: "Fashion · Thrift",
    fol: "47K",
    eng: "11.2%",
    rate: "$420",
    match: 88,
  },
  {
    name: "Sofia Reyes",
    handle: "@sofreyes",
    plat: "instagram",
    avI: "SR",
    avBg: "linear-gradient(135deg,#ff7a59,#ff4d8a)",
    cat: "Fitness · Pilates",
    fol: "287K",
    eng: "6.8%",
    rate: "$1,800",
    match: 86,
  },
];
