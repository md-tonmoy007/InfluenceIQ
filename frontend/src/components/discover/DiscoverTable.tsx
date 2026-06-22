"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { tableCreators, type TableCreator } from "@/data/tableCreators";
import type { InfluencerRecommendation } from "@/types/influencer";
import { useToast } from "@/components/ui/ToastProvider";
import {
  avatarFromName,
  estimateRateNumber,
  estimateViews,
  extractCategory,
  extractLocation,
  formatCompactNumber,
  gradientByPlatform,
  normalizePlatform,
  tierFromFollowers,
} from "@/lib/influencerPresentation";

type DiscoverTableProps = {
  items?: InfluencerRecommendation[];
  campaignId?: string;
};

const platformGlyphs: Record<string, React.ReactNode> = {
  instagram: (
    <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="white" strokeWidth="2">
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.5" cy="6.5" r="0.5" fill="white" />
    </svg>
  ),
  youtube: (
    <svg viewBox="0 0 24 18" width="11" height="9" fill="white">
      <path d="M23.5 3.5a3 3 0 0 0-2.1-2.1C19.5 1 12 1 12 1s-7.5 0-9.4.4A3 3 0 0 0 .5 3.5C.1 5.4.1 9 .1 9s0 3.6.4 5.5a3 3 0 0 0 2.1 2.1C4.5 17 12 17 12 17s7.5 0 9.4-.4a3 3 0 0 0 2.1-2.1c.4-1.9.4-5.5.4-5.5s0-3.6-.4-5.5zM9.5 12.5v-7L15.5 9l-6 3.5z" />
    </svg>
  ),
  tiktok: (
    <svg viewBox="0 0 20 22" width="9" height="11" fill="white">
      <path d="M14.5 1c.4 1.8 1.5 3.4 3 4.4 1.1.7 2.5 1.1 3.9 1.1V11c-1.6 0-3.2-.4-4.6-1.1-.6-.3-1.2-.7-1.7-1.1v6.6c0 4.1-3.4 7.5-7.5 7.5-1.6 0-3.1-.5-4.3-1.4-1.9-1.4-3.2-3.7-3.2-6.2 0-4.1 3.4-7.5 7.5-7.5.4 0 .9 0 1.3.1v4.4c-.4-.1-.8-.2-1.3-.2-1.7 0-3.1 1.4-3.1 3.1s1.4 3.2 3.2 3.2 3.2-1.4 3.2-3.1V1h3.6z" />
    </svg>
  ),
  facebook: (
    <svg viewBox="0 0 24 24" width="10" height="10" fill="white">
      <path d="M14 9V7c0-1 .5-2 2-2h2V1h-3c-3 0-5 2-5 5v3H7v4h3v9h4v-9h3l1-4h-4z" />
    </svg>
  ),
};

const pfClass = (platform: string) =>
  platform === "instagram"
    ? "pf-ig"
    : platform === "youtube"
      ? "pf-yt"
      : platform === "tiktok"
        ? "pf-tt"
        : "pf-fb";

const tierClasses: Record<string, string> = {
  Rising: "tier-rising",
  Established: "tier-established",
  Premium: "tier-premium",
};

type LiveRow = Omit<TableCreator, "t"> & { id: string; t: TableCreator["t"] | "—" };

const keyMap: Record<string, keyof LiveRow> = {
  name: "n",
  platform: "p",
  category: "c",
  tier: "t",
  followers: "f",
  views: "v",
  engagement: "e",
  rate: "r",
  match: "m",
  location: "loc",
};

const fromInfluencer = (item: InfluencerRecommendation): LiveRow => {
  const platform = normalizePlatform(item.platform);
  return {
    id: item.id,
    n: item.name,
    h: item.handle || "@unknown",
    p: platform,
    c: extractCategory(item),
    t: tierFromFollowers(item.followers),
    f: item.followers,
    v: estimateViews(item.followers, item.engagementRate),
    e: item.engagementRate,
    r: estimateRateNumber(item),
    m: Math.round(item.matchScore),
    loc: extractLocation(item),
    v_: item.trustGrade === "A+" || item.trustGrade === "A",
    a: avatarFromName(item.name),
    bg: gradientByPlatform[platform],
  };
};

