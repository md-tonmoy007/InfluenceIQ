"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { getDeepAnalysisStatus, triggerDeepAnalysis } from "@/lib/api";
import { reportHref } from "@/lib/routes";

type DeepAnalysisTriggerProps = {
  influencerId: string;
  campaignId: string;
  className?: string;
  label?: string;
};

type TriggerStatus = "idle" | "starting" | "running" | "failed";

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

  const pollRun = useCallback(
    async (runId: string) => {
      const result = await getDeepAnalysisStatus(influencerId, runId);
      const runStatus = String(result.status ?? "");

      if (runStatus === "completed") {
        const report = result.report as Record<string, unknown> | null | undefined;
        const reportId = report ? String(report.report_id ?? "") : "";
        if (reportId) {
          stopPolling();
          router.push(reportHref(influencerId, reportId));
          return true;
        }
      }

      if (runStatus === "failed") {
        stopPolling();
        setStatus("failed");
        return true;
      }

      return false;
    },
    [influencerId, router, stopPolling]
  );

  const handleClick = async () => {
    if (status === "starting" || status === "running") {
      return;
    }

    try {
      setStatus("starting");
      const start = await triggerDeepAnalysis(influencerId, campaignId);
      const runId = String(start.run_id ?? "");
      if (!runId) {
        setStatus("failed");
        return;
      }

      setStatus("running");
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

  const buttonLabel =
    status === "starting"
      ? "Starting…"
      : status === "running"
        ? "Analyzing…"
        : status === "failed"
          ? "Retry deep analysis"
          : label;

  return (
    <button
      type="button"
      className={className}
      style={
        className === "row-cta"
          ? { marginTop: "8px", background: "none", border: "none", cursor: "pointer", padding: 0 }
          : undefined
      }
      disabled={status === "starting" || status === "running"}
      onClick={() => void handleClick()}
    >
      {buttonLabel}
    </button>
  );
}
