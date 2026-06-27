"use client";

import Link from "next/link";

import CampaignFilterRail from "@/components/discover/CampaignFilterRail";
import DiscoverGrid from "@/components/discover/DiscoverGrid";
import DiscoverTable from "@/components/discover/DiscoverTable";
import { useCampaignInfluencers } from "@/hooks/useCampaignInfluencers";

type CampaignDiscoverPageClientProps = {
  campaignId: string;
  variant: "grid" | "table";
};

export default function CampaignDiscoverPageClient({
  campaignId,
  variant,
}: CampaignDiscoverPageClientProps) {
  const {
    items,
    total,
    facets,
    filters,
    setFilters,
    clearFilters,
    activeFilterCount,
    loading,
    loadingMore,
    error,
    loadMore,
    hasMore,
  } = useCampaignInfluencers(campaignId);

  const displayedTotal =
    activeFilterCount > 0 ? items.length : total;
  const totalLabel =
    activeFilterCount > 0 && hasMore ? `${displayedTotal}+` : String(displayedTotal);

  return (
    <>
      {error ? (
        <div
          style={{
            marginBottom: "18px",
            padding: "14px 16px",
            borderRadius: "16px",
            background: "rgba(255,110,80,0.12)",
            color: "var(--ink)",
          }}
        >
          {error}
        </div>
      ) : null}

      <div className="layout">
        <CampaignFilterRail
          facets={facets}
          filters={filters}
          activeFilterCount={activeFilterCount}
          onChange={setFilters}
          onClear={clearFilters}
        />

        <section>
          <div className="results-head">
            <div className="results-count">
              <strong>{loading ? "…" : totalLabel}</strong> creators in this campaign
              <span className="live">Live results</span>
            </div>
            <div className="results-actions">
              <div className="view-toggle" role="group" aria-label="View">
                <Link
                  href={`/discover?campaignId=${encodeURIComponent(campaignId)}`}
                  className={variant === "grid" ? "active" : undefined}
                  aria-label="Card view"
                  title="Card view"
                >
                  <svg
                    className="i"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.7"
                  >
                    <rect x="3" y="3" width="7" height="7" rx="1.4" />
                    <rect x="14" y="3" width="7" height="7" rx="1.4" />
                    <rect x="3" y="14" width="7" height="7" rx="1.4" />
                    <rect x="14" y="14" width="7" height="7" rx="1.4" />
                  </svg>
                </Link>
                <Link
                  href={`/discover/table?campaignId=${encodeURIComponent(campaignId)}`}
                  className={variant === "table" ? "active" : undefined}
                  aria-label="Table view"
                  title="Table view"
                >
                  <svg
                    className="i"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.7"
                  >
                    <line x1="4" y1="6" x2="20" y2="6" />
                    <line x1="4" y1="12" x2="20" y2="12" />
                    <line x1="4" y1="18" x2="20" y2="18" />
                  </svg>
                </Link>
              </div>
            </div>
          </div>

          {loading && !items.length ? (
            <div
              style={{
                padding: "18px 20px",
                borderRadius: "20px",
                background: "var(--panel)",
              }}
            >
              Loading campaign creators…
            </div>
          ) : variant === "grid" ? (
            <DiscoverGrid items={items} campaignId={campaignId} />
          ) : (
            <DiscoverTable items={items} campaignId={campaignId} />
          )}

          {hasMore ? (
            <div style={{ marginTop: "20px", display: "flex", justifyContent: "center" }}>
              <button
                type="button"
                className="btn btn-ghost"
                disabled={loadingMore}
                onClick={() => void loadMore()}
              >
                {loadingMore ? "Loading…" : "Load more creators"}
              </button>
            </div>
          ) : null}
        </section>
      </div>
    </>
  );
}
