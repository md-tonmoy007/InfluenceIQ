"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { formatPlanName } from "../../lib/api";
import { routes } from "../../lib/routes";
import BrandMark from "./BrandMark";

type SidebarCounts = {
  briefs: number;
  savedLists: number;
  plan: string;
};

type SidebarProps = {
  brandHref?: string;
  onNavigate?: () => void;
  counts?: SidebarCounts | null;
};

export default function Sidebar({
  brandHref = routes.dashboard,
  onNavigate,
  counts,
}: SidebarProps) {
  const pathname = usePathname() ?? "";
  const briefs = counts?.briefs ?? 0;
  const savedLists = counts?.savedLists ?? 0;
  const plan = counts?.plan ?? "starter";
  const planLabel = formatPlanName(plan);

  const navItems = [
    {
      label: "Dashboard",
      href: routes.dashboard,
      activePaths: [routes.dashboard],
      icon: (
        <svg
          className="ico i"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
        >
          <rect x="3" y="3" width="7" height="9" rx="1.4" />
          <rect x="14" y="3" width="7" height="5" rx="1.4" />
          <rect x="14" y="12" width="7" height="9" rx="1.4" />
          <rect x="3" y="16" width="7" height="5" rx="1.4" />
        </svg>
      ),
    },
    {
      label: "Discover",
      href: routes.discover,
      activePaths: [routes.discover, routes.discoverTable, "/profile"],
      icon: (
        <svg
          className="ico i"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
        >
          <circle cx="11" cy="11" r="6.5" />
          <path d="m20 20-3.5-3.5" />
        </svg>
      ),
    },
    {
      label: "Saved Lists",
      href: routes.lists,
      activePaths: [routes.lists],
      count: savedLists,
      icon: (
        <svg
          className="ico i"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
        >
          <path d="M19 21l-7-4.5L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16Z" />
        </svg>
      ),
    },
    {
      label: "Campaign Briefs",
      href: routes.briefs,
      activePaths: [routes.briefs, routes.newBrief, routes.shortlist],
      count: briefs,
      icon: (
        <svg
          className="ico i"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
        >
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
          <path d="M14 3v5h5" />
          <path d="M9 13h6M9 17h4" />
        </svg>
      ),
    },
    {
      label: "Settings",
      href: routes.settings,
      activePaths: [routes.settings],
      icon: (
        <svg
          className="ico i"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
        >
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
        </svg>
      ),
    },
  ];

  const isActive = (paths: string[]) =>
    paths.some(
      (path) => pathname === path || pathname.startsWith(`${path}/`)
    );

  return (
    <aside className="sidebar" id="workspace-sidebar">
      <Link
        className="brand"
        href={brandHref}
        aria-label="InfluenceIQ home"
        onClick={onNavigate}
      >
        <BrandMark />
        <span>InfluenceIQ</span>
      </Link>

      <div className="nav-section-label">Workspace</div>
      {navItems.map((item) => {
        const active = isActive(item.activePaths);
        return (
          <Link
            key={item.label}
            className={`side-link${active ? " active" : ""}`}
            href={item.href}
            onClick={onNavigate}
          >
            {item.icon}
            {item.label}
            {typeof item.count === "number" ? (
              <span className="count">{item.count}</span>
            ) : null}
          </Link>
        );
      })}

      <div className="side-spacer"></div>

      <div className="upgrade-card">
        <span className="sparkle">✦</span>
        <div className="t">You&apos;re on {planLabel}</div>
        <div className="s">
          {plan === "starter"
            ? "Upgrade to Pro to unlock unlimited briefs and CRM exports."
            : `Manage your ${planLabel} plan in Settings.`}
        </div>
        <Link className="btn btn-primary upbtn" href="/settings">
          {plan === "starter" ? "Upgrade to Pro" : "Manage plan"}
          <span className="arrow">→</span>
        </Link>
      </div>
    </aside>
  );
}
