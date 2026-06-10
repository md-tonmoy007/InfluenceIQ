"use client";

import { useEffect, useState } from "react";
import {
  getCampaign,
  getCampaignInfluencers,
  getCampaignState,
  type CampaignState,
  type CampaignSummary,
  type InfluencerListResult,
} from "@/lib/api";
import DiscoverGrid from "./DiscoverGrid";
import DiscoverTable from "./DiscoverTable";

type LiveCampaignDiscoverProps = {
  campaignId?: string;
  variant: "grid" | "table";
};

const titleize = (value: string) =>
  value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());

export default function LiveCampaignDiscover({
  campaignId,
  variant,
}: LiveCampaignDiscoverProps) {
  const [campaign, setCampaign] = useState<CampaignSummary | null>(null);
  const [pipelineState, setPipelineState] = useState<CampaignState | null>(null);
  const [results, setResults] = useState<InfluencerListResult | null>(null);
  const [loading, setLoading] = useState(Boolean(campaignId));
  const [error, setError] = useState("");

  useEffect(() => {
    if (!campaignId) {
      return;
    }

    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const [campaignData, stateData] = await Promise.all([
          getCampaign(campaignId),
          getCampaignState(campaignId),
        ]);
        if (cancelled) return;
        setCampaign(campaignData);
        setPipelineState(stateData);
        if (stateData.partial_results_available || stateData.status === "completed") {
          const influencerData = await getCampaignInfluencers(
            campaignId,
            new URLSearchParams({ limit: "100" })
          );
          if (cancelled) return;
          setResults(influencerData);
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Unable to load campaign");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [campaignId]);

  useEffect(() => {
    if (!campaignId || pipelineState?.status === "completed" || pipelineState?.status === "failed") {
      return;
    }

    const interval = window.setInterval(async () => {
      try {
        const nextState = await getCampaignState(campaignId);
        setPipelineState(nextState);
        if (nextState.partial_results_available || nextState.status === "completed") {
          const influencerData = await getCampaignInfluencers(
            campaignId,
            new URLSearchParams({ limit: "100" })
          );
          setResults(influencerData);
        }
      } catch (nextError) {
        setError(nextError instanceof Error ? nextError.message : "Unable to refresh campaign");
      }
    }, 2500);

    return () => window.clearInterval(interval);
  }, [campaignId, pipelineState?.status]);

  const banner = campaignId ? (
    <div style={{ marginBottom: "18px", padding: "14px 16px", borderRadius: "16px", background: "rgba(98,83,255,0.08)", color: "var(--ink)" }}>
      <strong>{campaign?.brand ?? "Live discovery"}</strong>
      {" · "}
      {titleize(String(pipelineState?.status ?? campaign?.status ?? "queued"))}
      {" · "}
      {pipelineState?.influencer_count ?? results?.total ?? 0} creators surfaced
    </div>
  ) : null;

  if (loading && campaignId) {
    return (
      <>
        {banner}
        <div style={{ padding: "18px 20px", borderRadius: "20px", background: "var(--panel)" }}>
          Loading live campaign results...
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        {banner}
        <div style={{ padding: "18px 20px", borderRadius: "20px", background: "rgba(255,110,80,0.12)" }}>
          {error}
        </div>
      </>
    );
  }

  return (
    <>
      {banner}
      {variant === "grid" ? (
        <DiscoverGrid items={results?.items} campaignId={campaignId} />
      ) : (
        <DiscoverTable items={results?.items} campaignId={campaignId} />
      )}
    </>
  );
}