const fmt = (n: number) =>
  n >= 1e6
    ? `${(n / 1e6).toFixed(n >= 1e7 ? 0 : 2)}M`
    : n >= 1e3
      ? `${Math.round(n / 1e3)}K`
      : `${n}`;

const fmtMoney = (n: number) => `$${n.toLocaleString()}`;

export default function DiscoverTable({ items, campaignId }: DiscoverTableProps) {
  const { toast } = useToast();
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const [sortKey, setSortKey] = useState<string>("match");
  const [sortDir, setSortDir] = useState<number>(-1);
  const [filterQuery, setFilterQuery] = useState("");

  const rows = useMemo<LiveRow[]>(
    () =>
      items?.length
        ? items.map(fromInfluencer)
        : tableCreators.map((creator, index) => ({ ...creator, id: String(index + 1) })),
    [items]
  );

  const sortedData = useMemo(() => {
    const key = keyMap[sortKey];
    return [...rows].sort((a, b) => {
      const av = a[key];
      const bv = b[key];
      if (typeof av === "number" && typeof bv === "number") {
        return (av - bv) * sortDir;
      }
      return String(av).localeCompare(String(bv)) * sortDir;
    });
  }, [rows, sortDir, sortKey]);

  const filteredData = useMemo(() => {
    const query = filterQuery.toLowerCase().trim();
    if (!query) return sortedData;
    return sortedData.filter((row) =>
      `${row.n} ${row.h} ${row.c} ${row.loc}`.toLowerCase().includes(query)
    );
  }, [filterQuery, sortedData]);

  const toggleAll = () => {
    if (selectedIndices.size === filteredData.length) {
      setSelectedIndices(new Set());
    } else {
      setSelectedIndices(new Set(filteredData.map((_, index) => index)));
    }
  };

  const toggleRow = (index: number) => {
    const next = new Set(selectedIndices);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    setSelectedIndices(next);
  };

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((prev) => -prev);
    } else {
      setSortKey(key);
      setSortDir(
        key === "followers" || key === "views" || key === "engagement" || key === "rate" || key === "match"
          ? -1
          : 1
      );
    }
  };

  const handleSaveBulk = () => {
    const count = selectedIndices.size;
    toast(`Saving ${count} creator${count !== 1 ? "s" : ""} to a list...`, {
      type: "success",
    });
  };

  const isAllSelected = selectedIndices.size === filteredData.length && filteredData.length > 0;
  const isMixed = selectedIndices.size > 0 && selectedIndices.size < filteredData.length;

  return (
    <>
      <div className="controls">
        <div className="seg" role="tablist">
          <Link href={campaignId ? `/discover?campaignId=${encodeURIComponent(campaignId)}` : "/discover"}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
              <rect x="3" y="3" width="7" height="7" rx="1.4" />
              <rect x="14" y="3" width="7" height="7" rx="1.4" />
              <rect x="3" y="14" width="7" height="7" rx="1.4" />
              <rect x="14" y="14" width="7" height="7" rx="1.4" />
            </svg>
            Card view
          </Link>
          <button type="button" className="active">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
              <line x1="4" y1="6" x2="20" y2="6" />
              <line x1="4" y1="12" x2="20" y2="12" />
              <line x1="4" y1="18" x2="20" y2="18" />
            </svg>
            Table view
          </button>
        </div>
        <div className="quick-search">
          <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" style={{ color: "var(--muted)" }}>
            <circle cx="11" cy="11" r="6.5" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          <input
            id="quick"
            placeholder="Filter by name, handle, or category..."
            value={filterQuery}
            onChange={(event) => setFilterQuery(event.target.value)}
          />
        </div>
        <button className="ctrl-btn" type="button">Filters</button>
        <button className="ctrl-btn" type="button">Columns</button>
        <button className="ctrl-btn" type="button">Export CSV</button>
      </div>

      <div className={`bulk-bar ${selectedIndices.size === 0 ? "hidden" : ""}`} id="bulk-bar">
        <span className="nc">
          <span className="pulse"></span>
          <span id="bulk-count">{selectedIndices.size}</span> selected
        </span>
        <span className="sep"></span>
        <button className="bulk-act primary" id="save-to-list" type="button" onClick={handleSaveBulk}>
          Save Selected to List
        </button>
        <button className="bulk-act" type="button">Compare</button>
        <button className="bulk-act" type="button">Export rows</button>
        <button className="clear" id="bulk-clear" type="button" onClick={() => setSelectedIndices(new Set())}>
          Clear selection
        </button>
      </div>

      <div className="term">
        <div className="term-head">
          <span className="ticker">
            <strong>IIQ-DSC</strong> - Live creator index
          </span>
          <span className="live">Streaming</span>
          <div className="right">
            <span>
              Rows <strong style={{ color: "var(--ink)", fontWeight: 500 }}>{filteredData.length}</strong>
            </span>
            <span>·</span>
            <span>
              Total <strong style={{ color: "var(--ink)", fontWeight: 500 }}>{rows.length}</strong>
            </span>
          </div>
        </div>
        <div className="scroll">
          <table className="t" id="big">
            <thead>
              <tr>
                <th>
                  <span className={`cb ${isAllSelected ? "on" : ""} ${isMixed ? "mixed" : ""}`} role="checkbox" aria-checked={isAllSelected} onClick={toggleAll}>
                    <svg viewBox="0 0 16 12">
                      <path d="M1 6 L6 11 L15 1" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                    </svg>
                  </span>
                </th>
                <th>#</th>
                <th className={sortKey === "name" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""} onClick={() => handleSort("name")}>Name</th>
                <th className={sortKey === "platform" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""} onClick={() => handleSort("platform")}>Platform</th>
                <th className={sortKey === "category" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""} onClick={() => handleSort("category")}>Category</th>
                <th className={sortKey === "tier" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""} onClick={() => handleSort("tier")}>Tier</th>
                <th className={`r ${sortKey === "followers" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""}`} onClick={() => handleSort("followers")}>Followers</th>
                <th className={`r ${sortKey === "views" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""}`} onClick={() => handleSort("views")}>Avg views</th>
                <th className={`r ${sortKey === "engagement" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""}`} onClick={() => handleSort("engagement")}>Engagement</th>
                <th className={`r ${sortKey === "rate" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""}`} onClick={() => handleSort("rate")}>Est. rate</th>
                <th className={sortKey === "match" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""} onClick={() => handleSort("match")}>Match</th>
                <th className={sortKey === "location" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""} onClick={() => handleSort("location")}>Location</th>
                <th className="r">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredData.map((row, index) => {
                const isSelected = selectedIndices.has(index);
                return (
                  <tr key={row.id} className={isSelected ? "selected" : ""}>
                    <td>
                      <span className={`cb row-cb ${isSelected ? "on" : ""}`} role="checkbox" aria-checked={isSelected} onClick={() => toggleRow(index)}>
                        <svg viewBox="0 0 16 12">
                          <path d="M1 6 L6 11 L15 1" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                        </svg>
                      </span>
                    </td>
                    <td className="num" style={{ color: "var(--muted)" }}>{String(index + 1).padStart(3, "0")}</td>
                    <td>
                      <div className="nc">
                        <div className="av-tiny" style={{ background: row.bg }}>{row.a}</div>
                        <div className="nm">
                          <span className="n1">{row.n}</span>
                          <span className="h">{row.h}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="platform-cell">
                        <span className={`g ${pfClass(row.p)}`}>{platformGlyphs[row.p]}</span>
                        <span style={{ textTransform: "capitalize" }}>{row.p}</span>
                      </span>
                    </td>
                    <td>{row.c}</td>
                    <td><span className={`tier-pill ${tierClasses[row.t] ?? "tier-established"}`}>{row.t}</span></td>
                    <td className="r num">{row.f > 0 ? fmt(row.f) : "—"}</td>
                    <td className="r num">{row.f > 0 ? formatCompactNumber(row.v) : "—"}</td>
                    <td className="r">{row.e > 0 ? `${row.e.toFixed(1)}%` : "—"}</td>
                    <td className="r num">{row.f > 0 ? fmtMoney(row.r) : "—"}</td>
                    <td>{row.m}%</td>
                    <td>{row.loc}</td>
                    <td className="r">
                      <div className="act-cell">
                        <Link
                          className="iconlink"
                          href={
                            campaignId
                              ? `/profile/${encodeURIComponent(row.id)}?campaignId=${encodeURIComponent(campaignId)}`
                              : `/profile/${encodeURIComponent(row.id)}`
                          }
                          title="View profile"
                        >
                          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7">
                            <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
