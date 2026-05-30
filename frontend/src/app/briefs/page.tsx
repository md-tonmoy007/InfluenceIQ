import '../briefs.css';
import AppShell from '@/components/shell/AppShell';
import Link from 'next/link';

export default function BriefsPage() {
  return (
    <AppShell
      crumbs={[{ label: 'Workspace' }, { label: 'Campaign Briefs', current: true }]}
      showSearch={false}
    >
      <main className="content">
        <div className="page-head">
          <div>
            <h1>Campaign <span className="ac">briefs.</span></h1>
            <p className="sub">A timeline of every brief you&apos;ve submitted to the matching engine. Open one to see its shortlist or duplicate it for a new push.</p>
          </div>
          <Link href="/briefs/new" className="btn btn-primary btn-sm">
            <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
              <path d="M12 5v14M5 12h14" />
            </svg>
            Start New Campaign Brief
          </Link>
        </div>

        <div className="seg-tabs">
          <button className="active" type="button">All <span className="count">5</span></button>
          <button type="button">Active <span className="count">2</span></button>
          <button type="button">Drafts <span className="count">1</span></button>
          <button type="button">Completed <span className="count">2</span></button>
        </div>

        <div className="brief-list">
          <Link className="brief" href="/shortlist">
            <span className="b-glyph gl-v">R</span>
            <div className="b-body">
              <div className="b-head">
                <span className="b-name">Ramadan Campaign 2026</span>
                <span className="b-status active">Active</span>
              </div>
              <div className="b-meta">
                <span><strong>Northwind Outdoor</strong></span>
                <span className="dot"></span>
                <span>Awareness · Sales</span>
                <span className="dot"></span>
                <span>IG · TT</span>
                <span className="dot"></span>
                <span>$12,000/mo</span>
                <span className="dot"></span>
                <span>Created May 5</span>
              </div>
            </div>
            <div className="b-stats">
              <div className="b-stat"><div className="l">Matches</div><div className="v">214</div></div>
              <div className="b-stat"><div className="l">Top match</div><div className="v good">96</div></div>
              <div className="b-stat"><div className="l">Shortlisted</div><div className="v">14</div></div>
            </div>
            <span className="b-arrow">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </span>
          </Link>

          <Link className="brief" href="/shortlist">
            <span className="b-glyph gl-cy">S</span>
            <div className="b-body">
              <div className="b-head">
                <span className="b-name">SS26 Trail Capsule</span>
                <span className="b-status active">Active</span>
              </div>
              <div className="b-meta">
                <span><strong>Northwind Outdoor</strong></span>
                <span className="dot"></span>
                <span>Product Launch</span>
                <span className="dot"></span>
                <span>IG · YT</span>
                <span className="dot"></span>
                <span>$8,500/mo</span>
                <span className="dot"></span>
                <span>Created May 2</span>
              </div>
            </div>
            <div className="b-stats">
              <div className="b-stat"><div className="l">Matches</div><div className="v">128</div></div>
              <div className="b-stat"><div className="l">Top match</div><div className="v good">94</div></div>
              <div className="b-stat"><div className="l">Shortlisted</div><div className="v">9</div></div>
            </div>
            <span className="b-arrow">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </span>
          </Link>

          <Link className="brief" href="/briefs/new">
            <span className="b-glyph gl-d">H</span>
            <div className="b-body">
              <div className="b-head">
                <span className="b-name">Holiday gifting (US + UK)</span>
                <span className="b-status draft">Draft</span>
              </div>
              <div className="b-meta">
                <span><strong>Northwind Outdoor</strong></span>
                <span className="dot"></span>
                <span>Sales</span>
                <span className="dot"></span>
                <span>IG · TT</span>
                <span className="dot"></span>
                <span>$15,000/mo</span>
                <span className="dot"></span>
                <span>Last edited Apr 28</span>
              </div>
            </div>
            <div className="b-stats">
              <div className="b-stat"><div className="l">Matches</div><div className="v" style={{ color: 'var(--muted)' }}>—</div></div>
              <div className="b-stat"><div className="l">Top match</div><div className="v" style={{ color: 'var(--muted)' }}>—</div></div>
              <div className="b-stat"><div className="l">Shortlisted</div><div className="v" style={{ color: 'var(--muted)' }}>0</div></div>
            </div>
            <span className="b-arrow">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </span>
          </Link>

          <Link className="brief" href="/shortlist">
            <span className="b-glyph gl-c">F</span>
            <div className="b-body">
              <div className="b-head">
                <span className="b-name">Father&apos;s Day · grooming & tools</span>
                <span className="b-status complete">Completed</span>
              </div>
              <div className="b-meta">
                <span><strong>Northwind Outdoor</strong></span>
                <span className="dot"></span>
                <span>Sales</span>
                <span className="dot"></span>
                <span>IG · YT</span>
                <span className="dot"></span>
                <span>$6,400/mo</span>
                <span className="dot"></span>
                <span>Closed May 1</span>
              </div>
            </div>
            <div className="b-stats">
              <div className="b-stat"><div className="l">Matches</div><div className="v">86</div></div>
              <div className="b-stat"><div className="l">Top match</div><div className="v good">91</div></div>
              <div className="b-stat"><div className="l">Contracted</div><div className="v">7</div></div>
            </div>
            <span className="b-arrow">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </span>
          </Link>

          <Link className="brief" href="/shortlist">
            <span className="b-glyph gl-g">Q</span>
            <div className="b-body">
              <div className="b-head">
                <span className="b-name">Q1 awareness — Pilates capsule</span>
                <span className="b-status complete">Completed</span>
              </div>
              <div className="b-meta">
                <span><strong>Northwind Outdoor</strong></span>
                <span className="dot"></span>
                <span>Awareness</span>
                <span className="dot"></span>
                <span>IG · TT</span>
                <span className="dot"></span>
                <span>$4,200/mo</span>
                <span className="dot"></span>
                <span>Closed Mar 18</span>
              </div>
            </div>
            <div className="b-stats">
              <div className="b-stat"><div className="l">Matches</div><div className="v">312</div></div>
              <div className="b-stat"><div className="l">Top match</div><div className="v good">93</div></div>
              <div className="b-stat"><div className="l">Contracted</div><div className="v">12</div></div>
            </div>
            <span className="b-arrow">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </span>
          </Link>

          <Link className="new-brief" href="/briefs/new">
            <span className="pp">+</span>
            <div>
              <div className="t">Start a new campaign brief</div>
              <div className="s">Describe your product, audience and budget — the matcher takes it from there.</div>
            </div>
          </Link>
        </div>
      </main>
    </AppShell>
  );
}
