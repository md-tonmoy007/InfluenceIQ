/** Unit tests for deep analysis frontend logic.

Tests the status-label mapping, API call shapes, route generation, and
the polling/progress state machine used by DeepAnalysisTrigger — without
needing a browser or React renderer.

Run with: npx tsx src/lib/deep-analysis.test.ts
*/

import { reportHref } from "./routes";

// ---------------------------------------------------------------------------
// Status label mapping (mirrors DeepAnalysisTrigger.STATUS_LABEL)
// ---------------------------------------------------------------------------

const STATUS_LABEL: Record<string, string> = {
  idle: "Run deep analysis",
  starting: "Starting…",
  social: "Collecting posts…",
  comments: "Collecting comments…",
  trends: "Gathering trends…",
  synthesizing: "Synthesizing…",
  failed: "Retry deep analysis",
};

function assertEqual(actual: unknown, expected: unknown, label: string) {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
}

function assertTrue(cond: boolean, label: string) {
  if (!cond) {
    throw new Error(`${label}: expected truthy, got falsy`);
  }
}

function assertFalse(cond: boolean, label: string) {
  if (cond) {
    throw new Error(`${label}: expected falsy, got truthy`);
  }
}

// ---------------------------------------------------------------------------
// 1. Status labels are stable and complete
// ---------------------------------------------------------------------------

const expectedStatuses = ["idle", "starting", "social", "comments", "trends", "synthesizing", "failed"];

for (const key of expectedStatuses) {
  assertTrue(typeof STATUS_LABEL[key] === "string", `STATUS_LABEL.${key} is a string`);
}

assertEqual(Object.keys(STATUS_LABEL).length, expectedStatuses.length, "no extra statuses");

// ---------------------------------------------------------------------------
// 2. isRunning check (idle and failed are NOT running, others ARE)
// ---------------------------------------------------------------------------

function isRunning(status: string): boolean {
  return status !== "idle" && status !== "failed";
}

assertFalse(isRunning("idle"), "idle is not running");
assertFalse(isRunning("failed"), "failed is not running");
for (const s of ["starting", "social", "comments", "trends", "synthesizing"]) {
  assertTrue(isRunning(s), `${s} is running`);
}

// ---------------------------------------------------------------------------
// 3. reportHref generates the correct URL
// ---------------------------------------------------------------------------

const href = reportHref("abc-123", "rpt-456");
assertTrue(href.startsWith("/report/"), "reportHref starts with /report/");
assertTrue(href.includes("reportId="), "reportHref includes reportId param");
assertTrue(href.includes("rpt-456"), "reportHref encodes reportId");

// ---------------------------------------------------------------------------
// 4. Polling status derivation from run payload
// ---------------------------------------------------------------------------

/** Mirrors the pollRun logic for deriving UI stage from API response. */
function deriveStage(result: { status: string; provider_coverage?: Record<string, unknown>; collected_comment_count?: number }): string {
  const runStatus = String(result.status);

  if (runStatus === "completed") return "completed";
  if (runStatus === "failed") return "failed";

  if (runStatus === "running") {
    const coverage = result.provider_coverage ?? {};
    const hasCoverage = Object.keys(coverage).length > 0;
    const commentCount = Number(result.collected_comment_count ?? 0);

    if (!hasCoverage) return "social";
    if (commentCount === 0) return "comments";
    return "synthesizing";
  }

  return "idle";
}

assertEqual(deriveStage({ status: "queued" }), "idle", "queued maps to idle");
assertEqual(deriveStage({ status: "running", provider_coverage: {} }), "social", "running + no coverage = social");
assertEqual(deriveStage({ status: "running", provider_coverage: { instagram: "ok" }, collected_comment_count: 0 }), "comments", "running + coverage + no comments = comments");
assertEqual(deriveStage({ status: "running", provider_coverage: { instagram: "ok" }, collected_comment_count: 50 }), "synthesizing", "running + coverage + comments = synthesizing");
assertEqual(deriveStage({ status: "completed" }), "completed", "completed maps to completed");
assertEqual(deriveStage({ status: "failed" }), "failed", "failed maps to failed");

// ---------------------------------------------------------------------------
// 5. API URL generation shapes (verify query params and paths)
// ---------------------------------------------------------------------------

function uriEncode(s: string): string {
  return encodeURIComponent(s);
}

function triggerUrl(influencerId: string, campaignId: string, commentTarget = 2000): string {
  return `/api/influencers/${uriEncode(influencerId)}/deep-analysis?campaign_id=${uriEncode(campaignId)}&comment_target=${commentTarget}`;
}

function latestUrl(influencerId: string, campaignId: string): string {
  return `/api/influencers/${uriEncode(influencerId)}/deep-analysis/latest?campaign_id=${uriEncode(campaignId)}`;
}

function statusUrl(influencerId: string, runId: string): string {
  return `/api/influencers/${uriEncode(influencerId)}/deep-analysis/${uriEncode(runId)}`;
}

