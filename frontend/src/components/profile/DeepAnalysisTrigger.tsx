"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getLatestDeepAnalysis, triggerDeepAnalysis } from "@/lib/api";
import { reportHref, reportRunHref } from "@/lib/routes";

type DeepAnalysisTriggerProps = {
  influencerId: string;
  campaignId: string;
  className?: string;
  viewClassName?: string;
  rerunClassName?: string;
  label?: string;
  deepAnalysisReady?: boolean;
  deepAnalysisBlockReason?: string | null;
};

type TriggerStatus = "idle" | "starting" | "social" | "comments" | "trends" | "synthesizing" | "failed";

const STATUS_LABEL: Record<TriggerStatus, string> = {
  idle: "Run deep analysis",
  starting: "Starting…",
  social: "Collecting posts…",
  comments: "Collecting comments…",
  trends: "Gathering trends…",
  synthesizing: "Synthesizing…",
  failed: "Retry deep analysis",
};

export default function DeepAnalysisTrigger({
  influencerId,
  campaignId,
  className = "row-cta",
  viewClassName,
  rerunClassName,
  label = "Run deep analysis",
  deepAnalysisReady,
  deepAnalysisBlockReason,
}: DeepAnalysisTriggerProps) {
  const router = useRouter();
  const [status, setStatus] = useState<TriggerStatus>("idle");
  const [latestReportId, setLatestReportId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    if (deepAnalysisReady === false) {
      return () => {
        active = false;
      };
    }

    void getLatestDeepAnalysis(influencerId, campaignId)
      .then((latest) => {
        if (!active) return;
        const report = latest.report as Record<string, unknown> | undefined;
        const reportId = latest.fresh && report ? String(report.report_id ?? "") : "";
        setLatestReportId(reportId || null);
      })
      .catch(() => {
        if (!active) return;
        setLatestReportId(null);
      });

    return () => {
      active = false;
    };
  }, [campaignId, deepAnalysisReady, influencerId]);

  const handleClick = async (force: boolean) => {
    if (status !== "idle" && status !== "failed") {
      return;
    }

    try {
      setStatus("starting");

      const start = await triggerDeepAnalysis(influencerId, campaignId, 2000, { force });

      // When ``force=false`` and a fresh cached report exists the API
      // returns ``status: "completed"`` with a ``report.report_id`` —
      // there is no run id because no Celery task was dispatched. Jump
      // straight to the rendered report.
      const startReport = start.report as Record<string, unknown> | undefined;
      if (start.status === "completed" && startReport && startReport.report_id) {
        setLatestReportId(String(startReport.report_id));
        setStatus("idle");
        router.push(reportHref(influencerId, String(startReport.report_id), campaignId));
        return;
      }

      const runId = String(start.run_id ?? "");
      if (!runId) {
        setStatus("failed");
        return;
      }

      setLatestReportId(null);
      setStatus("social");
      router.push(reportRunHref(influencerId, runId, campaignId));
    } catch {
      setStatus("failed");
    }
  };

  const buttonLabel = STATUS_LABEL[status] ?? label;
  const isRunning = status !== "idle" && status !== "failed";
  const rerunButtonClassName = rerunClassName ?? className;
  const viewButtonClassName = viewClassName ?? className;

  if (deepAnalysisReady === false) {
    return (
      <div
        className="deep-analysis-actions"
        style={{ display: "flex", flexDirection: "column", gap: "8px", width: "100%" }}
      >
        <button type="button" className={viewButtonClassName} disabled>
          Deep analysis unavailable
        </button>
        {deepAnalysisBlockReason ? (
          <div style={{ fontSize: "11px", lineHeight: 1.45, color: "var(--muted)" }}>
            {deepAnalysisBlockReason}
          </div>
        ) : null}
      </div>
    );
  }

  if (!isRunning && latestReportId) {
    return (
      <div
        className="deep-analysis-actions"
        style={{ display: "flex", flexDirection: "column", gap: "10px", width: "100%" }}
      >
        <Link
          href={reportHref(influencerId, latestReportId, campaignId)}
          className={viewButtonClassName}
        >
          View deep analysis
        </Link>
        <button
          type="button"
          className={rerunButtonClassName}
          onClick={() => void handleClick(true)}
        >
          Rerun deep analysis
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      className={rerunButtonClassName}
      disabled={isRunning}
      onClick={() => void handleClick(false)}
    >
      {buttonLabel}
    </button>
  );
}
