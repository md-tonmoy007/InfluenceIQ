export const canDeleteCampaign = (status: string): boolean =>
  status === "draft" ||
  status === "completed" ||
  status === "failed" ||
  status === "cancelled";

export const canEditCampaignBrief = (status: string): boolean => status === "draft";
