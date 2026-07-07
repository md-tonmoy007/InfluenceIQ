"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { getDeepAnalysisReport, getDeepAnalysisStatus } from "@/lib/api";
import { reportHref, shortlistHref } from "@/lib/routes";
import { getCampaignWebSocketUrl } from "@/lib/websocket";

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
      : status === "partial" || status === "no_data" || status === "no_results" || status === "unavailable" || status === "no_posts"
        ? "warn"
        : "bad";

  return <span className={`report-badge ${tone}`}>{status === "no_data" || status === "no_results" || status === "no_posts" ? "unavailable" : status}</span>;
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

const WS_EVENT_TO_STAGE: Record<string, TriggerStage> = {
  "deep_analysis.started": "starting",
  "deep_analysis.social_collected": "comments",
  "deep_analysis.comments_collected": "trends",
  "deep_analysis.external_signals_collected": "synthesizing",
  "deep_analysis.report_ready": "done",
  "deep_analysis.failed": "failed",
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

function inferStageFromStatus(result: Record<string, unknown>): TriggerStage {
  const runStatus = String(result.status ?? "");
  if (runStatus === "failed") return "failed";
  if (runStatus === "completed") return "done";
  const stage = result.current_stage;
  if (typeof stage === "string") {
    if (stage === "starting" || stage === "social" || stage === "comments" || stage === "trends" || stage === "synthesizing") {
      return stage;
    }
    if (stage === "done") return "done";
  }
  return "social";
}

export default function ReportPageClient({ influencerId, reportId, runId, campaignId }: ReportPageClientProps) {
  const router = useRouter();
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingStage, setLoadingStage] = useState<TriggerStage>(runId ? "starting" : "social");
  const [commentsAnalyzed, setCommentsAnalyzed] = useState<number>(0);
  const lastEventIdRef = useRef<number>(0);

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

    const handleStatus = (result: Record<string, unknown>, fromWs: boolean) => {
      if (!active) return;
      const runStatus = String(result.status ?? "");
      const stage = inferStageFromStatus(result);
      setLoadingStage(stage);
      setCommentsAnalyzed(Number(result.collected_comment_count ?? 0));

      if (runStatus === "completed") {
        const completedReport = result.report as Record<string, unknown> | null | undefined;
        const nextReportId = completedReport ? String(completedReport.report_id ?? "") : "";
        if (nextReportId) {
          router.replace(reportHref(influencerId, nextReportId, campaignId));
          return;
        }
        setError("Analysis finished, but no report id was returned.");
        return;
      }

      if (runStatus === "failed") {
        setError(String(result.failure_reason ?? result.error ?? "Deep analysis failed."));
        return;
      }

      // Only continue polling if the WS path didn't already give us a
      // terminal state.
      if (!fromWs && (runStatus === "running" || runStatus === "queued")) {
        pollTimer = setTimeout(poll, 2500);
      }
    };

    const poll = async () => {
      try {
        const result = await getDeepAnalysisStatus(influencerId, runId);
        handleStatus(result, false);
      } catch (err) {
        if (!active) return;
        setLoadingStage("failed");
        setError(err instanceof Error ? err.message : "Unable to load analysis status.");
      }
    };

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let reconnectAttempt = 0;

    const connectWebSocket = () => {
      if (!campaignId) {
        // No campaign context → fall back to plain polling.
        pollTimer = setTimeout(poll, 2500);
        return;
      }
      try {
        const url = getCampaignWebSocketUrl(campaignId, { lastEventId: lastEventIdRef.current });
        socket = new WebSocket(url);
      } catch {
        if (!active) return;
        reconnectTimer = setTimeout(connectWebSocket, 1500 * ++reconnectAttempt);
        return;
      }
      socket.onmessage = (ev) => {
        if (!active) return;
        try {
          const event = JSON.parse(ev.data) as { type?: string; event_id?: number; payload?: Record<string, unknown> };
          if (typeof event.event_id === "number" && event.event_id > lastEventIdRef.current) {
            lastEventIdRef.current = event.event_id;
          }
          if (event.type && event.type in WS_EVENT_TO_STAGE) {
            const stage = WS_EVENT_TO_STAGE[event.type];
            if (stage === "done") {
              setLoadingStage("done");
              void (async () => {
                try {
                  const result = await getDeepAnalysisStatus(influencerId, runId);
                  handleStatus(result, true);
                } catch {
                  /* fall through to redirect */
                }
                const latest = await getDeepAnalysisStatus(influencerId, runId).catch(() => null);
                const completedReport = latest?.report as Record<string, unknown> | null | undefined;
                const nextReportId = completedReport ? String(completedReport.report_id ?? "") : "";
                if (nextReportId) {
                  router.replace(reportHref(influencerId, nextReportId, campaignId));
                }
              })();
              return;
            }
            if (stage === "failed") {
              setLoadingStage("failed");
              const reason = String(event.payload?.error ?? "Deep analysis failed.");
              setError(reason);
              return;
            }
            setLoadingStage(stage);
            if (typeof event.payload?.comment_count === "number") {
              setCommentsAnalyzed(event.payload.comment_count as number);
            } else if (typeof event.payload?.post_count === "number") {
              // social stage emits post_count
            }
          }
        } catch {
          /* ignore malformed events */
        }
      };
      socket.onerror = () => {
        if (!active) return;
      };
      socket.onclose = () => {
        if (!active) return;
        // Fall back to polling if WS closes before completion.
        reconnectAttempt = Math.min(reconnectAttempt + 1, 4);
        reconnectTimer = setTimeout(connectWebSocket, 1500 * reconnectAttempt);
      };
    };

    // Kick off the first poll to get the current status. Subsequent
    // progress comes from the WebSocket; if the WS isn't available
    // (no campaign context, or the socket fails) we fall back to plain
    // polling inside the handler.
    void (async () => {
      try {
        const result = await getDeepAnalysisStatus(influencerId, runId);
        if (!active) return;
        const stage = inferStageFromStatus(result);
        handleStatus(result, false);
        if (stage !== "done" && stage !== "failed") {
          connectWebSocket();
        }
      } catch (err) {
        if (!active) return;
        setLoadingStage("failed");
        setError(err instanceof Error ? err.message : "Unable to load analysis status.");
      }
    })();

    return () => {
      active = false;
      if (pollTimer) clearTimeout(pollTimer);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (socket) {
        try { socket.close(); } catch { /* ignore */ }
      }
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
  const sufficiency = (payload.data_sufficiency as Record<string, unknown> | undefined) ?? {};
  const hasData = sufficiency.has_data !== false && (Number(sufficiency.analyzed_posts ?? 0) > 0 || Number(sufficiency.total_comments ?? 0) > 0);
  const primaryPlatform = safeStr(creator.primary_platform, "");
  const showPlatformChip = primaryPlatform !== "";

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
            {showPlatformChip ? <span className="report-chip">{primaryPlatform}</span> : null}
            <span className="report-chip">{safeStr(creator.followers, "0")} followers</span>
            <span className="report-chip">{safeStr(payload.comments_analyzed, "0")} comments analyzed</span>
            {!hasData ? <span className="report-chip report-chip-warn">Insufficient evidence</span> : null}
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
              {hasData ? (
                brandSafety.flagged_count && Number(brandSafety.flagged_count) > 0 ? (
                  <CoverageBadge status="warn" />
                ) : brandSafety.web_sentiment ? (
                  <CoverageBadge status="ok" />
                ) : (
                  <CoverageBadge status="unavailable" />
                )
              ) : (
                <CoverageBadge status="unavailable" />
              )}
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
                {postsAnalyzed.map((post, i) => {
                  const postTitle = safeStr(
                    post.title,
                    safeStr(post.caption, safeStr(post.post_url, "Untitled post"))
                  );
                  const postBody = safeStr(post.caption, safeStr(post.title, safeStr(post.post_url)));
                  return (
                    <article key={i} className="report-card report-post">
                      <div className="report-post-head">
                        <strong>{postTitle}</strong>
                        <span>
                          {post.status === "no_comments"
                            ? "No comments available"
                            : `${safeStr(post.like_count, "0")} likes · ${safeStr(post.comment_count, "0")} comments`}
                        </span>
                      </div>
                      {postBody ? <p>{postBody}</p> : null}
                    </article>
                  );
                })}
              </div>
            </Section>
          )}

          {citations.length > 0 && (
            <Section title="Citations">
              <div className="report-stack">
                {citations.map((citation, i) => {
                  const metrics = (citation.key_metrics as Record<string, unknown> | undefined) ?? {};
                  const metricParts: string[] = [];
                  if (metrics.sentiment_score !== undefined) {
                    metricParts.push(`sentiment ${Math.round(Number(metrics.sentiment_score))}`);
                  }
                  if (metrics.fake_comment_risk !== undefined) {
                    metricParts.push(`fake risk ${Math.round(Number(metrics.fake_comment_risk) * 100) / 100}`);
                  }
                  if (metrics.comment_count !== undefined) {
                    metricParts.push(`${safeStr(metrics.comment_count, "0")} comments`);
                  }
                  const metricLine = metricParts.join(" · ");
                  const source = safeStr(citation.source, "source");
                  if (citation.source === "search_visibility") {
                    const urls = Array.isArray(citation.urls)
                      ? (citation.urls as unknown[]).filter((u): u is string => typeof u === "string" && u.length > 0)
                      : [];
                    if (urls.length === 0) return null;
                    return (
                      <article key={i} className="report-card report-citation">
                        <div className="report-citation-source">{source}</div>
                        <ul className="report-citation-list">
                          {urls.map((u, j) => (
                            <li key={j}>
                              <a href={u} target="_blank" rel="noreferrer">{u}</a>
                            </li>
                          ))}
                        </ul>
                      </article>
                    );
                  }
                  const title = safeStr(citation.title, "Untitled post");
                  const url = safeStr(citation.url, "");
                  return (
                    <article key={i} className="report-card report-citation">
                      <div className="report-citation-source">{source}</div>
                      {url ? (
                        <a className="report-citation-title" href={url} target="_blank" rel="noreferrer">{title}</a>
                      ) : (
                        <span className="report-citation-title">{title}</span>
                      )}
                      {metricLine ? <div className="report-citation-meta">{metricLine}</div> : null}
                    </article>
                  );
                })}
              </div>
            </Section>
          )}
        </div>

        <aside className="report-side">
          <section className="report-card report-metrics">
            <h3>Audience sentiment & authenticity</h3>
            <div className="report-stat-list">
              <div><span>Audience sentiment</span><strong>{hasData ? safeStr(audience.sentiment) : "—"}</strong></div>
              <div><span>Fake engagement risk</span><strong>{hasData ? safeStr(audience.fake_engagement_risk) : "—"}</strong></div>
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
                      <span>{safeStr(info.profile_status)} · {safeStr(info.posts_fetched, "0")} posts · {safeStr(info.comments_analyzed, "0")} comments</span>
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

