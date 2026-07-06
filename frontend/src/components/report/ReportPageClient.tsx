"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { getDeepAnalysisReport, getDeepAnalysisStatus } from "@/lib/api";
import { reportHref, shortlistHref } from "@/lib/routes";

type ReportPageClientProps = {
  influencerId: string;
  reportId?: string;
  runId?: string;
  campaignId?: string;
};

function safeStr(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function CoverageBadge({ status }: { status: string }) {
  const tone =
    status === "ok"
      ? "ok"
      : status === "partial" || status === "no_data" || status === "no_results" || status === "unavailable"
        ? "warn"
        : "bad";

  return <span className={`report-badge ${tone}`}>{status === "no_data" || status === "no_results" ? "unavailable" : status}</span>;
}

type TriggerStage = "starting" | "social" | "comments" | "trends" | "synthesizing" | "done" | "failed";
const STAGES: TriggerStage[] = ["starting", "social", "comments", "trends", "synthesizing"];
const STAGE_LABEL: Record<TriggerStage, string> = {
  starting: "Starting analysis",
  social: "Collecting posts",
  comments: "Collecting comments",
  trends: "Gathering trend signals",
  synthesizing: "Synthesizing report",
  done: "Report ready",
  failed: "Analysis failed",
};
const STAGE_HINT: Record<TriggerStage, string> = {
  starting: "Setting up the run and checking for fresh cached results.",
  social: "Pulling creator profile signals and recent content.",
  comments: "Reading audience responses to understand sentiment and authenticity.",
  trends: "Checking external interest and web visibility signals.",
  synthesizing: "Combining all signals into a campaign-ready report.",
  done: "Redirecting to the completed report.",
  failed: "Something went wrong while generating the report.",
};

function Section({ title, meta, children }: { title: string; meta?: string; children: React.ReactNode }) {
  return (
    <section className="report-section">
      <div className="report-section-head">
        <h2>{title}</h2>
        {meta ? <span>{meta}</span> : null}
      </div>
      {children}
    </section>
  );
}

export default function ReportPageClient({ influencerId, reportId, runId, campaignId }: ReportPageClientProps) {
  const router = useRouter();
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingStage, setLoadingStage] = useState<TriggerStage>(runId ? "starting" : "social");
  const [commentsAnalyzed, setCommentsAnalyzed] = useState<number>(0);

  useEffect(() => {
    if (reportId) {
      void getDeepAnalysisReport(influencerId, reportId)
        .then(setReport)
        .catch((err: Error) => setError(err.message));
      return;
    }

    if (!runId) {
      return;
    }

    let active = true;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;

    const poll = async () => {
      try {
        const result = await getDeepAnalysisStatus(influencerId, runId);
        if (!active) return;

        const runStatus = String(result.status ?? "");
        const coverage = (result.provider_coverage as Record<string, unknown> | null) ?? {};
        const hasCoverage = Object.keys(coverage).length > 0;
        const commentCount = Number(result.collected_comment_count ?? 0);
        setCommentsAnalyzed(commentCount);

        if (runStatus === "completed") {
          const completedReport = result.report as Record<string, unknown> | null | undefined;
          const nextReportId = completedReport ? String(completedReport.report_id ?? "") : "";
          setLoadingStage("done");
          if (nextReportId) {
            router.replace(reportHref(influencerId, nextReportId, campaignId));
            return;
          }
          setError("Analysis finished, but no report id was returned.");
          return;
        }

        if (runStatus === "failed") {
          setLoadingStage("failed");
          setError(String(result.failure_reason ?? result.error ?? "Deep analysis failed."));
          return;
        }

        if (!hasCoverage) setLoadingStage("social");
        else if (commentCount === 0) setLoadingStage("comments");
        else if (commentCount < 25) setLoadingStage("trends");
        else setLoadingStage("synthesizing");

        pollTimer = setTimeout(poll, 2500);
      } catch (err) {
        if (!active) return;
        setLoadingStage("failed");
        setError(err instanceof Error ? err.message : "Unable to load analysis status.");
      }
    };

    void poll();
    return () => {
      active = false;
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [campaignId, influencerId, reportId, router, runId]);

  const loadingStep = useMemo(() => Math.max(STAGES.indexOf(loadingStage), 0), [loadingStage]);

  if (!reportId && !runId) {
    return <div className="report-empty">Missing report id.</div>;
  }

  if (!reportId && runId && !report && !error) {
    return (
      <div className="report-page report-loading-shell" role="status" aria-live="polite">
        <div className="report-loading-card">
          <div className="report-loading-orb" aria-hidden="true" />
          <h1>{STAGE_LABEL[loadingStage]}</h1>
          <p>{STAGE_HINT[loadingStage]}</p>
          <div className="report-loading-meta">
            <span>Run ID: {runId.slice(0, 8)}…</span>
            <span>{commentsAnalyzed} comments analyzed</span>
          </div>
          <div className="report-loading-steps">
            {STAGES.map((stage, index) => {
              const state = loadingStep > index ? "done" : loadingStep === index ? "active" : "";
              return (
                <div key={stage} className={`report-loading-step ${state}`.trim()}>
                  <div className="tick">{loadingStep > index ? "✓" : ""}</div>
                  <div>
                    <strong>{STAGE_LABEL[stage]}</strong>
                    <span>{STAGE_HINT[stage]}</span>
                  </div>
                </div>
              );
            })}
          </div>
          {campaignId ? (
            <div className="report-loading-actions">
              <Link href={shortlistHref(campaignId)} className="report-link-btn">Back to shortlist</Link>
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  if (error) return <div className="report-empty">{error}</div>;
  if (!report) return <div className="report-empty">Loading report…</div>;

  const payload = (report.report_payload as Record<string, unknown> | undefined) ?? {};
  const creator = (payload.creator_summary as Record<string, unknown> | undefined) ?? {};
  const audience = (payload.audience_signals as Record<string, unknown> | undefined) ?? {};
  const popularity = (payload.popularity_signals as Record<string, unknown> | undefined) ?? {};
  const brandSafety = (payload.brand_safety_signals as Record<string, unknown> | undefined) ?? {};
  const strengths = (payload.key_strengths as string[] | undefined) ?? [];
  const risks = (payload.key_risks as string[] | undefined) ?? [];
  const citations = (payload.citations as Array<Record<string, unknown>> | undefined) ?? [];
  const postsAnalyzed = (payload.posts_analyzed as Array<Record<string, unknown>> | undefined) ?? [];
  const platformCoverage = (payload.platform_coverage as Record<string, Record<string, unknown>> | undefined) ?? {};
  const confidenceReasoning = safeStr(payload.confidence_reasoning, "");

  return (
    <div className="report-page">
      <section className="report-hero">
        <div>
          <div className="report-eyebrow">Deep analysis report</div>
          <h1>{safeStr(creator.name, "Creator report")}</h1>
          <p>
            Recommendation grade <strong>{safeStr(report.overall_grade)}</strong> with <strong>{safeStr(report.confidence)}</strong> confidence.
          </p>
          <div className="report-chip-row">
            <span className="report-chip">{safeStr(creator.primary_platform, "Platform unavailable")}</span>
            <span className="report-chip">{safeStr(creator.followers, "0")} followers</span>
            <span className="report-chip">{safeStr(payload.comments_analyzed, "0")} comments analyzed</span>
          </div>
        </div>
        {campaignId ? <Link href={shortlistHref(campaignId)} className="report-link-btn">Back to shortlist</Link> : null}
      </section>

      <div className="report-grid">
        <div className="report-main">
          <Section title="Recommendation">
            <p className="report-lead">{safeStr(payload.recommendation ?? report.recommendation, "No recommendation available.")}</p>
            {confidenceReasoning ? <p className="report-muted">{confidenceReasoning}</p> : null}
          </Section>

          <Section title="Campaign fit">
            <p>{safeStr(payload.campaign_fit_summary)}</p>
          </Section>

          <Section title="Brand safety & controversy">
            <p>{safeStr(report.brand_safety_summary, "No additional issues flagged.")}</p>
            <div className="report-badge-row">
              {brandSafety.web_sentiment ? <CoverageBadge status="ok" /> : <CoverageBadge status="unavailable" />}
            </div>
          </Section>

          {(strengths.length > 0 || risks.length > 0) && (
            <Section title="Key strengths & risks">
              <div className="report-two-col">
                <div className="report-list-card">
                  <h3>Strengths</h3>
                  {strengths.length ? <ul>{strengths.map((s, i) => <li key={`s-${i}`}>{s}</li>)}</ul> : <p className="report-muted">No strengths recorded.</p>}
                </div>
                <div className="report-list-card">
                  <h3>Risks</h3>
                  {risks.length ? <ul>{risks.map((r, i) => <li key={`r-${i}`}>{r}</li>)}</ul> : <p className="report-muted">No risks recorded.</p>}
                </div>
              </div>
            </Section>
          )}

          {postsAnalyzed.length > 0 && (
            <Section title="Evidence by post" meta={`${postsAnalyzed.length} analyzed`}>
              <div className="report-stack">
                {postsAnalyzed.map((post, i) => (
                  <article key={i} className="report-card report-post">
                    <div className="report-post-head">
                      <strong>{safeStr(post.platform, "Unknown platform")}</strong>
                      <span>
                        {post.status === "no_comments"
                          ? "No comments available"
                          : `${safeStr(post.like_count, "0")} likes · ${safeStr(post.comment_count, "0")} comments`}
                      </span>
                    </div>
                    <p>{safeStr(post.summary)}</p>
                  </article>
                ))}
              </div>
            </Section>
          )}

          {citations.length > 0 && (
            <Section title="Citations">
              <div className="report-stack">
                {citations.map((citation, i) => (
                  <article key={i} className="report-card report-citation">
                    <a href={safeStr(citation.url, "#")} target="_blank" rel="noreferrer">{safeStr(citation.title, safeStr(citation.url))}</a>
                  </article>
                ))}
              </div>
            </Section>
          )}
        </div>

        <aside className="report-side">
          <section className="report-card report-metrics">
            <h3>Audience sentiment & authenticity</h3>
            <div className="report-stat-list">
              <div><span>Audience sentiment</span><strong>{safeStr(audience.sentiment)}</strong></div>
              <div><span>Fake engagement risk</span><strong>{safeStr(audience.fake_engagement_risk)}</strong></div>
              <div><span>Comments analyzed</span><strong>{safeStr(payload.comments_analyzed, "0")}</strong></div>
            </div>
          </section>

          <section className="report-card report-metrics">
            <h3>Popularity & trend signals</h3>
            <div className="report-badge-row">
              {popularity.interest_over_time ? <CoverageBadge status="ok" /> : <CoverageBadge status="unavailable" />}
              {brandSafety.search_visibility ? <CoverageBadge status="ok" /> : <CoverageBadge status="unavailable" />}
            </div>
            <p className="report-muted">Google Trends and external visibility are shown when available for this creator.</p>
          </section>

          <section className="report-card report-metrics">
            <h3>Platform coverage</h3>
            {Object.keys(platformCoverage).length > 0 ? (
              <div className="report-stack compact">
                {Object.entries(platformCoverage).map(([platform, info]) => (
                  <div key={platform} className="report-coverage-row">
                    <div>
                      <strong>{platform}</strong>
                      <span>{safeStr(info.profile_status)} · {safeStr(info.posts_fetched, "0")} posts</span>
                    </div>
                    {!info.comments_fetched ? <CoverageBadge status="unavailable" /> : <CoverageBadge status="ok" />}
                  </div>
                ))}
              </div>
            ) : (
              <p className="report-muted">No platform data available.</p>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
