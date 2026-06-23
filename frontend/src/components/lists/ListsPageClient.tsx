'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  addListItems,
  createSavedList,
  deleteSavedList,
  getSavedList,
  listSavedLists,
  removeListItem,
  updateSavedList,
  type SavedListItem as ApiSavedListItem,
  type SavedListSummary,
} from '@/lib/api';
import { useToast } from '@/components/ui/ToastProvider';
import { Crumb } from '@/components/shell/Topbar';

export type ListMembershipPayload = {
  list_id: string;
  influencer_id: string;
  source_campaign_id?: string | null;
  match_score_snapshot?: number | null;
};

/**
 * Add one or more creators to a list and return a result the UI can toast.
 * Exported at module scope so the Discover table and SaveToListPopover can
 * call into the same mutation flow without duplicating the request shape.
 */
export async function addSelectedToList(
  listId: string,
  items: Array<{
    influencer_id: string;
    source_campaign_id?: string | null;
    match_score_snapshot?: number | null;
  }>
): Promise<{ added: number; skipped: number }> {
  const result = await addListItems(listId, items);
  return { added: result.added.length, skipped: result.skipped.length };
}

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

const pName: Record<string, string> = {
  instagram: 'IG',
  youtube: 'YT',
  tiktok: 'TT',
  facebook: 'FB',
};

const matchClass = (m: number) => (m >= 92 ? 'mm-high' : m >= 85 ? 'mm-mid' : 'mm-low');
const pfClass = (p: string) =>
  p === 'instagram'
    ? 'pf-ig'
    : p === 'youtube'
      ? 'pf-yt'
      : p === 'tiktok'
        ? 'pf-tt'
        : 'pf-fb';

const formatReach = (count: number): string => {
  if (count >= 1_000_000) {
    return `${(count / 1_000_000).toFixed(2)}M`;
  }
  if (count >= 1_000) {
    return `${(count / 1_000).toFixed(0)}K`;
  }
  return count.toString();
};

const formatEngagement = (rate: number | null): string => {
  if (rate == null) return '—';
  return `${rate.toFixed(1)}%`;
};

