'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { parseBriefSearchParams } from '@/lib/briefQuery';
import { shortlistMatches } from '@/data/matches';
import { useToast } from '@/components/ui/ToastProvider';

const platformGlyphs = {
  instagram: (
    <span className="plat pf-ig">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
        <rect x="3" y="3" width="18" height="18" rx="5" />
        <circle cx="12" cy="12" r="4" />
        <circle cx="17.5" cy="6.5" r="0.5" fill="white" />
      </svg>
    </span>
  ),
  youtube: (
    <span className="plat pf-yt">
      <svg width="12" height="10" viewBox="0 0 24 18" fill="white">
        <path d="M23.5 3.5a3 3 0 0 0-2.1-2.1C19.5 1 12 1 12 1s-7.5 0-9.4.4A3 3 0 0 0 .5 3.5C.1 5.4.1 9 .1 9s0 3.6.4 5.5a3 3 0 0 0 2.1 2.1C4.5 17 12 17 12 17s7.5 0 9.4-.4a3 3 0 0 0 2.1-2.1c.4-1.9.4-5.5.4-5.5s0-3.6-.4-5.5zM9.5 12.5v-7L15.5 9l-6 3.5z" />
      </svg>
    </span>
  ),
  tiktok: (
    <span className="plat pf-tt">
      <svg width="10" height="12" viewBox="0 0 20 22" fill="white">
        <path d="M14.5 1c.4 1.8 1.5 3.4 3 4.4 1.1.7 2.5 1.1 3.9 1.1V11c-1.6 0-3.2-.4-4.6-1.1-.6-.3-1.2-.7-1.7-1.1v6.6c0 4.1-3.4 7.5-7.5 7.5-1.6 0-3.1-.5-4.3-1.4-1.9-1.4-3.2-3.7-3.2-6.2 0-4.1 3.4-7.5 7.5-7.5.4 0 .9 0 1.3.1v4.4c-.4-.1-.8-.2-1.3-.2-1.7 0-3.1 1.4-3.1 3.1s1.4 3.2 3.2 3.2 3.2-1.4 3.2-3.1V1h3.6z" />
      </svg>
    </span>
  ),
  facebook: (
    <span className="plat pf-fb">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="white">
        <path d="M14 9V7c0-1 .5-2 2-2h2V1h-3c-3 0-5 2-5 5v3H7v4h3v9h4v-9h3l1-4h-4z" />
      </svg>
    </span>
  ),
};

const tierClass = {
  Rising: 'tier-rising',
  Established: 'tier-established',
  Premium: 'tier-premium',
};

