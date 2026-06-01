import type { ReactNode } from "react";

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
  return (
    <div className="app">
      <Sidebar brandHref={brandHref} />
      <div className="main">
        <Topbar
          crumbs={crumbs}
          showSearch={showSearch}
          rightVariant={rightVariant}
          orgName={orgName}
        />
        {children}
      </div>
    </div>
  );
}
