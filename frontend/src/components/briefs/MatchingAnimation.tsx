"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { PipelineProgress } from "@/components/campaign/PipelineProgress";
import { useCampaignPipeline } from "@/hooks/useCampaignPipeline";

export default function MatchingAnimation() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const campaignId = searchParams.get("campaignId");
  const { state, events, isTerminal } = useCampaignPipeline(campaignId);

  useEffect(() => {
    if (!campaignId || !isTerminal) return;
    const timer = setTimeout(() => {
      router.replace(`/shortlist?campaignId=${encodeURIComponent(campaignId)}`);
    }, 800);
    return () => clearTimeout(timer);
  }, [campaignId, isTerminal, router]);

  if (!campaignId) {
    return <div className="matching-shell">Missing campaign id.</div>;
  }

  return (
    <div className="matching-shell">
      <h1>Running your campaign</h1>
      <p>Discovering creators, enriching platform data, and scoring matches.</p>
      <PipelineProgress state={state} events={events} />
    </div>
  );
}
