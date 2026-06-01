"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { tableCreators, TableCreator } from "@/data/tableCreators";
import { useToast } from "@/components/ui/ToastProvider";

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

const pfClass = (p: string) =>
  p === "instagram"
    ? "pf-ig"
    : p === "youtube"
    ? "pf-yt"
    : p === "tiktok"
    ? "pf-tt"
    : "pf-fb";

const tierClasses: Record<string, string> = {
  Rising: "tier-rising",
  Established: "tier-established",
  Premium: "tier-premium",
};

const fmt = (n: number) =>
  n >= 1e6
    ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 2) + "M"
    : n >= 1e3
    ? Math.round(n / 1e3) + "K"
    : n;

const fmtMoney = (n: number) => "$" + n.toLocaleString();

const keyMap: Record<string, keyof TableCreator> = {
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

export default function DiscoverTable() {
  const { toast } = useToast();
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const [sortKey, setSortKey] = useState<string>("match");
  const [sortDir, setSortDir] = useState<number>(-1);
  const [filterQuery, setFilterQuery] = useState("");

  const sortedData = useMemo(() => {
    const key = keyMap[sortKey];
    return [...tableCreators].sort((a, b) => {
      const av = a[key];
      const bv = b[key];
      if (typeof av === "number" && typeof bv === "number") {
        return (av - bv) * sortDir;
      }
      return String(av).localeCompare(String(bv)) * sortDir;
    });
  }, [sortKey, sortDir]);

  const filteredData = useMemo(() => {
    const q = filterQuery.toLowerCase().trim();
    if (!q) return sortedData;
    return sortedData.filter((d) =>
      (d.n + d.h + d.c + d.loc).toLowerCase().includes(q)
    );
  }, [sortedData, filterQuery]);

  const toggleAll = () => {
    if (selectedIndices.size === filteredData.length) {
      setSelectedIndices(new Set());
    } else {
      setSelectedIndices(new Set(filteredData.map((_, i) => i)));
    }
  };

  const toggleRow = (index: number) => {
    const next = new Set(selectedIndices);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    setSelectedIndices(next);
  };

  const handleSort = (k: string) => {
    if (sortKey === k) {
      setSortDir((prev) => -prev);
    } else {
      setSortKey(k);
      setSortDir(k === "followers" || k === "views" || k === "engagement" || k === "rate" || k === "match" ? -1 : 1);
    }
  };

  const handleSaveBulk = () => {
    const n = selectedIndices.size;
    toast(`Saving ${n} creator${n !== 1 ? "s" : ""} to a list…`, { type: "success" });
  };

  const isAllSelected = selectedIndices.size === filteredData.length && filteredData.length > 0;
  const isMixed = selectedIndices.size > 0 && selectedIndices.size < filteredData.length;

  return (
    <>
      <div className="controls">
        <div className="seg" role="tablist">
          <Link href="/discover">
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
            placeholder="Filter by name, handle, or category…"
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
          />
        </div>
        <button className="ctrl-btn" type="button">
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7">
            <path d="M3 5h18M6 12h12M10 19h4" />
          </svg>
          Filters<span className="badge">5</span>
        </button>
        <button className="ctrl-btn" type="button">
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M3 9h18M9 3v18" />
          </svg>
          Columns
        </button>
        <button className="ctrl-btn" type="button">
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7">
            <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
            <path d="M14 3v5h5" />
          </svg>
          Export CSV
        </button>
      </div>

      <div className={`bulk-bar ${selectedIndices.size === 0 ? "hidden" : ""}`} id="bulk-bar">
        <span className="nc">
          <span className="pulse"></span>
          <span id="bulk-count">{selectedIndices.size}</span> selected
        </span>
        <span className="sep"></span>
        <button className="bulk-act primary" id="save-to-list" type="button" onClick={handleSaveBulk}>
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M19 21l-7-4.5L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16Z" />
          </svg>
          Save Selected to List
        </button>
        <button className="bulk-act" type="button">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8">
            <rect x="3" y="5" width="8" height="14" rx="1.5" />
            <rect x="13" y="5" width="8" height="14" rx="1.5" />
          </svg>
          Compare
        </button>
        <button className="bulk-act" type="button">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
            <path d="M14 3v5h5" />
          </svg>
          Export rows
        </button>
        <button className="bulk-act" type="button">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M4 4h16v16H4z" />
            <path d="M4 4l8 8 8-8" />
          </svg>
          Contact all
        </button>
        <button className="clear" id="bulk-clear" type="button" onClick={() => setSelectedIndices(new Set())}>
          Clear selection
        </button>
      </div>

      <div className="term">
        <div className="term-head">
          <span className="ticker">
            <strong>IIQ•DSC</strong> — Live creator index
          </span>
          <span className="live">Streaming</span>
          <div className="right">
            <span>
              Rows <strong style={{ color: "var(--ink)", fontWeight: 500 }}>25</strong>/page
            </span>
            <span>·</span>
            <span>
              Total <strong style={{ color: "var(--ink)", fontWeight: 500 }}>50,247</strong>
            </span>
            <span>·</span>
            <span>
              Last tick <strong style={{ color: "var(--ink)", fontWeight: 500 }}>12 May 14:38 UTC</strong>
            </span>
          </div>
        </div>
        <div className="scroll">
          <table className="t" id="big">
            <colgroup>
              <col style={{ width: "38px" }} />
              <col style={{ width: "60px" }} />
              <col />
              <col />
              <col />
              <col />
              <col />
              <col />
              <col />
              <col />
              <col />
              <col />
              <col />
            </colgroup>
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
                <th className={sortKey === "name" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""} onClick={() => handleSort("name")}>
                  <span className="sortable">
                    Name
                    <svg className="ar" viewBox="0 0 12 12" width="9" height="9" fill="currentColor">
                      <path d="M6 8l4-5H2z" />
                    </svg>
                  </span>
                </th>
                <th className={sortKey === "platform" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""} onClick={() => handleSort("platform")}>
                  <span className="sortable">
                    Platform
                    <svg className="ar" viewBox="0 0 12 12" width="9" height="9" fill="currentColor">
                      <path d="M6 8l4-5H2z" />
                    </svg>
                  </span>
                </th>
                <th className={sortKey === "category" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""} onClick={() => handleSort("category")}>
                  <span className="sortable">
                    Category
                    <svg className="ar" viewBox="0 0 12 12" width="9" height="9" fill="currentColor">
                      <path d="M6 8l4-5H2z" />
                    </svg>
                  </span>
                </th>
                <th className={sortKey === "tier" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""} onClick={() => handleSort("tier")}>
                  <span className="sortable">
                    Tier
                    <svg className="ar" viewBox="0 0 12 12" width="9" height="9" fill="currentColor">
                      <path d="M6 8l4-5H2z" />
                    </svg>
                  </span>
                </th>
                <th className={`r ${sortKey === "followers" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""}`} onClick={() => handleSort("followers")}>
                  <span className="sortable">
                    Followers
                    <svg className="ar" viewBox="0 0 12 12" width="9" height="9" fill="currentColor">
                      <path d="M6 8l4-5H2z" />
                    </svg>
                  </span>
                </th>
                <th className={`r ${sortKey === "views" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""}`} onClick={() => handleSort("views")}>
                  <span className="sortable">
                    Avg views
                    <svg className="ar" viewBox="0 0 12 12" width="9" height="9" fill="currentColor">
                      <path d="M6 8l4-5H2z" />
                    </svg>
                  </span>
                </th>
                <th className={`r ${sortKey === "engagement" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""}`} onClick={() => handleSort("engagement")}>
                  <span className="sortable">
                    Engagement
                    <svg className="ar" viewBox="0 0 12 12" width="9" height="9" fill="currentColor">
                      <path d="M6 8l4-5H2z" />
                    </svg>
                  </span>
                </th>
                <th className={`r ${sortKey === "rate" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""}`} onClick={() => handleSort("rate")}>
                  <span className="sortable">
                    Est. rate
                    <svg className="ar" viewBox="0 0 12 12" width="9" height="9" fill="currentColor">
                      <path d="M6 8l4-5H2z" />
                    </svg>
                  </span>
                </th>
                <th className={sortKey === "match" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""} onClick={() => handleSort("match")}>
                  <span className="sortable">
                    Match
                    <svg className="ar" viewBox="0 0 12 12" width="9" height="9" fill="currentColor">
                      <path d="M6 8l4-5H2z" />
                    </svg>
                  </span>
                </th>
                <th className={sortKey === "location" ? `sorted ${sortDir < 0 ? "desc" : ""}` : ""} onClick={() => handleSort("location")}>
                  <span className="sortable">
                    Location
                    <svg className="ar" viewBox="0 0 12 12" width="9" height="9" fill="currentColor">
                      <path d="M6 8l4-5H2z" />
                    </svg>
                  </span>
                </th>
                <th className="r">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredData.map((d, i) => {
                const mClass = d.m >= 92 ? "" : d.m >= 80 ? "" : "low";
                const isSelected = selectedIndices.has(i);
                return (
                  <tr key={i} className={isSelected ? "selected" : ""}>
                    <td>
                      <span className={`cb row-cb ${isSelected ? "on" : ""}`} role="checkbox" aria-checked={isSelected} onClick={() => toggleRow(i)}>
                        <svg viewBox="0 0 16 12">
                          <path d="M1 6 L6 11 L15 1" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                        </svg>
                      </span>
                    </td>
                    <td className="num" style={{ color: "var(--muted)" }}>
                      {String(i + 1).padStart(3, "0")}
                    </td>
                    <td>
                      <div className="nc">
                        <div className="av-tiny" style={{ background: d.bg }}>
                          {d.a}
                        </div>
                        <div className="nm">
                          <span className="n1">
                            {d.n}
                            {d.v_ && (
                              <svg className="verified" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 1l2.4 2.1 3.1-.4 1.4 2.8 2.8 1.4-.4 3.1L23 12l-2.1 2.4.4 3.1-2.8 1.4-1.4 2.8-3.1-.4L12 23l-2.4-2.1-3.1.4-1.4-2.8-2.8-1.4.4-3.1L1 12l2.1-2.4-.4-3.1 2.8-1.4 1.4-2.8 3.1.4L12 1z" />
                                <path d="M8.5 12.5l2.4 2.4 4.6-5" stroke="white" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                              </svg>
                            )}
                          </span>
                          <span className="h">{d.h}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="platform-cell">
                        <span className={`g ${pfClass(d.p)}`}>{platformGlyphs[d.p]}</span>
                        <span style={{ textTransform: "capitalize" }}>{d.p}</span>
                      </span>
                    </td>
                    <td>{d.c}</td>
                    <td>
                      <span className={`tier-pill ${tierClasses[d.t]}`}>{d.t}</span>
                    </td>
                    <td className="r num">{fmt(d.f)}</td>
                    <td className="r num">{fmt(d.v)}</td>
                    <td className="r">
                      <span className="eng-cell">
                        <span className="eng-bar">
                          <i style={{ width: `${Math.min(100, (d.e / 12) * 100)}%` }}></i>
                        </span>
                        <span className="eng-val">{d.e.toFixed(1)}%</span>
                      </span>
                    </td>
                    <td className="r num">{fmtMoney(d.r)}</td>
                    <td>
                      <span className="match-cell">
                        <span className={`match-bar ${mClass}`}>
                          <i style={{ width: `${d.m}%` }}></i>
                          <span className="mv">{d.m}</span>
                        </span>
                      </span>
                    </td>
                    <td>{d.loc}</td>
                    <td className="r">
                      <div className="act-cell">
                        <Link className="iconlink" href="/profile/lila-park" title="View profile">
                          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7">
                            <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                        </Link>
                        <button className="iconlink save" title="Save to list" type="button">
                          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7">
                            <path d="M19 21l-7-4.5L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16Z" />
                          </svg>
                        </button>
                        <button className="iconlink" title="Contact" type="button">
                          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7">
                            <path d="M4 4h16v16H4z" />
                            <path d="M4 4l8 8 8-8" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="pagination">
          <div className="info">
            <span id="show-range">Showing 1–{filteredData.length}</span> of <strong>50,247</strong> creators
          </div>
          <div style={{ display: "flex", alignItems: "center" }}>
            <div className="per-page">
              <span>Per page</span>
              <select defaultValue="25">
                <option>10</option>
                <option value="25">25</option>
                <option>50</option>
                <option>100</option>
              </select>
            </div>
            <div className="pages">
              <button className="nav" disabled>
                ‹
              </button>
              <button className="active">1</button>
              <button>2</button>
              <button>3</button>
              <button>4</button>
              <button>5</button>
              <span className="ellipsis">…</span>
              <button>2010</button>
              <button className="nav">›</button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
