import React, { Suspense } from 'react';
import AppShell from '@/components/shell/AppShell';
import SettingsToggles from '@/components/settings/SettingsToggles';
import SettingsNav from '@/components/settings/SettingsNav';
import ProfileForm from '@/components/settings/ProfileForm';
import BrandForm from '@/components/settings/BrandForm';
import PlanBillingSection from '@/components/settings/PlanBillingSection';
import IntegrationsSection from '@/components/settings/IntegrationsSection';
import ApiKeysSection from '@/components/settings/ApiKeysSection';
import DangerZone from '@/components/settings/DangerZone';
import '../settings.css';

export default function SettingsPage() {
  const crumbs = [
    { label: 'Workspace', href: '/' },
    { label: 'Settings', current: true },
  ];

  return (
    <AppShell crumbs={crumbs} showSearch={false}>
      <main className="content">
        <div className="page-head">
          <h1>
            Account <span className="ac">settings.</span>
          </h1>
          <p className="sub">Manage your profile, plan, and notification preferences.</p>
        </div>

        <div className="settings-layout">
          <SettingsNav />

          <div>
            <ProfileForm />
            <BrandForm />
            <Suspense fallback={<section className="card"><p className="desc">Loading billing…</p></section>}>
              <PlanBillingSection />
            </Suspense>
            <SettingsToggles />
            <IntegrationsSection />
            <ApiKeysSection />
            <DangerZone />
          </div>
        </div>
      </main>
    </AppShell>
  );
}
