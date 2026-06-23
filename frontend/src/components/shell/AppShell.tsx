"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import AuthGate from "@/components/auth/AuthGate";
import Sidebar from "./Sidebar";
import Topbar, { Crumb } from "./Topbar";
import {
  getWorkspaceSummary,
  type WorkspaceSummary,
} from "@/lib/api";

type AppShellProps = {
  children: ReactNode;
  crumbs: Crumb[];
  showSearch?: boolean;
  rightVariant?: "default" | "minimal";
  orgName?: string;
  brandHref?: string;
};

type WorkspaceCounts = {
  briefs: number;
  savedLists: number;
  plan: string;
};

const WorkspaceCountsContext = createContext<WorkspaceCounts | null>(null);

export function useWorkspaceCounts(): WorkspaceCounts | null {
  return useContext(WorkspaceCountsContext);
}

export default function AppShell({
  children,
  crumbs,
  showSearch = false,
  rightVariant = "default",
  orgName,
  brandHref,
}: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [summary, setSummary] = useState<WorkspaceSummary | null>(null);

  useEffect(() => {
    let active = true;
    getWorkspaceSummary()
      .then((data) => {
        if (active) {
          setSummary(data);
        }
      })
      .catch(() => {
        // Soft-fail: the shell keeps rendering with zero counts.
      });
    return () => {
      active = false;
    };
  }, []);

  const counts = useMemo<WorkspaceCounts | null>(() => {
    if (!summary) return null;
    return {
      briefs: summary.sidebar_counts.briefs,
      savedLists: summary.sidebar_counts.saved_lists,
      plan: summary.upgrade_usage.plan,
    };
  }, [summary]);

  return (
    <AuthGate>
      {(user) => (
        <WorkspaceCountsContext.Provider value={counts}>
          <div className={`app${sidebarOpen ? " sidebar-open" : ""}`}>
            <Sidebar
              brandHref={brandHref}
              counts={counts}
              onNavigate={() => setSidebarOpen(false)}
            />
            <button
              className="sidebar-backdrop"
              type="button"
              aria-label="Close navigation"
              onClick={() => setSidebarOpen(false)}
            />
            <div className="main">
              <Topbar
                crumbs={crumbs}
                showSearch={showSearch}
                rightVariant={rightVariant}
                orgName={orgName ?? user.company_name}
                currentUser={user}
                sidebarOpen={sidebarOpen}
                onOpenSidebar={() => setSidebarOpen(true)}
              />
              {children}
            </div>
          </div>
        </WorkspaceCountsContext.Provider>
      )}
    </AuthGate>
  );
}
