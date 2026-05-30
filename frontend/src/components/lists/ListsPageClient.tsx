'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { savedLists, savedListRows, SavedList } from '@/data/lists';
import { useToast } from '@/components/ui/ToastProvider';
import { Crumb } from '@/components/shell/Topbar';

const platformGlyphSm = {
  instagram: (
    <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="white" strokeWidth="2">
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.5" cy="6.5" r="0.5" fill="white" />
    </svg>
  ),
  youtube: (
    <svg viewBox="0 0 24 18" width="11" height="9" fill="white">
      <path d="M23.5 3.5a3 3 0 0 0-2.1-2.1C19.5 1 12 1 12 1s-7.5 0-9.4.4A3 3 0 0 0 .5 3.5C.1 5.4.1 9 .1 9s0 3.6.4 5.5a3 3 0 0 0 2.1 2.1C4.5 17 12 17 12 17s7.5 0 9.4-.4a3 3 0 0 0 2.1-2.1c.4-1.9.4-5.5.4-5.5s0-3.6-.4-5.5zM9.5 12.5v-7L15.5 9l-6 3.5z" />
    </svg>
  ),
  tiktok: (
    <svg viewBox="0 0 20 22" width="9" height="11" fill="white">
      <path d="M14.5 1c.4 1.8 1.5 3.4 3 4.4 1.1.7 2.5 1.1 3.9 1.1V11c-1.6 0-3.2-.4-4.6-1.1-.6-.3-1.2-.7-1.7-1.1v6.6c0 4.1-3.4 7.5-7.5 7.5-1.6 0-3.1-.5-4.3-1.4-1.9-1.4-3.2-3.7-3.2-6.2 0-4.1 3.4-7.5 7.5-7.5.4 0 .9 0 1.3.1v4.4c-.4-.1-.8-.2-1.3-.2-1.7 0-3.1 1.4-3.1 3.1s1.4 3.2 3.2 3.2 3.2-1.4 3.2-3.1V1h3.6z" />
    </svg>
  ),
  facebook: (
    <svg viewBox="0 0 24 24" width="10" height="10" fill="white">
      <path d="M14 9V7c0-1 .5-2 2-2h2V1h-3c-3 0-5 2-5 5v3H7v4h3v9h4v-9h3l1-4h-4z" />
    </svg>
  ),
};

const pName = { instagram: 'IG', youtube: 'YT', tiktok: 'TT', facebook: 'FB' };

const matchClass = (m: number) => (m >= 92 ? 'mm-high' : m >= 85 ? 'mm-mid' : 'mm-low');
const pfClass = (p: string) => (p === 'instagram' ? 'pf-ig' : p === 'youtube' ? 'pf-yt' : p === 'tiktok' ? 'pf-tt' : 'pf-fb');

