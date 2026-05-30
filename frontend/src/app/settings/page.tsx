import React from 'react';
import AppShell from '@/components/shell/AppShell';
import SettingsToggles from '@/components/settings/SettingsToggles';
import SettingsNav from '@/components/settings/SettingsNav';
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
            <section className="card" id="profile">
              <h2>Profile</h2>
              <p className="desc">This is what teammates and creators see when you interact on InfluenceIQ.</p>
              <div className="avatar-row">
                <span className="av-big">EM</span>
                <a className="change-pic">Change photo</a>
              </div>
              <div className="row">
                <div className="field">
                  <label>Full name</label>
                  <input defaultValue="Elena Marchetti" />
                </div>
                <div className="field">
                  <label>Role</label>
                  <input defaultValue="Head of Growth" />
                </div>
              </div>
              <div className="row">
                <div className="field">
                  <label>Work email</label>
                  <input defaultValue="elena@northwind.co" />
                </div>
                <div className="field">
                  <label>Timezone</label>
                  <select defaultValue="America/Toronto (EDT)">
                    <option>America/Toronto (EDT)</option>
                    <option>America/Los_Angeles</option>
                    <option>Europe/London</option>
                    <option>Asia/Dhaka</option>
                  </select>
                </div>
              </div>
            </section>

            <section className="card" id="brand">
              <h2>Brand</h2>
              <p className="desc">Used to seed match scoring across all your briefs.</p>
              <div className="row">
                <div className="field">
                  <label>Brand name</label>
                  <input defaultValue="Northwind Outdoor" />
                </div>
                <div className="field">
                  <label>Industry</label>
                  <select defaultValue="Outdoor & activewear">
                    <option>Outdoor &amp; activewear</option>
                  </select>
                </div>
              </div>
              <div className="row">
                <div className="field">
                  <label>Country</label>
                  <select defaultValue="Canada">
                    <option>Canada</option>
                  </select>
                </div>
                <div className="field">
                  <label>Company size</label>
                  <select defaultValue="11–50">
                    <option>11–50</option>
                  </select>
                </div>
              </div>
            </section>

            <section className="card" id="billing">
              <h2>Plan &amp; Billing</h2>
              <p className="desc">You&apos;re on the Starter plan. Upgrade for unlimited briefs and direct outreach.</p>

              <div className="plan-grid">
                <div className="plan current">
                  <h3>Starter</h3>
                  <div className="price">
                    $0<span className="u">/mo</span>
                  </div>
                  <ul>
                    <li>5 active briefs</li>
                    <li>Up to 200 matches</li>
                    <li>CSV export</li>
                  </ul>
                </div>
                <div className="plan">
                  <h3>Pro</h3>
                  <div className="price">
                    $149<span className="u">/mo</span>
                  </div>
                  <ul>
                    <li>Unlimited briefs</li>
                    <li>Direct outreach</li>
                    <li>Saved-list CRM</li>
                    <li>Sentiment analytics</li>
                  </ul>
                </div>
                <div className="plan">
                  <h3>Scale</h3>
                  <div className="price">
                    $499<span className="u">/mo</span>
                  </div>
                  <ul>
                    <li>Everything in Pro</li>
                    <li>5 seats included</li>
                    <li>API access</li>
                    <li>Priority support</li>
                  </ul>
                </div>
              </div>

              <div style={{ marginTop: '16px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <button className="btn btn-primary btn-sm" type="button">
                  Upgrade to Pro
                </button>
                <button className="btn btn-ghost btn-sm" type="button">
                  Compare plans →
                </button>
              </div>

              <div style={{ marginTop: '22px', paddingTop: '18px', borderTop: '1px solid var(--line-soft)' }}>
                <div style={{ fontSize: '11.5px', fontFamily: "'JetBrains Mono',monospace", letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--muted)', marginBottom: '10px' }}>
                  Payment method
                </div>
                <div className="billing-card">
                  <span className="pic">VISA</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '13.5px', fontWeight: 500 }}>Visa ending in 4242</div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '1px' }}>Expires 09 / 2028</div>
                  </div>
                  <button className="btn btn-ghost btn-sm" type="button">
                    Update
                  </button>
                </div>
              </div>
            </section>

            <SettingsToggles />

            <section className="card" id="api">
              <h2>API &amp; Integrations</h2>
              <p className="desc">Connect InfluenceIQ to your campaign stack.</p>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button className="btn btn-ghost btn-sm" type="button">
                  Connect Slack
                </button>
                <button className="btn btn-ghost btn-sm" type="button">
                  Connect HubSpot
                </button>
                <button className="btn btn-ghost btn-sm" type="button">
                  Generate API key
                </button>
              </div>
            </section>

            <section className="card danger" id="danger">
              <h2>Delete account</h2>
              <p className="desc" style={{ color: 'var(--warn-ink)', opacity: 0.8 }}>
                Permanently delete your account and all associated briefs, lists and search history. This cannot be undone.
              </p>
              <button className="btn btn-ghost btn-sm" style={{ borderColor: 'color-mix(in oklab,var(--warn),white 60%)', color: 'var(--warn-ink)' }} type="button">
                Delete account
              </button>
            </section>
          </div>
        </div>
      </main>
    </AppShell>
  );
}
