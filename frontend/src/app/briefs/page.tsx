"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppShell from "@/components/shell/AppShell";
import { duplicateCampaign, listCampaigns, type CampaignListItem } from "@/lib/api";
import { campaignHref } from "@/lib/routes";
import { useToast } from "@/components/ui/ToastProvider";
import "../briefs.css";

type Filter = "all" | "active" | "drafts" | "completed";

const formatDate = (iso: string | null): string => {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
};

const formatTimeAgo = (iso: string | null): string => {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const now = Date.now();
  const diff = now - then;
  const day = 24 * 60 * 60 * 1000;
  if (diff < day) return "Today";
  if (diff < 2 * day) return "Yesterday";
  if (diff < 7 * day) {
    const days = Math.floor(diff / day);
    return `${days} days ago`;
  }
  return formatDate(iso);
};

const platformList = (campaign: CampaignListItem): string => {
  if (!campaign.preferred_platforms || campaign.preferred_platforms.length === 0) {
    return "—";
  }
  return campaign.preferred_platforms
    .map((platform) => {
      const trimmed = platform.toLowerCase();
      if (trimmed === "instagram") return "IG";
      if (trimmed === "youtube") return "YT";
      if (trimmed === "tiktok") return "TT";
      if (trimmed === "facebook") return "FB";
      return trimmed.slice(0, 2).toUpperCase();
    })
    .join(" · ");
};

const statusLabel = (status: string): { label: string; className: string } => {
  switch (status) {
    case "completed":
      return { label: "Completed", className: "complete" };
    case "running":
    case "pending":
      return { label: "Active", className: "active" };
    case "failed":
      return { label: "Failed", className: "draft" };
    case "draft":
      return { label: "Draft", className: "draft" };
    default:
      return { label: status, className: "active" };
  }
};

const goalTag = (campaign: CampaignListItem): string | null => {
  const snapshot = campaign.brief_snapshot;
  if (snapshot && Array.isArray(snapshot.goals) && snapshot.goals.length) {
    return (snapshot.goals as string[]).join(", ");
  }
  if (snapshot && typeof snapshot.goal === "string" && snapshot.goal) {
    return snapshot.goal;
  }
  if (campaign.search_query) return "Search";
  return null;
};

const matchesCampaignFilter = (campaign: CampaignListItem, filter: Filter): boolean => {
  switch (filter) {
    case "all":
      return true;
    case "active":
      return campaign.status === "running" || campaign.status === "pending";
    case "drafts":
      return campaign.status === "draft";
    case "completed":
      return campaign.status === "completed";
    default:
      return true;
  }
};

export default function BriefsPage() {
  return (
    <AppShell
      crumbs={[{ label: "Workspace" }, { label: "Campaign Briefs", current: true }]}
      showSearch={false}
    >
      <main className="content">
        <BriefsContent />
      </main>
    </AppShell>
  );
}