export default function ListsPageClient({ setCrumbs }: { setCrumbs: (crumbs: Crumb[]) => void }) {
  const [view, setView] = useState<'index' | 'detail'>('index');
  const [selectedList, setSelectedList] = useState<SavedList | null>(null);
  const [lists, setLists] = useState(savedLists);
  const [rows, setRows] = useState(savedListRows);
  const { toast } = useToast();

  const handleOpenList = (list: SavedList) => {
    setSelectedList(list);
    setView('detail');
    setCrumbs([
      { label: 'Workspace', href: '/' },
      { label: 'Saved Lists', href: '/lists' },
      { label: list.name, current: true },
    ]);
    window.scrollTo({ top: 0 });
  };

  const handleGoIndex = () => {
    setView('index');
    setSelectedList(null);
    setCrumbs([
      { label: 'Workspace', href: '/' },
      { label: 'Saved Lists', current: true },
    ]);
    window.scrollTo({ top: 0 });
  };

  const handleDeleteList = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Delete this list?')) {
      setLists(lists.filter((l) => l.id !== id));
      toast('List deleted');
    }
  };

  const handleRemoveCreator = (name: string) => {
    setRows(rows.filter((r) => r.name !== name));
    toast('Creator removed from list');
  };

  const handleNewList = () => {
    toast('Create new list — opens the naming dialog.', { type: 'info' });
  };

  return (
    <>
      {/* ===== INDEX VIEW ===== */}
      <section id="v-index" className={`view ${view === 'index' ? 'active' : ''}`}>
        <div className="page-head">
          <div>
            <h1>
              Saved <span className="accent">lists.</span>
            </h1>
            <p className="sub">Curated collections of creators you&apos;ve handpicked from Discover. Hand them off to a campaign brief when you&apos;re ready.</p>
          </div>
          <button className="btn btn-primary btn-sm" type="button" onClick={handleNewList}>
            <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
              <path d="M12 5v14M5 12h14" />
            </svg>
            New list
          </button>
        </div>

        <div className="grid" id="lists-grid">
          {lists.map((L) => (
            <article key={L.id} className={`card ${L.glow}`} onClick={() => handleOpenList(L)}>
              <div className="card-head">
                <span className={`ribbon ${L.status === 'active' ? 'active' : 'draft'}`}>
                  <span className="d"></span>
                  {L.status === 'active' ? 'Active' : 'Draft'}
                </span>
                <button className="icon-btn-sm" aria-label="More" title="More">
                  <svg className="i" viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="6" cy="12" r="1.4" />
                    <circle cx="12" cy="12" r="1.4" />
                    <circle cx="18" cy="12" r="1.4" />
                  </svg>
                </button>
              </div>
              <h3>{L.name}</h3>
              <div className="meta">
                <span>
                  <strong style={{ color: 'var(--ink-soft)', fontWeight: 500 }}>{L.count}</strong> influencers
                </span>
                <span className="dot"></span>
                <span>Created {L.created}</span>
              </div>

              <div className="av-row">
                {L.avatars.map((a, i) => (
                  <span key={i} className="a" style={{ background: a.bg }}>
                    {a.i}
                  </span>
                ))}
                <span className="more">+ {L.count - L.avatars.length} more</span>
              </div>

              <div className="platform-mix">
                <span className="lbl">Mix</span>
                {L.mix.map((m, i) => (
                  <span key={i} className={`pglyph ${pfClass(m.p)}`} title={pName[m.p]}>
                    {platformGlyphSm[m.p as keyof typeof platformGlyphSm]}
                    <span className="n">{m.n}</span>
                  </span>
                ))}
              </div>

              <div className="stat-row">
                <div>
                  <div className="l">Total reach</div>
                  <div className="v">{L.reach}</div>
                </div>
                <div>
                  <div className="l">Avg engagement</div>
                  <div className="v good">{L.engagement}</div>
                </div>
              </div>

              <div className="card-cta">
                <button
                  className="btn-card btn-open open-btn"
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleOpenList(L);
                  }}
                >
                  Open List
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.7">
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </button>
                <button className="btn-card btn-del" aria-label="Delete list" title="Delete list" type="button" onClick={(e) => handleDeleteList(L.id, e)}>
                  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7">
                    <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                  </svg>
                </button>
              </div>
            </article>
          ))}
          <article className="card card-new" id="new-list" tabIndex={0} onClick={handleNewList}>
            <div className="plus">+</div>
            <div className="t">Create a new list</div>
            <div className="s">Save creators from Discover into a focused, sharable collection.</div>
          </article>
        </div>
      </section>

      {/* ===== DETAIL VIEW ===== */}
      {selectedList && (
        <section id="v-detail" className={`view ${view === 'detail' ? 'active' : ''}`}>
          <a className="back-link" id="back" onClick={handleGoIndex}>
            <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
              <path d="M15 18l-6-6 6-6" />
            </svg>
            Back to Saved Lists
          </a>
          <div className="det-head">
            <div className="det-title">
              <h1>
                <span className={`ribbon ${selectedList.status === 'active' ? 'active' : 'draft'}`}>
                  <span className="d"></span>
                  {selectedList.status === 'active' ? 'Active' : 'Draft'}
                </span>
                <span className="name-edit" id="det-name" contentEditable suppressContentEditableWarning spellCheck="false">
                  {selectedList.name}
                </span>
              </h1>
              <div className="meta">
                <span>
                  <strong>{selectedList.count}</strong> influencers
                </span>
                <span>
                  Created <strong>{selectedList.created}</strong>
                </span>
                <span>
                  Last updated <strong>2 days ago</strong>
                </span>
                <span>
                  Owner <strong>Elena Marchetti</strong>
                </span>
              </div>
            </div>
            <div className="det-actions">
              <button className="btn btn-ghost btn-sm" type="button">
                <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
                  <path d="M14 3v5h5" />
                  <path d="M9 14l3 3 3-3M12 17V11" />
                </svg>
                Export CSV
              </button>
              <Link className="btn btn-primary btn-sm" href="/briefs/new">
                <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
                  <path d="M14 3v5h5" />
                  <path d="M9 13h6M9 17h4" />
                </svg>
                Start campaign brief<span className="arrow">→</span>
              </Link>
            </div>
          </div>

          <div className="summary-row">
            <div>
              <div className="l">Total reach</div>
              <div className="v">
                {selectedList.reach.replace('M', '')}
                <span className="u">M</span>
              </div>
              <div className="delta">▲ 240K since saved</div>
            </div>
            <div>
              <div className="l">Avg engagement</div>
              <div className="v">
                {selectedList.engagement.replace('%', '')}
                <span className="u">%</span>
              </div>
              <div className="delta">▲ 0.4 vs. category</div>
            </div>
            <div>
              <div className="l">Avg match score</div>
              <div className="v">
                {selectedList.match}
                <span className="u">/100</span>
              </div>
              <div className="delta">▲ Top quartile</div>
            </div>
            <div>
              <div className="l">Est. budget</div>
              <div className="v">
                $28.4<span className="u">K</span>
              </div>
              <div className="delta" style={{ color: 'var(--muted)' }}>
                range: $19K – $42K
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <span className="ttl">Influencers in this list</span>
              <span className="mono" style={{ fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                {rows.length} entries
              </span>
              <div className="right">
                <button className="filter-mini" type="button">
                  <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" style={{ width: '12px', height: '12px' }}>
                    <path d="M3 5h18M6 12h12M10 19h4" />
                  </svg>
                  Filter
                </button>
                <button className="filter-mini" type="button">
                  <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" style={{ width: '12px', height: '12px' }}>
                    <path d="M3 6h18M3 12h18M3 18h18" />
                  </svg>
                  Sort: Match score
                </button>
              </div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Platform</th>
                    <th>Category</th>
                    <th>Followers</th>
                    <th>Engagement</th>
                    <th>Est. rate</th>
                    <th>Match</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody id="det-rows">
                  {rows.map((r, i) => (
                    <tr key={i}>
                      <td>
                        <div className="name-cell">
                          <div className="av-tiny" style={{ background: r.avBg }}>
                            {r.avI}
                            <span className={`p ${pfClass(r.plat)}`} style={{ border: '1.5px solid #fff' }}>
                              {platformGlyphSm[r.plat as keyof typeof platformGlyphSm]}
                            </span>
                          </div>
                          <div className="nm">
                            <span className="n1">{r.name}</span>
                            <span className="h">{r.handle}</span>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="platform-cell">
                          <span className={`g ${pfClass(r.plat)}`}>{platformGlyphSm[r.plat as keyof typeof platformGlyphSm]}</span>
                          <span style={{ textTransform: 'capitalize' }}>{r.plat}</span>
                        </span>
                      </td>
                      <td>
                        <span style={{ color: 'var(--ink-soft)' }}>{r.cat}</span>
                      </td>
                      <td className="num">{r.fol}</td>
                      <td>
                        <span className="eng num">{r.eng}</span>
                      </td>
                      <td className="num">{r.rate}</td>
                      <td>
                        <span className={`match-mini ${matchClass(r.match)}`}>{r.match}%</span>
                      </td>
                      <td>
                        <div className="act-row" style={{ justifyContent: 'flex-end' }}>
                          <Link className="iconlink" href="/profile/lila-park" title="View profile">
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.7">
                              <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" />
                              <circle cx="12" cy="12" r="3" />
                            </svg>
                          </Link>
                          <button className="iconlink" title="Contact" type="button">
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.7">
                              <path d="M4 4h16v16H4z" />
                              <path d="M4 4l8 8 8-8" />
                            </svg>
                          </button>
                          <button className="iconlink danger remove" title="Remove from list" type="button" onClick={() => handleRemoveCreator(r.name)}>
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.7">
                              <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </>
  );
}