const formatDate = (iso: string | null): string => {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

const avatarFor = (name: string): string =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('') || 'IQ';

const gradientFor = (platform: string | null): string => {
  if (platform === 'youtube') return 'linear-gradient(135deg,#ef4444,#f97316)';
  if (platform === 'tiktok') return 'linear-gradient(135deg,#111827,#06b6d4)';
  if (platform === 'facebook') return 'linear-gradient(135deg,#2563eb,#60a5fa)';
  return 'linear-gradient(135deg,#6a4cff,#c054ff)';
};

type ListItemView = {
  itemId: string;
  influencerId: string;
  name: string;
  handle: string;
  platform: 'instagram' | 'youtube' | 'tiktok' | 'facebook';
  avI: string;
  avBg: string;
  cat: string;
  fol: string;
  eng: string;
  rate: string;
  match: number;
};

const mapListItem = (item: ApiSavedListItem): ListItemView => {
  const platform = (item.influencer?.primary_platform || 'instagram') as ListItemView['platform'];
  const name = item.influencer?.canonical_name || 'Unknown creator';
  const handle = item.influencer?.primary_handle || '@unknown';
  const followers = item.influencer?.follower_count;
  const engagement = item.influencer?.engagement_rate;
  return {
    itemId: item.id,
    influencerId: item.influencer_id,
    name,
    handle,
    platform,
    avI: avatarFor(name),
    avBg: gradientFor(platform),
    cat: item.influencer?.primary_category || 'General',
    fol: followers != null ? formatReach(followers) : '—',
    eng: formatEngagement(engagement ?? null),
    rate: '—',
    match: item.match_score_snapshot ?? 0,
  };
};

type ListView = {
  id: string;
  name: string;
  status: 'active' | 'draft';
  item_count: number;
  created: string;
  reach: string;
  engagement: string;
  match: string;
  glow: string;
  avatars: Array<{ i: string; bg: string }>;
  mix: Array<{ p: 'instagram' | 'youtube' | 'tiktok' | 'facebook'; n: number }>;
};

const GLOW_BY_INDEX = ['glow-v', 'glow-cy', 'glow-c'];

const toListView = (
  list: SavedListSummary,
  index: number
): ListView => {
  const reach = formatReach(list.total_followers);
  const mix = list.platform_mix
    .map((entry) => {
      if (
        entry.platform === 'instagram' ||
        entry.platform === 'youtube' ||
        entry.platform === 'tiktok' ||
        entry.platform === 'facebook'
      ) {
        return { p: entry.platform, n: entry.count };
      }
      return null;
    })
    .filter((entry): entry is { p: 'instagram' | 'youtube' | 'tiktok' | 'facebook'; n: number } =>
      entry != null
    );
  return {
    id: list.id,
    name: list.name,
    status: list.status,
    item_count: list.item_count,
    created: formatDate(list.created_at),
    reach: reach.endsWith('K') || reach.endsWith('M') ? reach : `${reach}`,
    engagement: formatEngagement(list.avg_engagement),
    match: list.avg_match_score != null ? list.avg_match_score.toFixed(1) : '—',
    glow: GLOW_BY_INDEX[index % GLOW_BY_INDEX.length],
    avatars: [],
    mix,
  };
};

export default function ListsPageClient({ setCrumbs }: { setCrumbs: (crumbs: Crumb[]) => void }) {
  const [view, setView] = useState<'index' | 'detail'>('index');
  const [lists, setLists] = useState<ListView[]>([]);
  const [selectedList, setSelectedList] = useState<ListView | null>(null);
  const [listItems, setListItems] = useState<ListItemView[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const refreshLists = async () => {
    const summaries = await listSavedLists();
    return summaries.map((summary, index) => toListView(summary, index));
  };

  useEffect(() => {
    let active = true;
    setLoading(true);
    refreshLists()
      .then((rows) => {
        if (active) {
          setLists(rows);
        }
      })
      .catch((error) => {
        if (active) {
          toast(
            error instanceof Error ? error.message : 'Unable to load saved lists.',
            { type: 'error' }
          );
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [toast]);

  const handleOpenList = async (list: ListView) => {
    setSelectedList(list);
    setView('detail');
    setCrumbs([
      { label: 'Workspace', href: '/' },
      { label: 'Saved Lists', href: '/lists' },
      { label: list.name, current: true },
    ]);
    window.scrollTo({ top: 0 });
    try {
      const detail = await getSavedList(list.id);
      setListItems(detail.items.map(mapListItem));
    } catch (error) {
      toast(
        error instanceof Error ? error.message : 'Unable to load list details.',
        { type: 'error' }
      );
    }
  };

  const handleDeleteList = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this list?')) return;
    try {
      await deleteSavedList(id);
      setLists((current) => current.filter((l) => l.id !== id));
      if (selectedList?.id === id) {
        handleGoIndex();
      }
      toast('List deleted');
    } catch (error) {
      toast(
        error instanceof Error ? error.message : 'Unable to delete list.',
        { type: 'error' }
      );
    }
  };

  const handleRemoveCreator = async (itemId: string) => {
    if (!selectedList) return;
    try {
      await removeListItem(selectedList.id, itemId);
      setListItems((current) => current.filter((row) => row.itemId !== itemId));
      toast('Creator removed from list');
    } catch (error) {
      toast(
        error instanceof Error ? error.message : 'Unable to remove creator.',
        { type: 'error' }
      );
    }
  };

  const handleNewList = async () => {
    const name = window.prompt('Name for the new list?');
    if (!name) return;
    try {
      const created = await createSavedList({ name });
      const next = toListView(created, lists.length);
      setLists((current) => [next, ...current]);
      toast('List created', { type: 'success' });
    } catch (error) {
      toast(
        error instanceof Error ? error.message : 'Unable to create list.',
        { type: 'error' }
      );
    }
  };

  const handleRenameList = async (newName: string) => {
    if (!selectedList) return;
    try {
      const updated = await updateSavedList(selectedList.id, { name: newName });
      const next = toListView(updated, lists.findIndex((l) => l.id === updated.id));
      setSelectedList(next);
      setLists((current) => current.map((l) => (l.id === next.id ? next : l)));
    } catch (error) {
      toast(
        error instanceof Error ? error.message : 'Unable to rename list.',
        { type: 'error' }
      );
    }
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
          {loading ? (
            <div className="card" aria-hidden="true" style={{ opacity: 0.5 }}>
              <div className="t">Loading your lists…</div>
            </div>
          ) : lists.length === 0 ? (
            <article className="card card-new" id="new-list" tabIndex={0} onClick={handleNewList}>
              <div className="plus">+</div>
              <div className="t">Create your first list</div>
              <div className="s">Save creators from Discover into a focused, sharable collection.</div>
            </article>
          ) : (
            <>
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
                      <strong style={{ color: 'var(--ink-soft)', fontWeight: 500 }}>{L.item_count}</strong> influencers
                    </span>
                    <span className="dot"></span>
                    <span>Created {L.created}</span>
                  </div>

                  {L.avatars.length ? (
                    <div className="av-row">
                      {L.avatars.map((a, i) => (
                        <span key={i} className="a" style={{ background: a.bg }}>
                          {a.i}
                        </span>
                      ))}
                      <span className="more">+ {L.item_count - L.avatars.length} more</span>
                    </div>
                  ) : null}

                  <div className="platform-mix">
                    <span className="lbl">Mix</span>
                    {L.mix.map((m, i) => (
                      <span key={i} className={`pglyph ${pfClass(m.p)}`} title={pName[m.p]}>
                        {platformGlyphSm[m.p]}
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
            </>
          )}
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
                <span
                  className="name-edit"
                  id="det-name"
                  contentEditable
                  suppressContentEditableWarning
                  spellCheck="false"
                  onBlur={(event) => {
                    const next = event.currentTarget.textContent?.trim();
                    if (next && next !== selectedList.name) {
                      void handleRenameList(next);
                    }
                  }}
                >
                  {selectedList.name}
                </span>
              </h1>
              <div className="meta">
                <span>
                  <strong>{listItems.length}</strong> influencers
                </span>
                <span>
                  Created <strong>{selectedList.created}</strong>
                </span>
                <span>
                  Last updated <strong>{formatDate(selectedList.created)}</strong>
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
                {selectedList.reach.replace('M', '').replace('K', '')}
                <span className="u">
                  {selectedList.reach.endsWith('M') ? 'M' : selectedList.reach.endsWith('K') ? 'K' : ''}
                </span>
              </div>
              <div className="delta">▲ Updated {formatDate(selectedList.created)}</div>
            </div>
            <div>
              <div className="l">Avg engagement</div>
              <div className="v">
                {selectedList.engagement.replace('%', '')}
                <span className="u">%</span>
              </div>
              <div className="delta">across {listItems.length} creators</div>
            </div>
            <div>
              <div className="l">Avg match score</div>
              <div className="v">
                {selectedList.match}
                <span className="u">/100</span>
              </div>
              <div className="delta">▲ recorded at save time</div>
            </div>
            <div>
              <div className="l">Influencers</div>
              <div className="v">
                {listItems.length}
                <span className="u">saved</span>
              </div>
              <div className="delta" style={{ color: 'var(--muted)' }}>
                Created {formatDate(selectedList.created)}
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <span className="ttl">Influencers in this list</span>
              <span className="mono" style={{ fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                {listItems.length} entries
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
                  {listItems.length === 0 ? (
                    <tr className="empty-row">
                      <td colSpan={8}>
                        No creators in this list yet. Save some from Discover to see them here.
                      </td>
                    </tr>
                  ) : (
                    listItems.map((r) => (
                      <tr key={r.itemId}>
                        <td>
                          <div className="name-cell">
                            <div className="av-tiny" style={{ background: r.avBg }}>
                              {r.avI}
                              <span className={`p ${pfClass(r.platform)}`} style={{ border: '1.5px solid #fff' }}>
                                {platformGlyphSm[r.platform]}
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
                            <span className={`g ${pfClass(r.platform)}`}>{platformGlyphSm[r.platform]}</span>
                            <span style={{ textTransform: 'capitalize' }}>{r.platform}</span>
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
                            <button className="iconlink danger remove" title="Remove from list" type="button" onClick={() => handleRemoveCreator(r.itemId)}>
                              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.7">
                                <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                              </svg>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </>
  );
}
