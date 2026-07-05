import React from "react";

import AppShell from "@/components/shell/AppShell";
import ReportPageClient from "@/components/report/ReportPageClient";
import { shortlistHref } from "@/lib/routes";
import "../../report.css";

export default async function ReportPage({
  params,
  searchParams,
}: {
  params: Promise<{ influencerId: string }>;
  searchParams: Promise<{ reportId?: string; runId?: string; campaignId?: string }>;
}) {
  const resolvedParams = await params;
  const resolvedSearchParams = await searchParams;

  const crumbs = [
    { label: "Workspace", href: "/" },
    resolvedSearchParams.campaignId
      ? { label: "Shortlist", href: shortlistHref(resolvedSearchParams.campaignId) }
      : { label: "Reports" },
    { label: "Deep analysis", current: true },
  ];

  return (
    <AppShell crumbs={crumbs}>
      <main className="content">
        <ReportPageClient
          influencerId={resolvedParams.influencerId}
          reportId={resolvedSearchParams.reportId}
          runId={resolvedSearchParams.runId}
          campaignId={resolvedSearchParams.campaignId}
        />
      </main>
    </AppShell>
  );
}
