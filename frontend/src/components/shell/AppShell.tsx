"use client";

import { useState } from "react";
import type { ReactNode } from "react";

import AuthGate from "@/components/auth/AuthGate";
import Sidebar from "./Sidebar";
import Topbar, { Crumb } from "./Topbar";

type AppShellProps = {
  children: ReactNode;
  crumbs: Crumb[];
  showSearch?: boolean;
  rightVariant?: "default" | "minimal";
  orgName?: string;
  brandHref?: string;
};

export default function AppShell({
  children,
  crumbs,
  showSearch = false,
  rightVariant = "default",
  orgName,
  brandHref,
}: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <AuthGate>
      {(user) => (
        <div className={`app${sidebarOpen ? " sidebar-open" : ""}`}>
          <Sidebar
            brandHref={brandHref}
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
      )}
    </AuthGate>
  );
}
