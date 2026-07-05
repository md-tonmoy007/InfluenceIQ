"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { getDeepAnalysisReport } from "@/lib/api";

function safeStr(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined) return fallback;
  return String(value);
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function CoverageBadge({ status }: { status: string }) {
  const color =
    status === "ok"
      ? "#10b981"
      : status === "partial" || status === "no_data" || status === "no_results"
        ? "#f59e0b"
        : "#ef4444";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: "4px",
        fontSize: "0.8rem",
        backgroundColor: `${color}20`,
        color,
        border: `1px solid ${color}40`,
        marginRight: "6px",
        marginBottom: "4px",
      }}
    >
      {status === "no_data" || status === "no_results" ? "unavailable" : status}
    </span>
  );
}

export default function ReportPage({ params }: { params: { influencerId: string } }) {
  const searchParams = useSearchParams();
  const reportId = searchParams.get("reportId");
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!reportId) {
      setError("Missing report id.");
      return;
    }
    void getDeepAnalysisReport(params.influencerId, reportId)
      .then(setReport)
      .catch((err: Error) => setError(err.message));
  }, [params.influencerId, reportId]);

  if (error) return <div className="report-page">{error}</div>;
  if (!report) return <div className="report-page">Loading report…</div>;

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
      <header>
        <h1>Deep Analysis Report</h1>
        <p>
          Grade{" "}
          <strong>{safeStr(report.overall_grade)}</strong> · Confidence{" "}
          <strong>{safeStr(report.confidence)}</strong>
        </p>
        {typeof creator.name === "string" && creator.name && (
          <p>
            Creator: <strong>{safeStr(creator.name)}</strong> · {safeStr(creator.primary_platform)} ·{" "}
            {safeStr(creator.followers, "0")} followers
          </p>
        )}
      </header>

      {/* Recommendation */}
      <Section title="Recommendation">
        <p className="recommendation-text">
          {safeStr(payload.recommendation ?? report.recommendation, "No recommendation available.")}
        </p>
        {confidenceReasoning && (
          <p className="confidence-reasoning" style={{ fontSize: "0.85rem", opacity: 0.7 }}>
            {confidenceReasoning}
          </p>
        )}
      </Section>

      {/* Campaign Fit */}
      <Section title="Campaign Fit">
        <p>{safeStr(payload.campaign_fit_summary)}</p>
      </Section>

      {/* Audience Sentiment & Authenticity */}
      <Section title="Audience Sentiment & Authenticity">
        <div className="metrics-row">
          <div className="metric">
            <span className="metric-label">Audience Sentiment</span>
            <span className="metric-value">{safeStr(audience.sentiment)}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Fake Engagement Risk</span>
            <span className="metric-value" style={{ color: Number(audience.fake_engagement_risk ?? 0) > 40 ? "#ef4444" : "#10b981" }}>
              {safeStr(audience.fake_engagement_risk)}
            </span>
          </div>
          <div className="metric">
            <span className="metric-label">Comments Analyzed</span>
            <span className="metric-value">{safeStr(payload.comments_analyzed, "0")}</span>
          </div>
        </div>
      </Section>

      {/* Popularity & Trend Signals */}
      <Section title="Popularity & Trend Signals">
        {popularity.interest_over_time ? (
          <div>
            <p>Google Trends data available for the past 12 months.</p>
            <CoverageBadge status="ok" />
          </div>
        ) : (
          <p>
            <CoverageBadge status="unavailable" /> Google Trends unavailable for this creator/topic.
          </p>
        )}
        {brandSafety.search_visibility ? (
          <div style={{ marginTop: "8px" }}>
            <p>External search visibility confirmed.</p>
            <CoverageBadge status="ok" />
          </div>
        ) : (
          <p>
            <CoverageBadge status="unavailable" /> Limited external search visibility.
          </p>
        )}
      </Section>

      {/* Brand Safety */}
      <Section title="Brand Safety & Controversy">
        <p>{safeStr(report.brand_safety_summary, "No additional issues flagged.")}</p>
        {brandSafety.web_sentiment ? (
          <CoverageBadge status="ok" />
        ) : (
          <CoverageBadge status="unavailable" />
        )}
      </Section>

      {/* Platform Coverage */}
      <Section title="Platform Coverage">
        {Object.keys(platformCoverage).length > 0 ? (
          <ul className="coverage-list">
            {Object.entries(platformCoverage).map(([platform, info]) => (
              <li key={platform}>
                <strong>{platform}</strong>: {safeStr(info.profile_status)} · {safeStr(info.posts_fetched, "0")} posts
                {!info.comments_fetched && (
                  <span style={{ color: "#f59e0b", marginLeft: "8px" }}>comments unavailable</span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p>No platform data available.</p>
        )}
      </Section>

      {/* Key Strengths & Risks */}
      {(strengths.length > 0 || risks.length > 0) && (
        <Section title="Key Strengths & Risks">
          {strengths.length > 0 && (
            <div>
              <h3 style={{ color: "#10b981" }}>Strengths</h3>
              <ul>
                {strengths.map((s, i) => (
                  <li key={`str-${i}`}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {risks.length > 0 && (
            <div>
              <h3 style={{ color: "#ef4444" }}>Risks</h3>
              <ul>
                {risks.map((r, i) => (
                  <li key={`risk-${i}`}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </Section>
      )}

      {/* Evidence by Post */}
      {postsAnalyzed.length > 0 && (
        <Section title={`Evidence by Post (${postsAnalyzed.length})`}>
          <div className="posts-table">
            {postsAnalyzed.map((post, i) => (
              <div key={i} className="post-row">
                <span className="post-platform">{safeStr(post.platform)}</span>
                <span className="post-metrics">
                  {post.status === "no_comments" ? (
                    <span style={{ color: "#f59e0b" }}>No comments available</span>
                  ) : (
                    <>
                      comments: {safeStr(post.comment_count, "0")} · sentiment:{" "}
                      {safeStr(post.sentiment_score)} · fake risk: {safeStr(post.fake_comment_risk)}
                    </>
                  )}
                </span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Citations */}
      {citations.length > 0 && (
        <Section title="Citations">
          <ul className="citations-list">
            {citations.map((c, i) => (
              <li key={`cite-${i}`}>
                {c.source === "post" ? (
                  <>
                    Post: {safeStr(c.platform)} · {safeStr((c.key_metrics as Record<string, unknown> | undefined)?.comment_count, "0")} comments
                  </>
                ) : (
                  <>External: search visibility evidence</>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Partial-data states */}
      {postsAnalyzed.some((p) => p.status === "no_comments") && (
        <p className="partial-notice" style={{ color: "#f59e0b", marginTop: "8px" }}>
          Some posts lack comments. Confidence reduced.
        </p>
      )}
      {Object.values(platformCoverage).some(
        (v) => v?.profile_status !== "ok"
      ) && (
        <p className="partial-notice" style={{ color: "#f59e0b", marginTop: "4px" }}>
          Some platform profiles were only partially fetched. Coverage may be incomplete.
        </p>
      )}

      <button type="button" onClick={() => window.print()}>
        Export PDF
      </button>
    </div>
  );
}
