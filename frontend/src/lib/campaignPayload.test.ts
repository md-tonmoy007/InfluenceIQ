import { buildCampaignPayloadFromQuery, stripBudgetMentions } from "./campaignPayload";

const assertEqual = (actual: unknown, expected: unknown, label: string) => {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
};

assertEqual(
  stripBudgetMentions("Eco-friendly cleaning $2k budget"),
  "Eco-friendly cleaning",
  "strips a trailing $-amount budget phrase"
);

assertEqual(
  stripBudgetMentions("financial influencer for genz, 2k dollar budget"),
  "financial influencer for genz",
  "strips a trailing 'N dollar budget' phrase and its leading comma"
);

assertEqual(
  stripBudgetMentions("skincare brand with a $500-$2000 budget"),
  "skincare brand",
  "strips a budget range phrase"
);

assertEqual(
  stripBudgetMentions("budget of $10,000 for protein powder"),
  "protein powder",
  "strips a leading 'budget of $X' phrase and dangling connector"
);

assertEqual(
  stripBudgetMentions("top skincare influencers"),
  "top skincare influencers",
  "leaves budget-free text unchanged"
);

const payload = buildCampaignPayloadFromQuery("Eco-friendly cleaning $2k budget");
assertEqual(payload.description, "Eco-friendly cleaning", "quick-create description excludes budget text");
assertEqual(payload.notes, "Eco-friendly cleaning $2k budget", "notes keep the original raw query");
