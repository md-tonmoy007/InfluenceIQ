import React from "react";
import AppShell from "@/components/shell/AppShell";
import DiscoverTable from "@/components/discover/DiscoverTable";
import "../../discover-table.css";

export default function DiscoverTablePage() {
  const crumbs = [
    { label: "Workspace" },
    { label: "Discover", href: "/discover" },
    { label: "Table view", current: true },
  ];

  return (
    <AppShell crumbs={crumbs} showSearch={false}>
      <main className="content">
        <div className="page-head">
          <div>
            <h1>
              Discover <span className="accent">creators.</span>
            </h1>
            <p className="sub">
              Data-dense view across 50,247 ranked profiles. Sort any column,
              multi-select, then save to a list.
            </p>
          </div>
        </div>
        <DiscoverTable />
      </main>
    </AppShell>
  );
}
