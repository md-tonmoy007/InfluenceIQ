import { campaignHref, shortlistHref } from "./routes";

const campaignId = "2b53be2e-95dd-4879-9479-57db754f7b04";

const assertEqual = (actual: string, expected: string, label: string) => {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${expected}, got ${actual}`);
  }
};

assertEqual(
  campaignHref(campaignId, "draft"),
  `/briefs/new?campaignId=${encodeURIComponent(campaignId)}`,
  "draft campaigns open the brief editor"
);

for (const status of ["running", "pending", "completed", "failed"]) {
  assertEqual(
    campaignHref(campaignId, status),
    shortlistHref(campaignId),
    `${status} campaigns open the shortlist`
  );
}

assertEqual(
  shortlistHref(campaignId),
  `/shortlist?campaignId=${encodeURIComponent(campaignId)}`,
  "shortlist href encodes campaign id"
);
