"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/shell/AppShell";
import { getWorkspaceSummary, type WorkspaceSummary } from "@/lib/api";
import { useToast } from "@/components/ui/ToastProvider";
import "../dashboard.css";

const formatNumber = (value: number, decimals = 0): string =>
  new Intl.NumberFormat(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);

const formatCompactNumber = (value: number, decimals = 1): string =>
  new Intl.NumberFormat(undefined, {
    notation: "compact",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);

const formatTimeAgo = (iso: string | null | undefined): string => {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const now = Date.now();
  const diffMs = now - then;
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (diffMs < minute) return "just now";
  if (diffMs < hour) {
    const minutes = Math.floor(diffMs / minute);
    return `${minutes} min ago`;
  }
  if (diffMs < day) {
    const hours = Math.floor(diffMs / hour);
    return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  }
  if (diffMs < 7 * day) {
    const days = Math.floor(diffMs / day);
    return `${days} day${days === 1 ? "" : "s"} ago`;
  }
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
};

const initialsOf = (name: string | null | undefined): string => {
  if (!name) return "IQ";
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("") || "IQ";
};

const platformLabel = (entryPoint: string | null | undefined): string => {
  if (entryPoint === "topbar_search") return "Topbar";
  if (entryPoint === "discover_search") return "Discover";
  return "Brief";
};

const scoreClass = (score: number): string => {
  if (score >= 90) return "good";
  if (score >= 80) return "mid";
  return "low";
};

const categoryOf = (niche: string | null | undefined): string => {
  if (!niche) return "General";
  // The dashboard's "Filters" column uses the niche as a category tag,
  // titlecased. Mapped here instead of pulling the brief snapshot so the
  // table stays decoupled from the schema.
  return niche
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

export default function DashboardPage() {
  const crumbs = [{ label: "Workspace" }, { label: "Dashboard", current: true }];

  return (
    <AppShell crumbs={crumbs} showSearch={true}>
      <main className="content">
        <DashboardContent />
      </main>
    </AppShell>
  );
}

function DashboardContent() {
  const { toast } = useToast();
  const [summary, setSummary] = useState<WorkspaceSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getWorkspaceSummary()
      .then((data) => {
        if (active) {
          setSummary(data);
        }
      })
      .catch((error) => {
        if (active) {
          toast(
            error instanceof Error
              ? error.message
              : "Unable to load workspace summary.",
            { type: "error" }
          );
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [toast]);

  if (loading && !summary) {
    return <DashboardSkeleton />;
  }

  if (!summary) {
    return (
      <div className="welcome">
        <div>
          <h1>Workspace unavailable</h1>
          <p className="sub">
            We couldn&apos;t load your dashboard. Try refreshing the page in a moment.
          </p>
        </div>
      </div>
    );
  }

  const { viewer, greeting, hero_counts, stats_cards, recent_searches, upgrade_usage } =
    summary;

  const firstName = viewer.name.split(/\s+/)[0] || viewer.name;
  const matchesCount = recent_searches.length;

  return (
    <>
      <div className="welcome">
        <div>
          <h1>
            {greeting.text}, {firstName}{" "}
            <span className="accent">— let&apos;s launch.</span>
          </h1>
          <p className="sub">
            {greeting.date_label}. You have{" "}
            <strong>
              {hero_counts.active_campaigns} active
            </strong>{" "}
            campaign{hero_counts.active_campaigns === 1 ? "" : "s"} and{" "}
            <strong>{hero_counts.saved_lists}</strong> saved list
            {hero_counts.saved_lists === 1 ? "" : "s"}.
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
            <span className="count-up">
              {formatCompactNumber(stats_cards.indexed_influencers, 2)}
            </span>
          </div>
          <div className="delta">
            ▲ Global catalog · {formatNumber(stats_cards.indexed_influencers)} total
          </div>
        </div>

        <div className="stat s-cyan">
          <div className="label">
            <span className="pin"></span>Categories Covered
          </div>
          <div className="value">
            <span className="count-up">{formatNumber(stats_cards.categories_covered)}</span>
          </div>
          <div className="delta">
            Across your {hero_counts.active_campaigns + hero_counts.completed_campaigns} campaigns
          </div>
        </div>

        <div className="stat s-coral">
          <div className="label">
            <span className="pin"></span>Avg Match Score
          </div>
          <div className="value">
            <span className="count-up">
              {formatNumber(stats_cards.avg_match_score_30d, 1)}
            </span>
            <span className="unit">/100</span>
          </div>
          <div className="delta">
            Last 30 days ·{" "}
            {stats_cards.avg_match_score_30d > 0
              ? `${matchesCount} recent search${matchesCount === 1 ? "" : "es"}`
              : "awaiting first scored run"}
          </div>
        </div>
      </section>

      <section className="panel" aria-label="Recent searches">
        <div className="panel-head">
          <h3>
            Recent searches <span className="live-pill">Live</span>
          </h3>
          <div className="meta">
            <span>Last {recent_searches.length || 0} runs</span>
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
            {recent_searches.length === 0 ? (
              <tr className="empty-row">
                <td colSpan={6}>
                  No searches yet. Launch your first campaign from{" "}
                  <Link href="/briefs/new">a brief</Link> or the{" "}
                  <Link href="/discover">Discover</Link> page.
                </td>
              </tr>
            ) : (
              recent_searches.map((row) => {
                // Top score isn't in the workspace summary; render an
                // em-dash so the table never fabricates a value.
                const topScore: number | null = null;
                const targetHref =
                  row.status === "running" || row.status === "pending"
                    ? `/discover?campaignId=${encodeURIComponent(row.campaign_id)}`
                    : `/shortlist?campaignId=${encodeURIComponent(row.campaign_id)}`;
                return (
                  <tr key={row.campaign_id}>
                    <td className="query">
                      <strong>{row.label || row.product}</strong>
                    </td>
                    <td>
                      <span className="tag violet">{categoryOf(row.niche)}</span>
                      <span className="tag">{platformLabel(row.entry_point)}</span>
                    </td>
                    <td>
                      {topScore != null ? (
                        <span className={`score ${scoreClass(topScore)}`}>
                          {Math.round(topScore)}
                        </span>
                      ) : (
                        <span className="score" style={{ color: "var(--muted)" }}>
                          —
                        </span>
                      )}
                    </td>
                    <td className="results">
                      {row.status === "completed"
                        ? "View"
                        : row.status === "failed"
                          ? "Failed"
                          : "Running…"}
                    </td>
                    <td className="when">{formatTimeAgo(row.created_at)}</td>
                    <td>
                      <Link className="open" href={targetHref}>
                        Open <span className="arrow">→</span>
                      </Link>
                    </td>
                  </tr>
                );
              })
            )}
            <tr className="empty-row">
              <td colSpan={6}>
                Searches are kept for 90 days. Pin a search to a saved list to keep it longer.
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <UpgradeCard usage={upgrade_usage} />
    </>
  );
}

function UpgradeCard({ usage }: { usage: WorkspaceSummary["upgrade_usage"] }) {
  return (
    <section className="panel" aria-label="Plan usage" style={{ marginTop: "18px" }}>
      <div className="panel-head">
        <h3>Plan & usage</h3>
        <div className="meta">
          <span>
            {usage.used} of {usage.limit} active briefs this month
          </span>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <div style={{ flex: 1 }}>
          <div
            style={{
              height: "8px",
              background: "var(--line, #efece4)",
              borderRadius: "4px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${Math.min(100, Math.round((usage.used / Math.max(1, usage.limit)) * 100))}%`,
                height: "100%",
                background:
                  "linear-gradient(90deg, oklch(0.58 0.22 285), oklch(0.74 0.18 30))",
              }}
            />
          </div>
        </div>
        <Link className="btn btn-ghost btn-sm" href="/settings">
          {usage.plan === "starter" ? "Upgrade to Pro" : "Manage plan"}
        </Link>
      </div>
    </section>
  );
}

function DashboardSkeleton() {
  return (
    <>
      <div className="welcome">
        <div>
          <h1>Loading your workspace…</h1>
          <p className="sub">Fetching live metrics from the matching engine.</p>
        </div>
      </div>
      <section className="stats" aria-label="Workspace stats">
        {[0, 1, 2].map((index) => (
          <div key={index} className="stat" aria-hidden="true">
            <div className="label">
              <span className="pin"></span>Loading…
            </div>
            <div className="value">
              <span className="count-up">—</span>
            </div>
            <div className="delta" style={{ color: "var(--muted)" }}>
              pulling live data
            </div>
          </div>
        ))}
      </section>
    </>
  );
}