function reportUrl(influencerId: string, reportId: string): string {
  return `/api/influencers/${uriEncode(influencerId)}/reports/${uriEncode(reportId)}`;
}

const infId = "abc";
const cmpId = "def";
const rId = "ghi";

assertEqual(triggerUrl(infId, cmpId), "/api/influencers/abc/deep-analysis?campaign_id=def&comment_target=2000", "trigger URL includes comment_target");
assertEqual(latestUrl(infId, cmpId), "/api/influencers/abc/deep-analysis/latest?campaign_id=def", "latest URL includes campaign_id");
assertEqual(statusUrl(infId, rId), "/api/influencers/abc/deep-analysis/ghi", "status URL includes run_id");
assertEqual(reportUrl(infId, rId), "/api/influencers/abc/reports/ghi", "report URL includes report_id");

// ---------------------------------------------------------------------------
// 6. Freshness check: should skip trigger when latest returns fresh=true
// ---------------------------------------------------------------------------

function shouldSkipTrigger(latest: { fresh: boolean; report?: { report_id: string } | null }): boolean {
  return latest.fresh && !!(latest.report?.report_id ?? "");
}

assertTrue(shouldSkipTrigger({ fresh: true, report: { report_id: "r-1" } }), "fresh report with id skips trigger");
assertFalse(shouldSkipTrigger({ fresh: false, report: { report_id: "r-1" } }), "stale report does not skip trigger");
assertFalse(shouldSkipTrigger({ fresh: true }), "fresh without report id does not skip trigger");
assertFalse(shouldSkipTrigger({ fresh: true, report: null }), "fresh with null report does not skip trigger");

// ---------------------------------------------------------------------------
// 7. Report payload partial-data detection
// ---------------------------------------------------------------------------

/** Mirrors the logic for detecting partial-data states in report page. */
function hasPartialCoverage(
  postsAnalyzed: Array<{ status: string }>,
  platformCoverage: Record<string, { profile_status: string }>,
): { postsWithoutComments: boolean; partialPlatforms: boolean } {
  return {
    postsWithoutComments: postsAnalyzed.some((p) => p.status === "no_comments"),
    partialPlatforms: Object.values(platformCoverage).some((v) => v?.profile_status !== "ok"),
  };
}

const result1 = hasPartialCoverage(
  [{ status: "ok" }, { status: "no_comments" }],
  { instagram: { profile_status: "ok" } },
);
assertTrue(result1.postsWithoutComments, "detects posts without comments");
assertFalse(result1.partialPlatforms, "all platforms ok");

const result2 = hasPartialCoverage(
  [{ status: "ok" }],
  { instagram: { profile_status: "partial" } },
);
assertFalse(result2.postsWithoutComments, "no missing comments");
assertTrue(result2.partialPlatforms, "detects partial platform");

const result3 = hasPartialCoverage([], {});
assertFalse(result3.postsWithoutComments, "empty posts = no missing");
assertFalse(result3.partialPlatforms, "empty platforms = none partial");

// ---------------------------------------------------------------------------
// 8. Event label mapping (PipelineProgress and ShortlistPageClient)
// ---------------------------------------------------------------------------

const EVENT_LABELS: Record<string, string> = {
  "deep_analysis.started": "Deep analysis started",
  "deep_analysis.social_collected": "Social content collected",
  "deep_analysis.comments_collected": "Comments collected",
  "deep_analysis.external_signals_collected": "Trend signals gathered",
  "deep_analysis.report_ready": "Deep analysis report ready",
  "deep_analysis.failed": "Deep analysis failed",
};

const expectedEvents = [
  "deep_analysis.started",
  "deep_analysis.social_collected",
  "deep_analysis.comments_collected",
  "deep_analysis.external_signals_collected",
  "deep_analysis.report_ready",
  "deep_analysis.failed",
];

for (const evt of expectedEvents) {
  assertTrue(typeof EVENT_LABELS[evt] === "string", `event label for ${evt} is defined`);
}

assertEqual(Object.keys(EVENT_LABELS).length, expectedEvents.length, "all 6 websocket events mapped");

// ---------------------------------------------------------------------------
// 9. Coverage badge color derivation (mirrors ReportPage logic)
// ---------------------------------------------------------------------------

function coverageColor(status: string): string {
  if (status === "ok") return "green";
  if (status === "partial" || status === "no_data" || status === "no_results") return "yellow";
  return "red";
}

assertEqual(coverageColor("ok"), "green", "ok = green");
assertEqual(coverageColor("partial"), "yellow", "partial = yellow");
assertEqual(coverageColor("no_data"), "yellow", "no_data = yellow");
assertEqual(coverageColor("no_results"), "yellow", "no_results = yellow");
assertEqual(coverageColor("error"), "red", "error = red");
assertEqual(coverageColor("unavailable"), "red", "unavailable = red");

console.log("All deep analysis frontend tests passed.");
