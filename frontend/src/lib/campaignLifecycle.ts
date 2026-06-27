export const canDeleteCampaign = (status: string): boolean =>
  status === "draft" ||
  status === "completed" ||
  status === "failed" ||
  status === "cancelled";

export const canEditCampaignBrief = (status: string): boolean => status === "draft";

export const canRerunCampaign = (status: string): boolean =>
  status === "completed" ||
  status === "failed" ||
  status === "cancelled" ||
  status === "partial";

export const isTerminalCampaign = (status: string): boolean => canRerunCampaign(status);
