export type CampaignPipelineEventType =
  | "pipeline.started"
  | "query.generated"
  | "url.discovered"
  | "page.scraped"
  | "influencer.found"
  | "score.calculated"
  | "pipeline.completed"
  | "pipeline.failed"
  | "heartbeat"
  | string;

export type CampaignPipelineEvent = {
  event_id: number;
  type: CampaignPipelineEventType;
  campaign_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
};

export const isTerminalPipelineEvent = (event: CampaignPipelineEvent) =>
  event.type === "pipeline.completed" || event.type === "pipeline.failed";
