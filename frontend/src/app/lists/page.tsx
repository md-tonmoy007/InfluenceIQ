'use client';

import React, { useState } from 'react';
import AppShell from '@/components/shell/AppShell';
import ListsPageClient from '@/components/lists/ListsPageClient';
import { Crumb } from '@/components/shell/Topbar';
import '../lists.css';

export default function ListsPage() {
  const [crumbs, setCrumbs] = useState<Crumb[]>([
    { label: 'Workspace', href: '/' },
    { label: 'Saved Lists' },
  ]);

  return (
    <AppShell crumbs={crumbs}>
      <main className="content">
        <ListsPageClient setCrumbs={setCrumbs} />
      </main>
    </AppShell>
  );
}