function BriefsContent() {
  const router = useRouter();
  const { toast } = useToast();
  const [campaigns, setCampaigns] = useState<CampaignListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>("all");
  const [duplicatingId, setDuplicatingId] = useState<string | null>(null);

  const loadCampaigns = useCallback(() => {
    setLoading(true);
    return listCampaigns({ limit: 100 })
      .then((result) => {
        setCampaigns(result.items);
      })
      .catch((error) => {
        toast(
          error instanceof Error ? error.message : "Unable to load your campaigns.",
          { type: "error" }
        );
      })
      .finally(() => {
        setLoading(false);
      });
  }, [toast]);

  useEffect(() => {
    void loadCampaigns();
  }, [loadCampaigns]);

  const handleDuplicate = async (campaignId: string) => {
    if (duplicatingId) return;
    setDuplicatingId(campaignId);
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
      setDuplicatingId(null);
    }
  };

  const filtered = campaigns.filter((campaign) =>
    matchesCampaignFilter(campaign, filter)
  );

  const counts = {
    all: campaigns.length,
    active: campaigns.filter((c) => matchesCampaignFilter(c, "active")).length,
    drafts: campaigns.filter((c) => matchesCampaignFilter(c, "drafts")).length,
    completed: campaigns.filter((c) => matchesCampaignFilter(c, "completed")).length,
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>
            Campaign <span className="ac">briefs.</span>
          </h1>
          <p className="sub">
            A timeline of every brief you&apos;ve submitted to the matching engine. Open one to see its shortlist or duplicate it for a new push.
          </p>
        </div>
        <Link href="/briefs/new" className="btn btn-primary btn-sm">
          <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Start New Campaign Brief
        </Link>
      </div>

      <div className="seg-tabs">
        {(
          [
            { id: "all" as const, label: "All" },
            { id: "active" as const, label: "Active" },
            { id: "drafts" as const, label: "Drafts" },
            { id: "completed" as const, label: "Completed" },
          ]
        ).map((tab) => (
          <button
            key={tab.id}
            className={filter === tab.id ? "active" : ""}
            type="button"
            onClick={() => setFilter(tab.id)}
          >
            {tab.label} <span className="count">{counts[tab.id]}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <BriefsSkeleton />
      ) : filtered.length === 0 ? (
        <div className="brief-list">
          <Link className="new-brief" href="/briefs/new">
            <span className="pp">+</span>
            <div>
              <div className="t">Start a new campaign brief</div>
              <div className="s">
                Describe your product, audience and budget — the matcher takes it from there.
              </div>
            </div>
          </Link>
        </div>
      ) : (
        <div className="brief-list">
          {filtered.map((campaign) => {
            const isDraft = campaign.status === "draft";
            const target = campaignHref(campaign.id, campaign.status);
            const goal = goalTag(campaign);
            const status = statusLabel(campaign.status);
            const label =
              campaign.campaign_name || campaign.product || "Untitled campaign";
            const initial = label.trim()[0]?.toUpperCase() ?? "C";
            const isLive =
              campaign.status === "running" || campaign.status === "pending";
            const matches = campaign.influencer_count ?? 0;
            const topScore = campaign.top_match_score;
            const shortlisted = campaign.shortlisted_count ?? 0;
            const contracted = campaign.contracted_count ?? 0;
            const thirdStatLabel =
              campaign.status === "completed" || contracted > 0
                ? "Contracted"
                : "Shortlisted";
            const thirdStatValue =
              thirdStatLabel === "Contracted" ? contracted : shortlisted;
            const createdLabel = isLive
              ? `${formatTimeAgo(campaign.created_at)}`
              : campaign.status === "completed"
                ? `Closed ${formatDate(campaign.completed_at ?? campaign.created_at)}`
                : `Created ${formatDate(campaign.created_at)}`;

            return (
              <div key={campaign.id} className="brief" style={{ display: "flex", alignItems: "stretch" }}>
                <Link className="brief" href={target} style={{ flex: 1, display: "flex", textDecoration: "none", color: "inherit" }}>
                <span className={`b-glyph gl-${status.className === "complete" ? "g" : status.className === "draft" ? "d" : status.className === "active" ? "v" : "cy"}`}>
                  {initial}
                </span>
                <div className="b-body">
                  <div className="b-head">
                    <span className="b-name">{label}</span>
                    <span className={`b-status ${status.className}`}>{status.label}</span>
                  </div>
                  <div className="b-meta">
                    <span>
                      <strong>{campaign.niche || "General"}</strong>
                    </span>
                    <span className="dot"></span>
                    {goal ? <span>{goal}</span> : null}
                    {goal ? <span className="dot"></span> : null}
                    <span>{platformList(campaign)}</span>
                    <span className="dot"></span>
                    <span>{campaign.budget_range ?? "Flexible budget"}</span>
                    <span className="dot"></span>
                    <span>{createdLabel}</span>
                  </div>
                </div>
                <div className="b-stats">
                  <div className="b-stat">
                    <div className="l">Matches</div>
                    <div
                      className="v"
                      style={matches === 0 ? { color: "var(--muted)" } : undefined}
                    >
                      {matches === 0 ? "—" : matches}
                    </div>
                  </div>
                  <div className="b-stat">
                    <div className="l">Top match</div>
                    <div
                      className={`v${topScore && topScore >= 90 ? " good" : ""}`}
                      style={
                        topScore == null ? { color: "var(--muted)" } : undefined
                      }
                    >
                      {topScore == null ? "—" : Math.round(topScore)}
                    </div>
                  </div>
                  <div className="b-stat">
                    <div className="l">{thirdStatLabel}</div>
                    <div
                      className="v"
                      style={thirdStatValue === 0 ? { color: "var(--muted)" } : undefined}
                    >
                      {isLive && thirdStatValue === 0 ? "—" : thirdStatValue}
                    </div>
                  </div>
                </div>
                <span className="b-arrow">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </span>
                </Link>
                <div className="b-actions" style={{ display: "flex", flexDirection: "column", gap: "6px", padding: "12px 12px 12px 0", justifyContent: "center" }}>
                  {isDraft ? (
                    <Link
                      href={`/briefs/new?campaignId=${encodeURIComponent(campaign.id)}`}
                      className="btn btn-ghost btn-sm"
                      style={{ fontSize: "11px", padding: "4px 8px" }}
                    >
                      Edit
                    </Link>
                  ) : null}
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    style={{ fontSize: "11px", padding: "4px 8px" }}
                    disabled={duplicatingId === campaign.id}
                    onClick={() => void handleDuplicate(campaign.id)}
                  >
                    {duplicatingId === campaign.id ? "…" : "Duplicate"}
                  </button>
                </div>
              </div>
            );
          })}
          <Link className="new-brief" href="/briefs/new">
            <span className="pp">+</span>
            <div>
              <div className="t">Start a new campaign brief</div>
              <div className="s">
                Describe your product, audience and budget — the matcher takes it from there.
              </div>
            </div>
          </Link>
        </div>
      )}
    </>
  );
}

function BriefsSkeleton() {
  return (
    <div className="brief-list" aria-hidden="true">
      {[0, 1, 2].map((index) => (
        <div key={index} className="brief" style={{ opacity: 0.5 }}>
          <span className="b-glyph gl-d">·</span>
          <div className="b-body">
            <div className="b-head">
              <span className="b-name" style={{ color: "var(--muted)" }}>
                Loading campaign…
              </span>
            </div>
            <div className="b-meta" style={{ color: "var(--muted)" }}>
              <span>fetching from workspace</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
