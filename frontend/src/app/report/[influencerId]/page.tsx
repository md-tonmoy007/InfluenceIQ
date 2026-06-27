"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { getDeepAnalysisReport } from "@/lib/api";

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

  return (
    <div className="report-page">
      <header>
        <h1>Deep Analysis Report</h1>
        <p>Grade {String(report.overall_grade ?? "—")} · Confidence {String(report.confidence ?? "—")}</p>
      </header>
      <section>
        <h2>Recommendation</h2>
        <p>{String(report.recommendation ?? payload.recommendation ?? "No recommendation available.")}</p>
      </section>
      <section>
        <h2>Audience sentiment</h2>
        <p>{String(report.audience_sentiment ?? "—")}</p>
      </section>
      <section>
        <h2>Fake engagement risk</h2>
        <p>{String(report.fake_engagement_risk ?? "—")}</p>
      </section>
      <section>
        <h2>Brand safety</h2>
        <p>{String(report.brand_safety_summary ?? "No additional issues flagged.")}</p>
      </section>
      <button type="button" onClick={() => window.print()}>
        Export PDF
      </button>
    </div>
  );
}
