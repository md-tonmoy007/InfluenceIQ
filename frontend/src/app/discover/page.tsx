import React from "react";
import Link from "next/link";
import AppShell from "@/components/shell/AppShell";
import DiscoverSearch from "@/components/discover/DiscoverSearch";
import DiscoverGrid from "@/components/discover/DiscoverGrid";
import RangeFilter from "@/components/discover/RangeFilter";
import "../discover.css";

export default function DiscoverPage() {
  const crumbs = [{ label: "Workspace" }, { label: "Discover", current: true }];

  return (
    <AppShell crumbs={crumbs} showSearch={false}>
      <main className="content">
        <div className="page-head">
          <div>
            <h1>
              Discover <span className="accent">creators.</span>
            </h1>
            <p className="sub">
              Describe what you&apos;re looking for, then let our AI rank 2.4M
              creators against your brief.
            </p>
          </div>
        </div>

        {/* ===== Natural language search ===== */}
        <DiscoverSearch />

        {/* ===== Filters + Results ===== */}
        <div className="layout">
          {/* Filters sidebar */}
          <aside className="filters">
            <div className="filters-head">
              <h3>
                Filters <span className="badge mono">5</span>
              </h3>
              <span className="clear">Clear all</span>
            </div>

            <div className="filter-section">
              <div className="label">
                Platform <span className="v">2 selected</span>
              </div>
              <div className="check-list">
                <label className="check">
                  <input type="checkbox" defaultChecked />
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
                  <span className="platform-ico pf-ig">
                    <svg
                      width="11"
                      height="11"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <rect x="3" y="3" width="18" height="18" rx="5" />
                      <circle cx="12" cy="12" r="4" />
                      <circle
                        cx="17.5"
                        cy="6.5"
                        r="0.5"
                        fill="currentColor"
                      />
                    </svg>
                  </span>
                  <span className="label-text">Instagram</span>
                  <span className="ct">1.2M</span>
                </label>
                <label className="check">
                  <input type="checkbox" defaultChecked />
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
                  <span className="platform-ico pf-yt">
                    <svg width="11" height="9" viewBox="0 0 24 18" fill="currentColor">
                      <path d="M23.5 3.5a3 3 0 0 0-2.1-2.1C19.5 1 12 1 12 1s-7.5 0-9.4.4A3 3 0 0 0 .5 3.5C.1 5.4.1 9 .1 9s0 3.6.4 5.5a3 3 0 0 0 2.1 2.1C4.5 17 12 17 12 17s7.5 0 9.4-.4a3 3 0 0 0 2.1-2.1c.4-1.9.4-5.5.4-5.5s0-3.6-.4-5.5zM9.5 12.5v-7L15.5 9l-6 3.5z" />
                    </svg>
                  </span>
                  <span className="label-text">YouTube</span>
                  <span className="ct">680K</span>
                </label>
                <label className="check">
                  <input type="checkbox" />
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
                  <span className="platform-ico pf-tt">
                    <svg width="10" height="11" viewBox="0 0 20 22" fill="currentColor">
                      <path d="M14.5 1c.4 1.8 1.5 3.4 3 4.4 1.1.7 2.5 1.1 3.9 1.1V11c-1.6 0-3.2-.4-4.6-1.1-.6-.3-1.2-.7-1.7-1.1v6.6c0 4.1-3.4 7.5-7.5 7.5-1.6 0-3.1-.5-4.3-1.4-1.9-1.4-3.2-3.7-3.2-6.2 0-4.1 3.4-7.5 7.5-7.5.4 0 .9 0 1.3.1v4.4c-.4-.1-.8-.2-1.3-.2-1.7 0-3.1 1.4-3.1 3.1s1.4 3.2 3.2 3.2 3.2-1.4 3.2-3.1V1h3.6z" />
                    </svg>
                  </span>
                  <span className="label-text">TikTok</span>
                  <span className="ct">412K</span>
                </label>
                <label className="check">
                  <input type="checkbox" />
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
                  <span className="platform-ico pf-fb">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M14 9V7c0-1 .5-2 2-2h2V1h-3c-3 0-5 2-5 5v3H7v4h3v9h4v-9h3l1-4h-4z" />
                    </svg>
                  </span>
                  <span className="label-text">Facebook</span>
                  <span className="ct">156K</span>
                </label>
              </div>
            </div>

            <div className="filter-section">
              <div className="label">
                Category <span className="v">3 selected</span>
              </div>
              <div className="check-list">
                <label className="check">
                  <input type="checkbox" defaultChecked />
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
                  <span className="cat-ico cat-fashion"></span>
                  <span className="label-text">Fashion</span>
                  <span className="ct">312K</span>
                </label>
                <label className="check">
                  <input type="checkbox" />
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
                  <span className="cat-ico cat-tech"></span>
                  <span className="label-text">Tech</span>
                  <span className="ct">198K</span>
                </label>
                <label className="check">
                  <input type="checkbox" />
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
                  <span className="cat-ico cat-food"></span>
                  <span className="label-text">Food</span>
                  <span className="ct">274K</span>
                </label>
                <label className="check">
                  <input type="checkbox" defaultChecked />
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
                  <span className="cat-ico cat-lifestyle"></span>
                  <span className="label-text">Lifestyle</span>
                  <span className="ct">441K</span>
                </label>
                <label className="check">
                  <input type="checkbox" defaultChecked />
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
                  <span className="cat-ico cat-beauty"></span>
                  <span className="label-text">Beauty</span>
                  <span className="ct">208K</span>
                </label>
                <label className="check">
                  <input type="checkbox" />
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
                  <span className="cat-ico cat-fitness"></span>
                  <span className="label-text">Fitness</span>
                  <span className="ct">163K</span>
                </label>
                <label className="check">
                  <input type="checkbox" />
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
                  <span className="cat-ico cat-travel"></span>
                  <span className="label-text">Travel</span>
                  <span className="ct">189K</span>
                </label>
                <label className="check">
                  <input type="checkbox" />
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
                  <span className="cat-ico cat-gaming"></span>
                  <span className="label-text">Gaming</span>
                  <span className="ct">94K</span>
                </label>
              </div>
            </div>

            <div className="filter-section">
              <div className="label">Tier</div>
              <div className="radio-list">
                <label className="radio">
                  <input type="radio" name="tier" />
                  <span className="dot"></span>
                  <span className="lab">
                    <span className="name">Rising</span>
                    <span className="meta">Emerging voices</span>
                  </span>
                  <span className="tier-mark tier-rising">&lt; 50K</span>
                </label>
                <label className="radio active">
                  <input type="radio" name="tier" defaultChecked />
                  <span className="dot"></span>
                  <span className="lab">
                    <span className="name">Established</span>
                    <span className="meta">Reliable mid-tier reach</span>
                  </span>
                  <span className="tier-mark tier-established">50K – 500K</span>
                </label>
                <label className="radio">
                  <input type="radio" name="tier" />
                  <span className="dot"></span>
                  <span className="lab">
                    <span className="name">Premium</span>
                    <span className="meta">Top-tier creators</span>
                  </span>
                  <span className="tier-mark tier-premium">500K+</span>
                </label>
              </div>
            </div>

            <RangeFilter
              id="budget"
              label="Budget per post"
              min={50}
              max={10000}
              step={50}
              initialValue={3200}
              prefix="$"
              format="currency"
            />

            <div className="filter-section">
              <div className="label">Audience location</div>
              <div className="select-wrap">
                <select className="select" defaultValue="India">
                  <option>🌍 Global</option>
                  <option>🇧🇩 Bangladesh</option>
                  <option value="India">🇮🇳 India</option>
                  <option>🇺🇸 United States</option>
                  <option>🇬🇧 United Kingdom</option>
                  <option>🇨🇦 Canada</option>
                  <option>🇦🇺 Australia</option>
                  <option>🇩🇪 Germany</option>
                  <option>🇧🇷 Brazil</option>
                  <option>🇯🇵 Japan</option>
                  <option>Other regions…</option>
                </select>
              </div>
            </div>

            <RangeFilter
              id="er"
              label="Min engagement rate"
              min={1}
              max={15}
              step={0.5}
              initialValue={3.5}
              unit="%"
              format="percent"
            />
          </aside>

          {/* Results */}
          <section>
            <div className="results-head">
              <div className="results-count">
                <strong>248</strong> creators match your brief
                <span className="live">Live results</span>
              </div>
              <div className="results-actions">
                <div className="sort-wrap">
                  <span className="lbl">Sort</span>
                  <div className="select-wrap" style={{ marginLeft: "-4px" }}>
                    <select id="sort" defaultValue="Best Match">
                      <option>Best Match</option>
                      <option>Highest Engagement</option>
                      <option>Lowest Rate</option>
                      <option>Most Followers</option>
                    </select>
                  </div>
                </div>
                <div className="view-toggle" role="group" aria-label="View">
                  <button
                    className="active"
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
                  </button>
                  <Link
                    href="/discover/table"
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

            <DiscoverGrid />
          </section>
        </div>
      </main>
    </AppShell>
  );
}
