"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";

import { getLatestDeepAnalysis, triggerDeepAnalysis } from "@/lib/api";
import { reportHref, reportRunHref } from "@/lib/routes";

type DeepAnalysisTriggerProps = {
  influencerId: string;
  campaignId: string;
  className?: string;
  label?: string;
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
  label = "Run deep analysis",
}: DeepAnalysisTriggerProps) {
  const router = useRouter();
  const [status, setStatus] = useState<TriggerStatus>("idle");

  const navigateToReport = useCallback(
    (reportId: string) => {
      router.push(reportHref(influencerId, reportId, campaignId));
    },
    [campaignId, influencerId, router]
  );

  const handleClick = async () => {
    if (status !== "idle" && status !== "failed") {
      return;
    }

    try {
      setStatus("starting");

      // Check for existing fresh report first
      const latest = await getLatestDeepAnalysis(influencerId, campaignId);
      if (latest.fresh) {
        const report = latest.report as Record<string, unknown> | undefined;
        const reportId = report ? String(report.report_id ?? "") : "";
        if (reportId) {
          navigateToReport(reportId);
          return;
        }
      }

      // No fresh report, start a new run
      const start = await triggerDeepAnalysis(influencerId, campaignId);

      // If the backend returned a cached report inline
      const inlineReport = start.report as Record<string, unknown> | null | undefined;
      if (inlineReport) {
        const reportId = String(inlineReport.report_id ?? "");
        if (reportId) {
          navigateToReport(reportId);
          return;
        }
      }

      const runId = String(start.run_id ?? "");
      if (!runId) {
        setStatus("failed");
        return;
      }

      setStatus("social");
      router.push(reportRunHref(influencerId, runId, campaignId));
    } catch {
      setStatus("failed");
    }
  };

  const buttonLabel = STATUS_LABEL[status] ?? label;
  const isRunning = status !== "idle" && status !== "failed";

  return (
    <button
      type="button"
      className={className}
      disabled={isRunning}
      onClick={() => void handleClick()}
    >
      {buttonLabel}
    </button>
  );
}
