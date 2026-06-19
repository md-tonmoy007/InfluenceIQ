import React, { Suspense } from "react";
import Link from "next/link";
import AppShell from "@/components/shell/AppShell";
import DashboardInteractions from "@/components/dashboard/DashboardInteractions";
import "../dashboard.css";

export default function DashboardPage() {
  const crumbs = [{ label: "Workspace" }, { label: "Dashboard", current: true }];

  return (
    <AppShell crumbs={crumbs} showSearch={true}>
      <main className="content">
        <div className="welcome">
          <div>
            <h1>
              Good morning, Elena <span className="accent">— let&apos;s launch.</span>
            </h1>
            <p className="sub">
              Sunday, May 10. You have 2 briefs awaiting creator approvals and 1
              new shortlist ready to review.
            </p>
          </div>
          <div className="actions">
            <Link className="btn btn-ghost" href="/briefs/new">
              <svg
                className="i"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
              >
                <path d="M12 5v14M5 12h14" />
              </svg>
              New brief
            </Link>
            <Link className="btn btn-primary" href="/discover">
              Find Influencers
              <span className="arrow">→</span>
            </Link>
          </div>
        </div>

        <section className="stats" aria-label="Workspace stats">
          <div className="stat s-violet">
            <div className="label">
              <span className="pin"></span>Influencers Indexed
            </div>
            <div className="value">
              <span className="count-up" data-target="2.41" data-decimals="2">
                0.00
              </span>
              <span className="unit">M</span>
            </div>
            <div className="delta">
              ▲ 38,210 this week <span className="neutral">· refreshed 4h ago</span>
            </div>
            <svg
              className="spark"
              width="120"
              height="36"
              viewBox="0 0 120 36"
              fill="none"
              aria-hidden="true"
            >
              <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="oklch(0.58 0.22 285)" />
                  <stop offset="100%" stopColor="oklch(0.74 0.18 30)" />
                </linearGradient>
                <linearGradient id="g1f" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="0%"
                    stopColor="oklch(0.58 0.22 285)"
                    stopOpacity="0.25"
                  />
                  <stop
                    offset="100%"
                    stopColor="oklch(0.58 0.22 285)"
                    stopOpacity="0"
                  />
                </linearGradient>
              </defs>
              <path
                d="M0 30 L12 26 L24 28 L36 20 L48 22 L60 14 L72 16 L84 8 L96 12 L108 4 L120 6 L120 36 L0 36 Z"
                fill="url(#g1f)"
              />
              <path
                style={{ "--len": 200 } as React.CSSProperties}
                d="M0 30 L12 26 L24 28 L36 20 L48 22 L60 14 L72 16 L84 8 L96 12 L108 4 L120 6"
                stroke="url(#g1)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>

          <div className="stat s-cyan">
            <div className="label">
              <span className="pin"></span>Categories Covered
            </div>
            <div className="value">
              <span className="count-up" data-target="182">
                0
              </span>
            </div>
            <div className="delta">▲ 6 new niches added in April</div>
            <svg
              className="spark"
              width="120"
              height="36"
              viewBox="0 0 120 36"
              fill="none"
              aria-hidden="true"
            >
              <defs>
                <linearGradient id="g2" x1="0" y1="1" x2="0" y2="0">
                  <stop
                    offset="0%"
                    stopColor="oklch(0.78 0.15 215)"
                    stopOpacity="0.4"
                  />
                  <stop offset="100%" stopColor="oklch(0.78 0.15 215)" />
                </linearGradient>
              </defs>
              <g fill="url(#g2)">
                <rect
                  style={{ "--len": 0 } as React.CSSProperties}
                  x="2"
                  y="22"
                  width="8"
                  height="12"
                  rx="2"
                />
                <rect
                  style={{ "--len": 0 } as React.CSSProperties}
                  x="14"
                  y="18"
                  width="8"
                  height="16"
                  rx="2"
                />
                <rect
                  style={{ "--len": 0 } as React.CSSProperties}
                  x="26"
                  y="24"
                  width="8"
                  height="10"
                  rx="2"
                />
                <rect
                  style={{ "--len": 0 } as React.CSSProperties}
                  x="38"
                  y="14"
                  width="8"
                  height="20"
                  rx="2"
                />
                <rect
                  style={{ "--len": 0 } as React.CSSProperties}
                  x="50"
                  y="10"
                  width="8"
                  height="24"
                  rx="2"
                />
                <rect
                  style={{ "--len": 0 } as React.CSSProperties}
                  x="62"
                  y="14"
                  width="8"
                  height="20"
                  rx="2"
                />
                <rect
                  style={{ "--len": 0 } as React.CSSProperties}
                  x="74"
                  y="6"
                  width="8"
                  height="28"
                  rx="2"
                />
                <rect
                  style={{ "--len": 0 } as React.CSSProperties}
                  x="86"
                  y="10"
                  width="8"
                  height="24"
                  rx="2"
                />
                <rect
                  style={{ "--len": 0 } as React.CSSProperties}
                  x="98"
                  y="2"
                  width="8"
                  height="32"
                  rx="2"
                />
                <rect
                  style={{ "--len": 0 } as React.CSSProperties}
                  x="110"
                  y="8"
                  width="8"
                  height="26"
                  rx="2"
                />
              </g>
            </svg>
          </div>

          <div className="stat s-coral">
            <div className="label">
              <span className="pin"></span>Avg Match Score
            </div>
            <div className="value">
              <span className="count-up" data-target="87.4" data-decimals="1">
                0.0
              </span>
              <span className="unit">/100</span>
            </div>
            <div className="delta">▲ 2.1 vs. last 30 days</div>
            <svg
              className="spark"
              width="80"
              height="40"
              viewBox="0 0 80 40"
              fill="none"
              aria-hidden="true"
            >
              <defs>
                <linearGradient id="g3" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="oklch(0.74 0.18 30)" />
                  <stop offset="100%" stopColor="oklch(0.58 0.22 285)" />
                </linearGradient>
              </defs>
              <circle cx="40" cy="20" r="15" stroke="#eeeae0" strokeWidth="4" />
              <circle
                className="prog"
                style={{ "--len": 94.2 } as React.CSSProperties}
                cx="40"
                cy="20"
                r="15"
                stroke="url(#g3)"
                strokeWidth="4"
                strokeDasharray="82 100"
                strokeLinecap="round"
                transform="rotate(-90 40 20)"
              />
              <text
                x="40"
                y="24"
                textAnchor="middle"
                fontSize="11"
                fontWeight="600"
                fontFamily="JetBrains Mono"
                fill="oklch(0.40 0.18 30)"
              >
                87
              </text>
            </svg>
          </div>
        </section>

        <section className="panel" aria-label="Recent searches">
          <div className="panel-head">
            <h3>
              Recent searches <span className="live-pill">Live</span>
            </h3>
            <div className="meta">
              <span>Last 7 days</span>
              <span>·</span>
              <Link href="/briefs">View all →</Link>
            </div>
          </div>
          <table className="tbl">
            <thead>
              <tr>
                <th style={{ width: "40%" }}>Query</th>
                <th>Filters</th>
                <th>Top match</th>
                <th>Results</th>
                <th>When</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="query">Sustainable activewear for women 25–34</td>
                <td>
                  <span className="tag violet">Wellness</span>
                  <span className="tag">US/CA</span>
                  <span className="tag">100K–500K</span>
                </td>
                <td>
                  <span className="score good">96</span>
                </td>
                <td className="results">214</td>
                <td className="when">2 hours ago</td>
                <td>
                  <Link className="open" href="/shortlist">
                    Open <span className="arrow">→</span>
                  </Link>
                </td>
              </tr>
              <tr>
                <td className="query">Outdoor gear creators with PNW audiences</td>
                <td>
                  <span className="tag cyan">Outdoor</span>
                  <span className="tag">US</span>
                  <span className="tag">50K–200K</span>
                </td>
                <td>
                  <span className="score good">94</span>
                </td>
                <td className="results">128</td>
                <td className="when">Yesterday</td>
                <td>
                  <Link className="open" href="/shortlist">
                    Open <span className="arrow">→</span>
                  </Link>
                </td>
              </tr>
              <tr>
                <td className="query">Father&apos;s Day gifting · grooming &amp; tools</td>
                <td>
                  <span className="tag coral">Lifestyle</span>
                  <span className="tag">Dads</span>
                  <span className="tag">25K–100K</span>
                </td>
                <td>
                  <span className="score">91</span>
                </td>
                <td className="results">86</td>
                <td className="when">Tue, May 6</td>
                <td>
                  <Link className="open" href="/shortlist">
                    Open <span className="arrow">→</span>
                  </Link>
                </td>
              </tr>
              <tr>
                <td className="query">Plant-based recipe creators, brand-safe</td>
                <td>
                  <span className="tag violet">Food</span>
                  <span className="tag">Vegan</span>
                  <span className="tag">Mid-tier</span>
                </td>
                <td>
                  <span className="score">89</span>
                </td>
                <td className="results">312</td>
                <td className="when">Mon, May 5</td>
                <td>
                  <Link className="open" href="/shortlist">
                    Open <span className="arrow">→</span>
                  </Link>
                </td>
              </tr>
              <tr>
                <td className="query">Indie bookstagram, US Northeast</td>
                <td>
                  <span className="tag cyan">Books</span>
                  <span className="tag">Northeast</span>
                  <span className="tag">10K–50K</span>
                </td>
                <td>
                  <span className="score">85</span>
                </td>
                <td className="results">47</td>
                <td className="when">Sun, May 4</td>
                <td>
                  <Link className="open" href="/shortlist">
                    Open <span className="arrow">→</span>
                  </Link>
                </td>
              </tr>
              <tr className="empty-row">
                <td colSpan={6}>
                  Searches are kept for 90 days. Pin a search to a saved list to
                  keep it longer.
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </main>
      <Suspense fallback={null}>
        <DashboardInteractions />
      </Suspense>
    </AppShell>
  );
}
