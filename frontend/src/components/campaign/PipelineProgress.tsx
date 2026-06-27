"use client";

import type { CampaignState } from "@/lib/api";

type PipelineProgressProps = {
  state: CampaignState | null;
  events?: Array<{ type: string; payload?: Record<string, unknown> }>;
};

const PHASE_LABELS: Record<string, string> = {
  initializing: "Initializing",
  query_generation: "Generating queries",
  searching: "Searching the web",
  crawling: "Fetching sources",
  extracting: "Extracting creators",
  enrichment: "Enriching platform data",
  scoring: "Scoring influencers",
  completed: "Completed",
  partial: "Partial results ready",
  failed: "Failed",
  cancelled: "Cancelled",
};

function eventLabel(type: string): string {
  const labels: Record<string, string> = {
    "campaign.started": "Campaign started",
    "campaign.completed": "Campaign completed",
    "campaign.partial": "Partial campaign results ready",
    "campaign.failed": "Campaign failed",
    "campaign.cancelled": "Campaign cancelled",
    "query.generation.completed": "Queries generated",
    "search.executed": "Search completed",
    "page.fetched": "Page fetched",
    "content.extracted": "Content extracted",
    "influencer.found": "Influencer found",
    "platform.enriched": "Platform data enriched",
    "score.calculated": "Score calculated",
    "deep_analysis.started": "Deep analysis started",
    "deep_analysis.report_ready": "Deep analysis report ready",
  };
  return labels[type] ?? type.replaceAll(".", " ");
}

export function PipelineProgress({ state, events = [] }: PipelineProgressProps) {
  const phase = state?.phase ?? state?.status ?? "initializing";
  const discovered = Number(state?.urls_discovered ?? 0);
  const processed = Number(state?.urls_processed ?? state?.urls_scraped ?? 0);
  const scores = Number(state?.scores_computed ?? 0);
  const progress = discovered > 0 ? Math.min(100, Math.round((processed / discovered) * 100)) : 0;

  return (
    <div className="pipeline-progress">
      <div className="pipeline-progress__header">
        <strong>{PHASE_LABELS[String(phase)] ?? String(phase)}</strong>
        <span>{String(state?.status ?? "running")}</span>
      </div>
      <div className="pipeline-progress__bar" aria-hidden="true">
        <div className="pipeline-progress__fill" style={{ width: `${progress}%` }} />
      </div>
      <div className="pipeline-progress__stats">
        <span>{processed}/{discovered} sources</span>
        <span>{scores} scores</span>
        <span>{Number(state?.platforms_enriched ?? 0)} enriched</span>
      </div>
      {events.length > 0 ? (
        <ul className="pipeline-progress__events">
          {events.slice(-5).map((event, index) => (
            <li key={`${event.type}-${index}`}>{eventLabel(event.type)}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
