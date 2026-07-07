import type { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";
import { cancelCampaign, rerunCampaign, RerunOutreachError } from "@/lib/api";

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

/**
 * Cancel a running campaign and immediately re-dispatch it.
 *
 * The backend refuses a direct rerun while status is `running` (HTTP 409,
 * `backend/api/routers/campaigns.py:466-470`), so the user has no
 * self-service escape from a stuck pipeline via `performQuickRerun`.
 * This helper performs the required cancel-first sequence:
 *   1. `POST /api/campaigns/{id}/cancel`  — sets status to `cancelled`
 *      and revokes in-flight task ids.
 *   2. `POST /api/campaigns/{id}/rerun?start_pipeline=true` with
 *      `X-Confirm-Rerun: true` (covers campaigns that already have
 *      outreach records).
 *
 * Already-completed work (scored influencers, crawl sources) is
 * preserved in the DB across the cycle, so the rerun converges
 * quickly to a terminal state.
 */
export async function performCancelAndRerun(
  campaignId: string,
  router: AppRouterInstance,
  toast: ToastFn,
  onStart?: () => void
): Promise<void> {
  onStart?.();
  await cancelCampaign(campaignId);
  // The cancel-then-rerun flow is itself the user confirmation, so
  // forward `X-Confirm-Rerun` to skip the outreach-confirm modal that
  // `performQuickRerunWithConfirm` would otherwise trigger.
  await rerunCampaign(campaignId, { startPipeline: true, confirmOutreach: true });
  toast("Run cancelled — restarting the search.", { type: "success" });
  router.push(`/matching?campaignId=${encodeURIComponent(campaignId)}&rerun=1`);
}

export { RerunOutreachError };
