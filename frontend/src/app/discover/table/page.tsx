import React from "react";
import Link from "next/link";
import AppShell from "@/components/shell/AppShell";
import LiveCampaignDiscover from "@/components/discover/LiveCampaignDiscover";
import CampaignDiscoverPageClient from "@/components/discover/CampaignDiscoverPageClient";
import { shortlistHref } from "@/lib/routes";
import "../../discover-table.css";

export default async function DiscoverTablePage({
  searchParams,
}: {
  searchParams: Promise<{ campaignId?: string }>;
}) {
  const params = await searchParams;
  const campaignId = params.campaignId;
  const crumbs = [
    { label: "Workspace" },
    { label: "Discover", href: "/discover" },
    { label: "Table view", current: true },
  ];

  if (campaignId) {
    return (
      <AppShell crumbs={crumbs} showSearch={false}>
        <main className="content">
          <div className="page-head">
            <div>
              <h1>
                Discover <span className="accent">creators.</span>
              </h1>
              <p className="sub">
                Data-dense campaign view with live filters and pagination.
              </p>
            </div>
            <Link className="btn btn-ghost" href={shortlistHref(campaignId)}>
              Back to shortlist
            </Link>
          </div>
          <CampaignDiscoverPageClient campaignId={campaignId} variant="table" />
        </main>
      </AppShell>
    );
  }

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
        <LiveCampaignDiscover variant="table" />
      </main>
    </AppShell>
  );
}
