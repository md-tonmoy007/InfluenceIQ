"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { createCampaign } from "@/lib/api";
import { buildCampaignPayloadFromQuery, buildDiscoverBriefSnapshot } from "@/lib/campaignPayload";
import { useToast } from "@/components/ui/ToastProvider";

export default function DiscoverSearch() {
  const router = useRouter();
  const { toast } = useToast();
  const [query, setQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSearch = async () => {
    const trimmed = query.trim();
    if (!trimmed || submitting) {
      return;
    }

    setSubmitting(true);
    try {
      const brief = buildCampaignPayloadFromQuery(trimmed);
      const campaignName = trimmed.slice(0, 120);
      const campaign = await createCampaign(brief, {
        entryPoint: "discover_search",
        searchQuery: trimmed,
        campaignName,
        briefSnapshot: buildDiscoverBriefSnapshot(brief, campaignName),
      });
      const next = `/discover?campaignId=${encodeURIComponent(campaign.campaignId)}`;
      router.push(
        `/matching?campaignId=${encodeURIComponent(campaign.campaignId)}&next=${encodeURIComponent(next)}`
      );
    } catch (error) {
      toast(
        error instanceof Error ? error.message : "Unable to start creator discovery.",
        { type: "error" }
      );
      setSubmitting(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter") {
      void handleSearch();
    }
  };

  const handleSuggest = (text: string) => {
    setQuery(text);
  };

  return (
    <section className="search-hero">
      <div className="search-row">
        <div className="ai-icon" aria-hidden="true">
          <svg
            className="i"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
          >
            <path d="M12 3l1.8 4.5L18 9.3l-4.2 1.8L12 15.6l-1.8-4.5L6 9.3l4.2-1.8L12 3z" />
            <path
              d="M19 16l.9 2.1L22 19l-2.1.9L19 22l-.9-2.1L16 19l2.1-.9L19 16z"
              opacity="0.7"
            />
          </svg>
        </div>
        <input
          id="nl-search"
          className="search-input"
          placeholder="Describe your product, audience, and budget - e.g. skincare brand targeting women 20-35, budget $500"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <div className="search-actions">
          <span className="search-kbd">Cmd K</span>
          <button
            id="nl-find"
            className="btn btn-primary"
            type="button"
            onClick={() => void handleSearch()}
            disabled={submitting}
          >
            {submitting ? "Starting search..." : "Find creators"}
            <span className="arrow">-&gt;</span>
          </button>
        </div>
      </div>
      <div className="search-suggest">
        <span className="lbl">Try</span>
        <button
          className="suggest"
          type="button"
          onClick={() => handleSuggest("Eco-friendly cleaning, US moms 30-45")}
        >
          Eco-friendly cleaning, US moms 30-45
        </button>
        <button
          className="suggest"
          type="button"
          onClick={() => handleSuggest("Fintech app for Gen Z, $2K budget")}
        >
          Fintech app for Gen Z, $2K budget
        </button>
        <button
          className="suggest"
          type="button"
          onClick={() => handleSuggest("Gaming peripherals, mid-tier streamers")}
        >
          Gaming peripherals, mid-tier streamers
        </button>
        <button
          className="suggest"
          type="button"
          onClick={() => handleSuggest("Wedding photography in Bangalore")}
        >
          Wedding photography in Bangalore
        </button>
      </div>
    </section>
  );
}
