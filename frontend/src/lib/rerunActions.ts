import type { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";
import { rerunCampaign, RerunOutreachError } from "@/lib/api";

type ToastFn = (message: string, options?: { type?: "success" | "error" | "info" }) => void;

type QuickRerunOptions = {
  campaignId: string;
  router: AppRouterInstance;
  toast: ToastFn;
  onStart?: () => void;
  confirmOutreach?: boolean;
};

export async function performQuickRerun({
  campaignId,
  router,
  toast,
  onStart,
  confirmOutreach = false,
}: QuickRerunOptions): Promise<void> {
  onStart?.();
  await rerunCampaign(campaignId, { startPipeline: true, confirmOutreach });
  toast("Rerunning search with your current brief.", { type: "success" });
  router.push(`/matching?campaignId=${encodeURIComponent(campaignId)}&rerun=1`);
}

export async function performQuickRerunWithConfirm(
  options: QuickRerunOptions
): Promise<void> {
  try {
    await performQuickRerun(options);
  } catch (error) {
    if (error instanceof RerunOutreachError) {
      if (
        confirm(
          `${error.message}\n\nContinue and replace current match results?`
        )
      ) {
        await performQuickRerun({ ...options, confirmOutreach: true });
        return;
      }
      return;
    }
    throw error;
  }
}

export async function performEditAndRerun(
  campaignId: string,
  router: AppRouterInstance,
  toast: ToastFn,
  onStart?: () => void
): Promise<void> {
  onStart?.();
  await rerunCampaign(campaignId, { startPipeline: false });
  toast("Brief unlocked for editing.", { type: "success" });
  router.push(`/briefs/new?campaignId=${encodeURIComponent(campaignId)}`);
}

export { RerunOutreachError };
