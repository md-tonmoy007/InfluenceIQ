import React from "react";
import AppShell from "@/components/shell/AppShell";
import LiveProfilePageClient from "@/components/profile/LiveProfilePageClient";
import "../../profile.css";

export default async function ProfilePage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ campaignId?: string }>;
}) {
  const resolvedParams = await params;
  const resolvedSearchParams = await searchParams;

  const crumbs = [
    { label: "Workspace", href: "/" },
    { label: "Discover", href: resolvedSearchParams.campaignId ? `/discover?campaignId=${encodeURIComponent(resolvedSearchParams.campaignId)}` : "/discover" },
    { label: "Creator profile", current: true },
  ];

  return (
    <AppShell crumbs={crumbs}>
      <main className="content">
        <LiveProfilePageClient
          campaignId={resolvedSearchParams.campaignId}
          influencerId={resolvedParams.id}
        />
      </main>
    </AppShell>
  );
}
