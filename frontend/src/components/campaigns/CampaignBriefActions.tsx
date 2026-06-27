"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { deleteCampaign, duplicateCampaign } from "@/lib/api";
import { canDeleteCampaign, canEditCampaignBrief } from "@/lib/campaignLifecycle";
import { useToast } from "@/components/ui/ToastProvider";
import "./campaign-brief-actions.css";

type CampaignBriefActionsProps = {
  campaignId: string;
  status: string;
  label?: string;
  showEdit?: boolean;
  onDeleted?: () => void;
};

export default function CampaignBriefActions({
  campaignId,
  status,
  label = "this campaign",
  showEdit = true,
  onDeleted,
}: CampaignBriefActionsProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [duplicating, setDuplicating] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDuplicate = async () => {
    if (duplicating) return;
    setDuplicating(true);
    try {
      const duplicated = await duplicateCampaign(campaignId);
      toast("Campaign duplicated as a new draft.", { type: "success" });
      router.push(`/briefs/new?campaignId=${encodeURIComponent(duplicated.campaignId)}`);
    } catch (error) {
      toast(
        error instanceof Error ? error.message : "Unable to duplicate campaign.",
        { type: "error" }
      );
    } finally {
      setDuplicating(false);
    }
  };

  const handleDelete = async () => {
    if (deleting || !canDeleteCampaign(status)) return;
    if (!confirm(`Delete "${label}"? This cannot be undone.`)) return;

    setDeleting(true);
    try {
      await deleteCampaign(campaignId);
      toast("Campaign deleted.", { type: "success" });
      if (onDeleted) {
        onDeleted();
      } else {
        router.push("/briefs");
      }
    } catch (error) {
      toast(
        error instanceof Error ? error.message : "Unable to delete campaign.",
        { type: "error" }
      );
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="campaign-brief-actions">
      {showEdit && canEditCampaignBrief(status) ? (
        <Link
          className="campaign-brief-action"
          href={`/briefs/new?campaignId=${encodeURIComponent(campaignId)}`}
        >
          <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
            <path d="M12 20h9" />
            <path d="M16.5 3.5a2.1 2.1 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
          </svg>
          Edit brief
        </Link>
      ) : null}
      <button
        type="button"
        className="campaign-brief-action"
        disabled={duplicating}
        onClick={() => void handleDuplicate()}
      >
        <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
          <rect x="8" y="8" width="12" height="12" rx="2" />
          <path d="M4 16V6a2 2 0 0 1 2-2h10" />
        </svg>
        {duplicating ? "Duplicating…" : "Duplicate"}
      </button>
      {canDeleteCampaign(status) ? (
        <button
          type="button"
          className="campaign-brief-action danger"
          disabled={deleting}
          onClick={() => void handleDelete()}
        >
          <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
            <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
          </svg>
          {deleting ? "Deleting…" : "Delete"}
        </button>
      ) : null}
    </div>
  );
}
