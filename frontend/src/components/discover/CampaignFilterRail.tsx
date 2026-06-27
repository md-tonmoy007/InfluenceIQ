"use client";

import type { CampaignFacets } from "@/lib/api";
import type { CampaignInfluencerFilters } from "@/hooks/useCampaignInfluencers";

type CampaignFilterRailProps = {
  facets: CampaignFacets | null;
  filters: CampaignInfluencerFilters;
  activeFilterCount: number;
  onChange: (filters: CampaignInfluencerFilters) => void;
  onClear: () => void;
};

const platformLabels: Record<string, string> = {
  instagram: "Instagram",
  youtube: "YouTube",
  tiktok: "TikTok",
  x: "X",
  twitter: "X",
  facebook: "Facebook",
  unknown: "Unknown",
};

const tierLabels: Record<string, string> = {
  nano: "Nano",
  rising: "Rising",
  mid: "Mid-tier",
  established: "Established",
  premium: "Premium",
  mega: "Mega",
  unknown: "Unknown",
};

export default function CampaignFilterRail({
  facets,
  filters,
  activeFilterCount,
  onChange,
  onClear,
}: CampaignFilterRailProps) {
  const update = (patch: Partial<CampaignInfluencerFilters>) => {
    onChange({ ...filters, ...patch });
  };

  const togglePlatform = (value: string) => {
    update({ platform: filters.platform === value ? undefined : value });
  };

  const toggleGrade = (value: string) => {
    update({ grade: filters.grade === value ? undefined : value });
  };

  return (
    <aside className="filters">
      <div className="filters-head">
        <h3>
          Filters{" "}
          <span className="badge mono">{activeFilterCount}</span>
        </h3>
        <button type="button" className="clear" onClick={onClear}>
          Clear all
        </button>
      </div>

      <div className="filter-section">
        <div className="label">
          Platform{" "}
          <span className="v">{filters.platform ? "1 selected" : "Any"}</span>
        </div>
        <div className="check-list">
          {(facets?.platforms ?? []).map((facet) => (
            <label className="check" key={facet.value}>
              <input
                type="checkbox"
                checked={filters.platform === facet.value}
                onChange={() => togglePlatform(facet.value)}
              />
              <span className="box">
                <svg viewBox="0 0 16 12" width="10" height="8">
                  <path
                    d="M1 6 L6 11 L15 1"
                    stroke="currentColor"
                    strokeWidth="2.4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                  />
                </svg>
              </span>
              <span className="label-text">
                {platformLabels[facet.value] ?? facet.value}
              </span>
              <span className="ct">{facet.count}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="filter-section">
        <div className="label">
          Trust grade{" "}
          <span className="v">{filters.grade ?? "Any"}</span>
        </div>
        <div className="radio-list">
          {(facets?.trust_grades ?? []).map((facet) => (
            <label
              className={`radio ${filters.grade === facet.value ? "active" : ""}`}
              key={facet.value}
            >
              <input
                type="radio"
                name="grade"
                checked={filters.grade === facet.value}
                onChange={() => toggleGrade(facet.value)}
              />
              <span className="dot"></span>
              <span className="lab">
                <span className="name">{facet.value}</span>
                <span className="meta">{facet.count} creators</span>
              </span>
            </label>
          ))}
        </div>
      </div>

      <div className="filter-section">
        <div className="label">Category</div>
        <div className="select-wrap">
          <select
            className="select"
            value={filters.niche ?? ""}
            onChange={(event) =>
              update({ niche: event.target.value || undefined })
            }
          >
            <option value="">All categories</option>
            {(facets?.categories ?? []).map((facet) => (
              <option key={facet.value} value={facet.value}>
                {facet.value} ({facet.count})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="filter-section">
        <div className="label">Audience location</div>
        <div className="select-wrap">
          <select
            className="select"
            value={filters.location ?? ""}
            onChange={(event) =>
              update({ location: event.target.value || undefined })
            }
          >
            <option value="">All locations</option>
            {(facets?.locations ?? []).map((facet) => (
              <option key={facet.value} value={facet.value}>
                {facet.value} ({facet.count})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="filter-section">
        <div className="label">Follower tiers in campaign</div>
        <div className="check-list">
          {(facets?.follower_tiers ?? []).map((facet) => (
            <div className="check" key={facet.value} style={{ cursor: "default" }}>
              <span className="label-text">
                {tierLabels[facet.value] ?? facet.value}
              </span>
              <span className="ct">{facet.count}</span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
