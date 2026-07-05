"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { getDeepAnalysisStatus, getLatestDeepAnalysis, triggerDeepAnalysis } from "@/lib/api";
import { reportHref } from "@/lib/routes";

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
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const navigateToReport = useCallback(
    (reportId: string) => {
      stopPolling();
      router.push(reportHref(influencerId, reportId));
    },
    [influencerId, router, stopPolling]
  );

  const pollRun = useCallback(
    async (runId: string) => {
      const result = await getDeepAnalysisStatus(influencerId, runId);
      const runStatus = String(result.status ?? "");

      if (runStatus === "completed") {
        const report = result.report as Record<string, unknown> | null | undefined;
        const reportId = report ? String(report.report_id ?? "") : "";
        if (reportId) {
          navigateToReport(reportId);
          return true;
        }
      }

      if (runStatus === "failed") {
        stopPolling();
        setStatus("failed");
        return true;
      }

      // Derive staged progress from the run status and provider_coverage
      if (runStatus === "running") {
        const coverage = (result.provider_coverage as Record<string, unknown> | null) ?? {};
        const hasCoverage = Object.keys(coverage).length > 0;
        const commentCount = Number(result.collected_comment_count ?? 0);

        if (!hasCoverage) {
          setStatus("social");
        } else if (commentCount === 0) {
          setStatus("comments");
        } else {
          // We don't get fine-grained stage info from the polling endpoint,
          // so infer trending/synthesizing based on timing
          setStatus("synthesizing");
        }
      }

      return false;
    },
    [influencerId, navigateToReport, stopPolling]
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
      if (await pollRun(runId)) {
        return;
      }

      stopPolling();
      pollRef.current = setInterval(() => {
        void pollRun(runId);
      }, 2500);
    } catch {
      stopPolling();
      setStatus("failed");
    }
  };

  const buttonLabel = STATUS_LABEL[status] ?? label;
  const isRunning = status !== "idle" && status !== "failed";

  return (
    <button
      type="button"
      className={className}
      style={
        className === "row-cta"
          ? { marginTop: "8px", background: "none", border: "none", cursor: "pointer", padding: 0 }
          : undefined
      }
      disabled={isRunning}
      onClick={() => void handleClick()}
    >
      {buttonLabel}
    </button>
  );
}
