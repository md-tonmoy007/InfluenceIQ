"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Fragment } from "react";
import type { KeyboardEvent } from "react";

import AccountMenu from "../ui/AccountMenu";
import NotificationMenu from "../ui/NotificationMenu";
import type { CurrentUser } from "@/lib/api";

export type Crumb = {
  label: string;
  href?: string;
  current?: boolean;
};

type TopbarProps = {
  crumbs: Crumb[];
  showSearch?: boolean;
  rightVariant?: "default" | "minimal";
  orgName?: string;
  currentUser?: CurrentUser;
  sidebarOpen?: boolean;
  onOpenSidebar?: () => void;
};

export default function Topbar({
  crumbs,
  showSearch = false,
  rightVariant = "default",
  orgName = "Northwind Outdoor",
  currentUser,
  sidebarOpen = false,
  onOpenSidebar,
}: TopbarProps) {
  const router = useRouter();
  const normalizedCrumbs = crumbs.map((crumb, index) => ({
    ...crumb,
    current: crumb.current ?? index === crumbs.length - 1,
  }));

  const handleSearchKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter") return;
    const value = event.currentTarget.value.trim();
    if (!value) return;
    router.push("/matching?next=/shortlist");
  };

  return (
    <header className="topbar">
      <button
        className="mobile-menu-btn"
        type="button"
        aria-label="Open navigation"
        aria-controls="workspace-sidebar"
        aria-expanded={sidebarOpen}
        onClick={onOpenSidebar}
      >
        <svg
          className="i"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
        >
          <path d="M4 7h16M4 12h16M4 17h16" />
        </svg>
      </button>
      <div className="crumbs">
        {normalizedCrumbs.map((crumb, index) => (
          <Fragment key={`${crumb.label}-${crumb.href ?? "current"}-${index}`}>
            {crumb.href && !crumb.current ? (
              <Link href={crumb.href}>{crumb.label}</Link>
            ) : (
              <span className={crumb.current ? "here" : undefined}>
                {crumb.label}
              </span>
            )}
            {index < normalizedCrumbs.length - 1 ? <span>/</span> : null}
          </Fragment>
        ))}
      </div>

      {showSearch ? (
        <div className="search">
          <svg
            className="i"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
          >
            <circle cx="11" cy="11" r="6.5" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          <input
            id="top-search"
            placeholder="Describe your brand to find creators…"
            onKeyDown={handleSearchKeyDown}
          />
          <span className="kbd">⏎</span>
        </div>
      ) : null}

      <div className="right">
        {rightVariant !== "minimal" ? (
          <button className="icon-btn" title="Help" aria-label="Help">
            <svg
              className="i"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
            >
              <circle cx="12" cy="12" r="9" />
              <path d="M9.5 9.5a2.5 2.5 0 1 1 4 2c-.7.5-1.5 1-1.5 2" />
              <circle cx="12" cy="17" r="0.6" fill="currentColor" />
            </svg>
          </button>
        ) : null}
        <NotificationMenu />
        <AccountMenu orgName={orgName} user={currentUser} />
      </div>
    </header>
  );
}
