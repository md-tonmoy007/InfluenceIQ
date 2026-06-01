export type CampaignPipelineEvent =
  | {
      name: "query.generated";
      campaignId: string;
      query: string;
      timestamp: string;
    }
  | {
      name: "url.discovered";
      campaignId: string;
      url: string;
      timestamp: string;
    }
  | {
      name: "page.scraped";
      campaignId: string;
      url: string;
      timestamp: string;
    }
  | {
      name: "influencer.found";
      campaignId: string;
      influencerId: string;
      timestamp: string;
    }
  | {
      name: "score.calculated";
      campaignId: string;
      influencerId: string;
      score: number;
      timestamp: string;
    }
  | {
      name: "pipeline.completed";
      campaignId: string;
      timestamp: string;
    }
  | {
      name: "pipeline.failed";
      campaignId: string;
      error: string;
      timestamp: string;
    };
