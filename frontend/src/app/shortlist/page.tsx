import '../shortlist.css';
import AppShell from '@/components/shell/AppShell';
import ShortlistPageClient from '@/components/shortlist/ShortlistPageClient';
import { Suspense } from 'react';

export default async function ShortlistPage({ searchParams }: { searchParams: Promise<{ product?: string }> }) {
  const params = await searchParams;
  const product = params.product || 'Shortlist';

  return (
    <AppShell
      crumbs={[
        { label: 'Workspace', href: '/dashboard' },
        { label: 'Campaign Briefs', href: '/briefs' },
        { label: product, current: true }
      ]}
      showSearch={false}
    >
      <main className="content">
        <Suspense fallback={<div>Loading shortlist...</div>}>
          <ShortlistPageClient />
        </Suspense>
      </main>
    </AppShell>
  );
}