export default function ShortlistPageClient() {
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const brief = parseBriefSearchParams(Object.fromEntries(searchParams.entries()));

  const [selectedIndices, setSelectedIndices] = useState<number[]>([0, 1]);
  const [showPdf, setShowPdf] = useState(false);

  useEffect(() => {
    if (showPdf) {
      document.body.style.overflow = 'hidden';
      const handleEsc = (e: KeyboardEvent) => {
        if (e.key === 'Escape') setShowPdf(false);
      };
      window.addEventListener('keydown', handleEsc);
      return () => window.removeEventListener('keydown', handleEsc);
    } else {
      document.body.style.overflow = '';
    }
  }, [showPdf]);

  const toggleSelection = (idx: number) => {
    setSelectedIndices(prev =>
      prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]
    );
  };

  const handleExport = () => {
    if (selectedIndices.length === 0) {
      toast('Select at least one creator to export.', { type: 'info' });
      return;
    }
    setShowPdf(true);
    toast('Shortlist exported — opening preview.', { type: 'success' });
  };

  const handleCompare = () => {
    if (selectedIndices.length < 2) {
      toast('Select at least 2 creators to compare.', { type: 'info' });
    } else {
      toast(`Opening compare view for ${selectedIndices.length} creators…`, { type: 'info' });
    }
  };

  const chosenMatches = selectedIndices.map(i => shortlistMatches[i]).filter(Boolean);
  const today = new Date().toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Top matches for <span className="accent">{brief.brand}&apos;s</span> campaign</h1>
          <p className="page-sub">
            <span className="pill">{brief.product}</span>
            <span className="pill">{brief.goal}</span>
            <span className="pill">{brief.platforms.join(' + ')}</span>
            <span className="pill">{brief.tier}</span>
            <span className="pill">{brief.budget}</span>
          </p>
        </div>
        <span className="toast"><span className="dot"></span>Ranked from 50,247 profiles · 1.8s</span>
      </div>

      <div className="top-actions">
        <div className="left">
          <span className="selection-pill"><span className="n">{selectedIndices.length}</span> selected</span>
          <span style={{ fontSize: '12.5px', color: 'var(--muted)' }}>Tick the rows you want to compare or export.</span>
        </div>
        <button className="btn btn-ghost" type="button" onClick={handleCompare}>
          <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><rect x="3" y="5" width="8" height="14" rx="1.5" /><rect x="13" y="5" width="8" height="14" rx="1.5" /><line x1="12" y1="3" x2="12" y2="21" strokeDasharray="2 3" /></svg>
          Compare Selected
        </button>
        <button className="btn btn-primary" type="button" onClick={handleExport}>
          <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M9 14l3 3 3-3M12 17V11" /></svg>
          Export Shortlist as PDF
        </button>
      </div>

      <div className="layout">
        {/* ===== Ranked list ===== */}
        <section className="list">
          {shortlistMatches.map((m, i) => {
            const circ = 2 * Math.PI * 28;
            const dash = circ * (m.match / 100);
            const matchClass = m.match >= 92 ? 'high' : 'mid';
            const isChecked = selectedIndices.includes(i);

            return (
              <article key={i} className={`row ${isChecked ? 'checked' : ''}`} style={{ animationDelay: `${0.06 * i}s` }}>
                <div className="rank-col" onClick={() => toggleSelection(i)}>
                  <div className="rank">{m.rank}</div>
                  <div className={`checkbox ${isChecked ? 'on' : ''}`} role="checkbox" aria-checked={isChecked}>
                    <svg viewBox="0 0 16 12" width="10" height="8"><path d="M1 6 L6 11 L15 1" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none" /></svg>
                  </div>
                </div>
                <div className="av-col">
                  <div className="av" style={{ background: m.avBg }}>
                    {m.avatar}
                    {platformGlyphs[m.platform]}
                  </div>
                </div>
                <div className="info-col">
                  <div className="name-row">
                    <span className="name">{m.name}</span>
                    {m.verified && (
                      <svg className="verified" viewBox="0 0 24 24" fill="currentColor"><path d="M12 1l2.4 2.1 3.1-.4 1.4 2.8 2.8 1.4-.4 3.1L23 12l-2.1 2.4.4 3.1-2.8 1.4-1.4 2.8-3.1-.4L12 23l-2.4-2.1-3.1.4-1.4-2.8-2.8-1.4.4-3.1L1 12l2.1-2.4-.4-3.1 2.8-1.4 1.4-2.8 3.1.4L12 1z" /><path d="M8.5 12.5l2.4 2.4 4.6-5" stroke="white" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    )}
                    <span className="handle">{m.handle}</span>
                  </div>
                  <div className="reason">
                    <span className="spark"><svg viewBox="0 0 24 24" width="10" height="10" fill="currentColor"><path d="M12 3l1.8 4.5L18 9.3l-4.2 1.8L12 15.6l-1.8-4.5L6 9.3l4.2-1.8L12 3z" /></svg></span>
                    <span dangerouslySetInnerHTML={{ __html: m.reason }} />
                  </div>
                  <div className="tag-row">
                    <span className={`tag tag-tier ${tierClass[m.tier]}`}>{m.tier}</span>
                    {m.tags.map(t => <span key={t} className="tag">{t}</span>)}
                  </div>
                </div>
                <div className="stats-col">
                  <div><div className="lbl">Followers</div><div className="val">{m.followers}</div></div>
                  <div><div className="lbl">Engagement</div><div className="val eng">{m.engagement}</div></div>
                  <div><div className="lbl">Avg views</div><div className="val">{m.avgViews}</div></div>
                  <div><div className="lbl">Rate / post</div><div className="val">{m.rate}</div></div>
                </div>
                <div className="actions-col">
                  <div className="match-ring" title={`${m.match}% match`}>
                    <svg width="74" height="74" viewBox="0 0 74 74">
                      <defs>
                        <linearGradient id={`grad-${i}`} x1="0" y1="0" x2="1" y2="1">
                          <stop offset="0%" stopColor="oklch(0.58 0.22 285)" />
                          <stop offset="100%" stopColor="oklch(0.74 0.18 30)" />
                        </linearGradient>
                      </defs>
                      <circle cx="37" cy="37" r="28" fill="none" stroke="var(--paper-2)" strokeWidth="6" />
                      <circle cx="37" cy="37" r="28" fill="none" stroke={`url(#grad-${i})`} strokeWidth="6" strokeLinecap="round"
                        strokeDasharray={`${dash} ${circ}`} style={{ transition: 'stroke-dasharray 1s' }} />
                    </svg>
                    <div className={`val ${matchClass}`}>{m.match}<span className="pct">% MATCH</span></div>
                  </div>
                  <Link href="/profile/lila-park" className="row-cta">View profile <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M13 6l6 6-6 6" /></svg></Link>
                </div>
              </article>
            );
          })}
        </section>

        {/* ===== Brief summary sidebar ===== */}
        <aside className="brief-side">
          <div className="head">
            <h4>Submitted brief</h4>
            <div className="sub">Reference</div>
          </div>
          <div className="body">
            <div className="row-k"><span className="k">Brand</span><span className="v">{brief.brand}</span></div>
            <div className="row-k"><span className="k">Product</span><span className="v">{brief.product}</span></div>
            <div className="row-k"><span className="k">Category</span><span className="v">{brief.category}</span></div>
            <div className="row-k"><span className="k">Goal</span><span className="v">{brief.goal}</span></div>
            <div className="row-k">
              <span className="k">Ages</span>
              <span className="v stack">
                {brief.ages.length ? brief.ages.map(a => <span key={a} className="pill">{a}</span>) : <span style={{ color: 'var(--muted-soft)', fontStyle: 'italic' }}>none</span>}
              </span>
            </div>
            <div className="row-k"><span className="k">Gender</span><span className="v">{brief.gender}</span></div>
            <div className="row-k">
              <span className="k">Locations</span>
              <span className="v stack">
                {brief.locs.length ? brief.locs.map(l => <span key={l} className="pill">{l}</span>) : <span style={{ color: 'var(--muted-soft)', fontStyle: 'italic' }}>none</span>}
              </span>
            </div>
            <div className="row-k">
              <span className="k">Platforms</span>
              <span className="v stack">
                {brief.platforms.length ? brief.platforms.map(p => <span key={p} className="pill">{p}</span>) : <span style={{ color: 'var(--muted-soft)', fontStyle: 'italic' }}>none</span>}
              </span>
            </div>
            <div className="row-k"><span className="k">Tier</span><span className="v">{brief.tier}</span></div>
            <div className="row-k">
              <span className="k">Budget</span>
              <span className="v">
                {brief.budget.includes('USD') ? (
                  <>
                    {brief.budget.replace(' USD', '')}
                    <br />
                    <span style={{ fontSize: '11px', color: 'var(--muted)' }}>USD</span>
                  </>
                ) : brief.budget}
              </span>
            </div>
          </div>
          <div className="conf">
            <div className="t">AI confidence <strong>94%</strong></div>
            <div className="bar"></div>
            <div className="hint">High-confidence shortlist. Brief was specific on geography, platform, and audience age — all top-5 results meet your hard filters.</div>
          </div>
          <div className="foot">
            <Link className="b" href="/briefs/new"><svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z" /></svg>Edit brief</Link>
            <button className="b" type="button"><svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M21 12a9 9 0 1 1-3-6.7M21 3v6h-6" /></svg>Re-run matching</button>
          </div>
        </aside>
      </div>

      <div className={`pdf-preview ${showPdf ? 'open' : ''}`} aria-hidden={!showPdf}>
        <div className="pdf-preview-panel" role="dialog" aria-modal="true" aria-label="Exported shortlist preview">
          <div className="pdf-preview-head">
            <div>
              <div className="pdf-preview-title">Shortlist PDF Preview</div>
              <div className="pdf-preview-sub">Generated {today} · {chosenMatches.length} creator{chosenMatches.length === 1 ? '' : 's'} selected.</div>
            </div>
            <div className="pdf-preview-actions">
              <button className="btn btn-ghost btn-sm" type="button" onClick={() => setShowPdf(false)}>Close</button>
              <button className="btn btn-primary btn-sm" type="button" onClick={() => window.print()}>Open print dialog</button>
            </div>
          </div>
          <div className="pdf-preview-body">
            <div className="pdf-sheet">
              <h2>{brief.product} — Creator Shortlist</h2>
              <div className="meta">
                <span><strong>Brand:</strong> {brief.brand}</span>
                <span><strong>Goal:</strong> {brief.goal}</span>
                <span><strong>Platforms:</strong> {brief.platforms.join(' + ')}</span>
                <span><strong>Exported:</strong> {today}</span>
                <span className="pdf-pill">{chosenMatches.length} creators</span>
              </div>
              <table className="pdf-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Creator</th>
                    <th>Platform</th>
                    <th>Followers</th>
                    <th>Engagement</th>
                    <th>Avg Views</th>
                    <th>Rate</th>
                    <th>Match</th>
                  </tr>
                </thead>
                <tbody>
                  {chosenMatches.map(m => (
                    <tr key={m.rank}>
                      <td>{m.rank}</td>
                      <td>
                        <div className="pdf-name">{m.name}</div>
                        <span className="pdf-handle">{m.handle}</span>
                        <div className="pdf-tags">{m.tags.slice(0, 3).map(t => <span key={t} className="pdf-tag">{t}</span>)}</div>
                      </td>
                      <td>{m.platform.charAt(0).toUpperCase() + m.platform.slice(1)}</td>
                      <td>{m.followers}</td>
                      <td>{m.engagement}</td>
                      <td>{m.avgViews}</td>
                      <td>{m.rate}</td>
                      <td>{m.match}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
