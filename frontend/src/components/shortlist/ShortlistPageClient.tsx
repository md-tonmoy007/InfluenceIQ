'use client';

import { useEffect, useMemo, useRef, useState, useCallback, type ReactNode } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { parseBriefSearchParams } from '@/lib/briefQuery';
import { parseBriefSnapshot } from '@/lib/campaignPayload';
import {
  addCampaignContract,
  getCampaign,
  getCampaignInfluencers,
  getCampaignState,
  listCampaignContracts,
  type CampaignState,
  type CampaignSummary,
  type InfluencerListResult,
} from '@/lib/api';
import { getCampaignWebSocketUrl } from '@/lib/websocket';
import type { CampaignPipelineEvent } from '@/types/events';
import { isTerminalPipelineEvent } from '@/types/events';
import { useToast } from '@/components/ui/ToastProvider';
import DeepAnalysisTrigger from '@/components/profile/DeepAnalysisTrigger';
import CampaignBriefActions from '@/components/campaigns/CampaignBriefActions';
import { canRerunCampaign } from '@/lib/campaignLifecycle';
import { performQuickRerunWithConfirm } from '@/lib/rerunActions';

const platformGlyphs: Record<string, ReactNode> = {
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
} as const;

type MatchRow = {
  id: string;
  rank: number;
  name: string;
  handle: string;
  platform: 'instagram' | 'youtube' | 'tiktok' | 'facebook';
  avatar: string;
  avBg: string;
  match: number;
  followers: string;
  engagement: string;
  avgViews: string;
  rate: string;
  tier: keyof typeof tierClass;
  tags: string[];
  verified: boolean;
  reason: string;
};

const gradientByPlatform: Record<MatchRow['platform'], string> = {
  instagram: 'linear-gradient(135deg,#6a4cff,#c054ff)',
  youtube: 'linear-gradient(135deg,#ef4444,#f97316)',
  tiktok: 'linear-gradient(135deg,#111827,#06b6d4)',
  facebook: 'linear-gradient(135deg,#2563eb,#60a5fa)',
};

const normalizePlatform = (value: string): MatchRow['platform'] => {
  const lowered = value.toLowerCase();
  if (lowered === 'youtube' || lowered === 'tiktok' || lowered === 'facebook') {
    return lowered;
  }
  return 'instagram';
};

const formatCompactNumber = (value: number) =>
  new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(value);

const formatPercent = (value: number) => `${value.toFixed(1)}%`;

const toTier = (followers: number): MatchRow['tier'] => {
  if (followers >= 500_000) return 'Premium';
  if (followers >= 50_000) return 'Established';
  return 'Rising';
};

const titleize = (value: string) =>
  value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase());

const hostLabel = (rawUrl: string) => {
  try {
    return new URL(rawUrl).hostname.replace(/^www\./, '');
  } catch {
    return rawUrl;
  }
};

const formatHandle = (handle: string): string => {
  const trimmed = handle.trim();
  if (!trimmed) return '@unknown';
  if (/^https?:\/\//i.test(trimmed)) {
    try {
      const url = new URL(trimmed);
      const segment = url.pathname.replace(/^\/+/, '').split('/')[0];
      if (segment) return `@${segment}`;
      return url.hostname.replace(/^www\./, '');
    } catch {
      return trimmed;
    }
  }
  return trimmed.startsWith('@') ? trimmed : `@${trimmed}`;
};

const hasMetricValue = (value: string) => value.trim() !== '' && value.trim() !== '—';

const avatarFromName = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0]?.toUpperCase() ?? '')
    .join('') || 'IQ';

const estimateViews = (followers: number, engagementRate: number) =>
  Math.max(0, Math.round(followers * Math.max(engagementRate, 1) * 0.04));

const reasonForInfluencer = (
  trustGrade: string,
  platform: string,
  tags: string[],
  citations: string[],
  matchScore: number
) => {
  if (tags.length) {
    return `<em>${titleize(tags[0])}</em> fit with corroboration from ${Math.max(citations.length, 1)} source${citations.length === 1 ? '' : 's'}.`;
  }
  if (trustGrade === 'A+' || trustGrade === 'A') {
    return `<em>High-confidence match</em> on ${titleize(platform)} with a ${Math.round(matchScore)}% campaign score.`;
  }
  return `<em>Promising shortlist candidate</em> on ${titleize(platform)} with room to validate during outreach.`;
};

const tagsForInfluencer = (
  platform: string,
  brandSafetyFlags: string[],
  citations: string[],
  subScores: Record<string, number>
) => {
  const tags: string[] = [];
  tags.push(titleize(platform));
  Object.entries(subScores)
    .filter(([key, value]) => key !== 'data_source_count' && value >= 75)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .forEach(([key]) => tags.push(titleize(key)));
  if (!brandSafetyFlags.length) {
    tags.push('Brand safe');
  }
  citations.slice(0, 2).forEach(citation => tags.push(hostLabel(citation)));
  return Array.from(new Set(tags)).slice(0, 4);
};

const toMatchRows = (influencers: InfluencerListResult['items']): MatchRow[] =>
  influencers.map((item, index) => {
    const platform = normalizePlatform(item.platform);
    const tags = tagsForInfluencer(
      item.platform,
      item.brandSafetyFlags,
      item.citations,
      item.subScores
    );

    return {
      id: item.id,
      rank: index + 1,
      name: item.name,
      handle: formatHandle(item.handle),
      platform,
      avatar: avatarFromName(item.name),
      avBg: gradientByPlatform[platform],
      match: Math.round(item.matchScore),
      followers: item.followers > 0 ? formatCompactNumber(item.followers) : '—',
      engagement: item.engagementRate > 0 ? formatPercent(item.engagementRate) : '—',
      avgViews:
        item.followers > 0
          ? formatCompactNumber(estimateViews(item.followers, item.engagementRate))
          : '—',
      rate: item.rate || '—',
      tier: toTier(item.followers),
      tags,
      verified: item.trustGrade === 'A+' || item.trustGrade === 'A',
      reason: reasonForInfluencer(
        item.trustGrade,
        item.platform,
        tags,
        item.citations,
        item.matchScore
      ),
    };
  });

const eventLabel = (event: CampaignPipelineEvent) => {
  switch (event.type) {
    case 'campaign.started':
      return 'Campaign started';
    case 'campaign.completed':
      return 'Campaign completed';
    case 'campaign.partial':
      return 'Partial campaign results ready';
    case 'campaign.failed':
      return `Campaign failed: ${String(event.payload.reason ?? event.payload.error ?? 'unknown error')}`;
    case 'campaign.cancelled':
      return 'Campaign cancelled';
    case 'query.generation.completed':
      return `Generated ${String(event.payload.query_count ?? 0)} search queries`;
    case 'page.fetched':
      return `Fetched ${String(event.payload.url ?? 'page')}`;
    case 'platform.enriched':
      return 'Platform data enriched';
    case 'deep_analysis.started':
      return 'Deep analysis started';
    case 'deep_analysis.social_collected':
      return 'Social content collected';
    case 'deep_analysis.comments_collected':
      return 'Comments collected';
    case 'deep_analysis.external_signals_collected':
      return 'Trend signals gathered';
    case 'deep_analysis.report_ready':
      return 'Deep analysis report ready';
    case 'deep_analysis.failed':
      return 'Deep analysis failed';
    case 'score.calculated':
      return `Scored influencer ${String(event.payload.influencer_id ?? '')}`;
    case 'pipeline.completed':
      return 'Pipeline completed';
    case 'pipeline.failed':
      return `Pipeline failed: ${String(event.payload.error ?? 'unknown error')}`;
    case 'heartbeat':
      return 'Connection heartbeat';
    default:
      return titleize(event.type);
  }
};

type ListEmptyStat = { label: string; value: string };

function ListEmptyState({
  title,
  description,
  stats,
  progressPct,
  progressLabel,
  loading = false,
  action,
}: {
  title: string;
  description: string;
  stats?: ListEmptyStat[];
  progressPct?: number | null;
  progressLabel?: string;
  loading?: boolean;
  action?: ReactNode;
}) {
  return (
    <article className="list-empty">
      <div className={`list-empty-icon ${loading ? 'loading' : ''}`} aria-hidden="true">
        {loading ? null : (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round" />
          </svg>
        )}
      </div>
      <div className="list-empty-body">
        <h3>{title}</h3>
        <p>{description}</p>
        {stats?.length ? (
          <div className="list-empty-stats">
            {stats.map(stat => (
              <div key={stat.label} className="list-empty-stat">
                <span className="k">{stat.label}</span>
                <span className="v">{stat.value}</span>
              </div>
            ))}
          </div>
        ) : null}
        {progressPct != null ? (
          <div className="list-empty-progress">
            <div className="bar">
              <div className="fill" style={{ width: `${Math.min(100, Math.max(0, progressPct))}%` }} />
            </div>
            {progressLabel ? <div className="hint">{progressLabel}</div> : null}
          </div>
        ) : null}
        {action ? <div className="list-empty-action">{action}</div> : null}
      </div>
    </article>
  );
}

export default function ShortlistPageClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { toast } = useToast();
  const fallbackBrief = useMemo(
    () => parseBriefSearchParams(Object.fromEntries(searchParams.entries())),
    [searchParams]
  );
  const campaignId = searchParams.get('campaignId') || searchParams.get('campaign_id') || '';
  const missingCampaignId = !campaignId;

  const [campaign, setCampaign] = useState<CampaignSummary | null>(null);
  const [pipelineState, setPipelineState] = useState<CampaignState | null>(null);
  const [influencerResult, setInfluencerResult] = useState<InfluencerListResult | null>(null);
  const [events, setEvents] = useState<CampaignPipelineEvent[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [contractedIds, setContractedIds] = useState<Set<string>>(new Set());
  const [markingContractId, setMarkingContractId] = useState<string | null>(null);
  const [showPdf, setShowPdf] = useState(false);
  const [loadingCampaign, setLoadingCampaign] = useState(!missingCampaignId);
  const [loadingInfluencers, setLoadingInfluencers] = useState(false);
  const [errorMessage, setErrorMessage] = useState(missingCampaignId ? 'No campaignId found in the URL. Submit a brief first to start the live pipeline.' : '');
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'connected' | 'polling'>(missingCampaignId ? 'idle' : 'polling');
  const [bannerRerunning, setBannerRerunning] = useState(false);
  const lastEventIdRef = useRef(0);

  const clearRerunState = useCallback(() => {
    setInfluencerResult(null);
    setPipelineState(null);
    setEvents([]);
    setSelectedIds([]);
    setErrorMessage('');
    lastEventIdRef.current = 0;
  }, []);

  const liveBrief = useMemo(() => {
    if (campaignId && loadingCampaign) {
      return {
        brand: '…',
        description: '…',
        locs: [] as string[],
        platforms: [] as string[],
        tier: '…',
        budget: '…',
      };
    }

    if (campaign) {
      const parsed = parseBriefSnapshot(campaign.briefSnapshot, {
        searchQuery: campaign.searchQuery,
        product: campaign.product,
        budget_range: campaign.budgetRange,
        preferred_platforms: campaign.preferredPlatforms,
      });
      return {
        brand: parsed.brand,
        description: parsed.description,
        locs: parsed.locs,
        platforms: parsed.platforms,
        tier: parsed.tier,
        budget: parsed.budget,
      };
    }

    return {
      brand: fallbackBrief.brand,
      description: fallbackBrief.description,
      locs: fallbackBrief.locs,
      platforms: fallbackBrief.platforms,
      tier: fallbackBrief.tier,
      budget: fallbackBrief.budget,
    };
  }, [campaign, campaignId, fallbackBrief, loadingCampaign]);

  const matches = useMemo(
    () => toMatchRows(influencerResult?.items ?? []),
    [influencerResult]
  );

  useEffect(() => {
    if (showPdf) {
      document.body.style.overflow = 'hidden';
      const handleEsc = (e: KeyboardEvent) => {
        if (e.key === 'Escape') setShowPdf(false);
      };
      window.addEventListener('keydown', handleEsc);
      return () => window.removeEventListener('keydown', handleEsc);
    }

    document.body.style.overflow = '';
  }, [showPdf]);

  useEffect(() => {
    if (missingCampaignId) {
      return;
    }

    let cancelled = false;

    const loadCampaign = async () => {
      try {
        setLoadingCampaign(true);
        const [campaignData, stateData] = await Promise.all([
          getCampaign(campaignId),
          getCampaignState(campaignId),
        ]);
        if (cancelled) {
          return;
        }
        setCampaign(campaignData);
        setPipelineState(stateData);
        setErrorMessage('');
      } catch (error) {
        if (cancelled) {
          return;
        }
        setErrorMessage(error instanceof Error ? error.message : 'Unable to load campaign');
      } finally {
        if (!cancelled) {
          setLoadingCampaign(false);
        }
      }
    };

    void loadCampaign();
    return () => {
      cancelled = true;
    };
  }, [campaignId, missingCampaignId]);

  useEffect(() => {
    if (!campaignId) return;
    let cancelled = false;
    listCampaignContracts(campaignId)
      .then((result) => {
        if (cancelled) return;
        setContractedIds(
          new Set(
            result.items
              .filter((item) => item.status === 'contracted')
              .map((item) => item.influencer_id)
          )
        );
      })
      .catch(() => {
        // Non-fatal; contract badges stay empty.
      });
    return () => {
      cancelled = true;
    };
  }, [campaignId]);

  const handleMarkContracted = async (influencerId: string) => {
    if (!campaignId || markingContractId) return;
    setMarkingContractId(influencerId);
    try {
      await addCampaignContract(campaignId, influencerId);
      setContractedIds((current) => new Set([...current, influencerId]));
      toast('Creator marked as contracted.', { type: 'success' });
    } catch (error) {
      toast(
        error instanceof Error ? error.message : 'Unable to mark creator as contracted.',
        { type: 'error' }
      );
    } finally {
      setMarkingContractId(null);
    }
  };

  useEffect(() => {
    const state = pipelineState;
    if (!campaignId || !state) {
      return;
    }

    if (
      state.status !== 'completed' &&
      state.status !== 'partial' &&
      state.status !== 'failed' &&
      state.status !== 'cancelled' &&
      !state.partial_results_available &&
      (state.scores_computed ?? 0) <= 0
    ) {
      return;
    }

    let cancelled = false;
    const loadInfluencers = async () => {
      try {
        setLoadingInfluencers(true);
        const response = await getCampaignInfluencers(campaignId);
        if (cancelled) {
          return;
        }
        setInfluencerResult(response);
        setSelectedIds(current =>
          current.length ? current.filter(id => response.items.some(item => item.id === id)) : response.items.slice(0, 2).map(item => item.id)
        );
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(error instanceof Error ? error.message : 'Unable to load influencer shortlist');
        }
      } finally {
        if (!cancelled) {
          setLoadingInfluencers(false);
        }
      }
    };

    void loadInfluencers();
    return () => {
      cancelled = true;
    };
  }, [campaignId, pipelineState]);

  const wsConnectedRef = useRef(false);

  useEffect(() => {
    if (!campaignId) {
      return;
    }

    const isTerminal =
      pipelineState?.status === 'completed' ||
      pipelineState?.status === 'partial' ||
      pipelineState?.status === 'failed' ||
      pipelineState?.status === 'cancelled';
    if (isTerminal) {
      return;
    }

    const interval = window.setInterval(async () => {
      if (wsConnectedRef.current) return;
      try {
        const nextState = await getCampaignState(campaignId);
        setPipelineState(nextState);
        setErrorMessage('');
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : 'Campaign polling failed');
      }
    }, 2500);

    return () => window.clearInterval(interval);
  }, [campaignId, pipelineState?.status]);

  useEffect(() => {
    if (!campaignId) {
      return;
    }

    let socket: WebSocket | null = null;
    let cancelled = false;
    let reconnectTimer: number | null = null;

    const openSocket = () => {
      try {
        socket = new WebSocket(
          getCampaignWebSocketUrl(campaignId, { lastEventId: lastEventIdRef.current })
        );
      } catch (error) {
        wsConnectedRef.current = false;
        setConnectionStatus('polling');
        setErrorMessage(error instanceof Error ? error.message : 'Unable to open live updates');
        return;
      }

      socket.onopen = () => {
        wsConnectedRef.current = true;
        setConnectionStatus('connected');
      };

      socket.onmessage = async message => {
        try {
          const event = JSON.parse(message.data) as CampaignPipelineEvent;
          if (event.type === 'heartbeat') {
            const heartbeatState = event.payload.state;
            if (heartbeatState && typeof heartbeatState === 'object') {
              setPipelineState(current => ({ ...(current ?? {}), ...(heartbeatState as CampaignState) }));
            }
            return;
          }

          setEvents(current => {
            const next = [...current, event];
            return next.slice(-12);
          });
          if (event.event_id > 0) {
            lastEventIdRef.current = Math.max(lastEventIdRef.current, event.event_id);
          }
          if (isTerminalPipelineEvent(event)) {
            const nextState = await getCampaignState(campaignId);
            setPipelineState(nextState);
          }
        } catch {
          wsConnectedRef.current = false;
          setConnectionStatus('polling');
        }
      };

      socket.onclose = () => {
        wsConnectedRef.current = false;
        setConnectionStatus('polling');
        if (!cancelled && pipelineState?.status !== 'completed' && pipelineState?.status !== 'failed') {
          reconnectTimer = window.setTimeout(openSocket, 1500);
        }
      };

      socket.onerror = () => {
        wsConnectedRef.current = false;
        setConnectionStatus('polling');
      };
    };

    openSocket();

    return () => {
      cancelled = true;
      wsConnectedRef.current = false;
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      socket?.close();
    };
  }, [campaignId]);

  const toggleSelection = (id: string) => {
    setSelectedIds(current =>
      current.includes(id) ? current.filter(existingId => existingId !== id) : [...current, id]
    );
  };

  const handleExport = () => {
    if (selectedIds.length === 0) {
      toast('Select at least one creator to export.', { type: 'info' });
      return;
    }
    setShowPdf(true);
    toast('Shortlist exported, opening preview.', { type: 'success' });
  };

  const handleCompare = () => {
    if (selectedIds.length < 2) {
      toast('Select at least 2 creators to compare.', { type: 'info' });
      return;
    }
    toast(`Opening compare view for ${selectedIds.length} creators.`, { type: 'info' });
  };

  const chosenMatches = matches.filter(match => selectedIds.includes(match.id));
  const today = new Date().toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
  const stateStatus = pipelineState?.status ?? campaign?.status ?? 'loading';
  const statePhase = String(pipelineState?.phase ?? 'queued');
  const urlsScraped = pipelineState?.urls_scraped ?? 0;
  const urlsDiscovered = pipelineState?.urls_discovered ?? 0;
  const scoresComputed = pipelineState?.scores_computed ?? 0;
  const urlProgressPct =
    urlsDiscovered > 0 ? Math.round((urlsScraped / urlsDiscovered) * 100) : null;
  const pipelineStats: ListEmptyStat[] = [
    { label: 'Status', value: titleize(stateStatus) },
    { label: 'Phase', value: titleize(statePhase) },
    { label: 'URLs scraped', value: `${urlsScraped}/${urlsDiscovered}` },
    { label: 'Scores', value: String(scoresComputed) },
  ];
  const failureMessage =
    campaign?.error ??
    (typeof pipelineState?.error === 'string' ? pipelineState.error : null) ??
    null;

  const handleBannerRerun = async () => {
    if (bannerRerunning || !campaignId) return;
    setBannerRerunning(true);
    try {
      await performQuickRerunWithConfirm({
        campaignId,
        router,
        toast,
        onStart: clearRerunState,
      });
    } catch (error) {
      toast(
        error instanceof Error ? error.message : 'Unable to rerun campaign.',
        { type: 'error' }
      );
    } finally {
      setBannerRerunning(false);
    }
  };

  const emptyListState = (() => {
    if (loadingInfluencers) {
      return {
        title: 'Loading shortlist',
        description: 'Pulling ranked creators as the pipeline surfaces matches.',
        loading: true,
        showProgress: true,
      };
    }
    if (stateStatus === 'failed') {
      return {
        title: 'Matching failed',
        description:
          failureMessage ??
          'The pipeline stopped before producing results. Try rerunning the search or editing your brief.',
        loading: false,
        showProgress: false,
      };
    }
    if (stateStatus === 'cancelled') {
      return {
        title: 'Campaign cancelled',
        description: 'This search was cancelled. Rerun it to discover creators again.',
        loading: false,
        showProgress: false,
      };
    }
    if (stateStatus === 'completed' && matches.length === 0) {
      return {
        title: 'No creators matched',
        description:
          'The pipeline finished but no creators met your brief criteria. Try editing platforms, tier, or budget and rerun.',
        loading: false,
        showProgress: false,
      };
    }
    if (stateStatus === 'partial' && matches.length === 0) {
      return {
        title: 'Partial results only',
        description:
          failureMessage ??
          'Some pipeline steps failed before matches could be ranked. Rerun to try again.',
        loading: false,
        showProgress: false,
      };
    }
    return {
      title: 'Campaign is still processing',
      description:
        'InfluenceIQ is discovering creators, scraping profiles, and scoring fit against your brief. Matches will appear here automatically.',
      loading: stateStatus === 'running',
      showProgress: true,
    };
  })();

  const rerunAction =
    canRerunCampaign(stateStatus) ? (
      <button
        type="button"
        className="btn btn-primary btn-sm"
        disabled={bannerRerunning}
        onClick={() => void handleBannerRerun()}
      >
        {bannerRerunning ? 'Rerunning…' : 'Rerun search'}
      </button>
    ) : null;

  if (!campaignId) {
    return (
      <div className="shortlist-page">
        <div className="page-head">
          <div>
            <h1>Live shortlist unavailable</h1>
            <p className="page-sub">{errorMessage}</p>
          </div>
          <Link className="btn btn-primary" href="/briefs/new">
            Submit a brief
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="shortlist-page">
      <div className="page-head">
        <div>
          <h1>Top matches for <span className="accent">{liveBrief.brand}&apos;s</span> campaign</h1>
          <p className="page-sub">
            <span className="pill">{liveBrief.description}</span>
            <span className="pill">{liveBrief.platforms.join(' + ')}</span>
            <span className="pill">{liveBrief.tier}</span>
            <span className="pill">{liveBrief.budget}</span>
          </p>
        </div>
        <span className="toast">
          <span className="dot"></span>
          {connectionStatus === 'connected' ? 'Live updates connected' : 'Polling fallback active'} · {titleize(stateStatus)} / {titleize(statePhase)}
        </span>
      </div>

      <div className="top-actions">
        <div className="left">
          <span className="selection-pill"><span className="n">{selectedIds.length}</span> selected</span>
          <span style={{ fontSize: '12.5px', color: 'var(--muted)' }}>
            Campaign {campaignId.slice(0, 8)} · {pipelineState?.influencer_count ?? influencerResult?.total ?? 0} creators surfaced
          </span>
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

      {errorMessage ? (
        <div style={{ marginBottom: '18px', padding: '14px 16px', borderRadius: '16px', background: 'rgba(255,110,80,0.12)', color: 'var(--ink)' }}>
          {errorMessage}
        </div>
      ) : null}

      {(stateStatus === 'failed' || stateStatus === 'partial') && failureMessage ? (
        <div className="rerun-banner">
          <div>
            <strong>{stateStatus === 'failed' ? 'Matching failed' : 'Partial run'}</strong>
            <p>{failureMessage}</p>
          </div>
          {rerunAction}
        </div>
      ) : null}

      <div className="layout">
        <section className="list">
          {loadingCampaign ? (
            <ListEmptyState
              title="Loading campaign"
              description="Connecting to the backend and fetching your campaign state."
              loading
            />
          ) : matches.length ? (
            matches.map((m, i) => {
              const circ = 2 * Math.PI * 28;
              const dash = circ * (m.match / 100);
              const matchClass = m.match >= 92 ? 'high' : 'mid';
              const isChecked = selectedIds.includes(m.id);
              const isContracted = contractedIds.has(m.id);

              return (
                <article key={m.id} className={`row ${isChecked ? 'checked' : ''}`} style={{ animationDelay: `${0.06 * i}s` }}>
                  <div className="rank-col" onClick={() => toggleSelection(m.id)}>
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
                      <div className="name-line">
                        <span className="name">{m.name}</span>
                        {m.verified ? (
                          <svg className="verified" viewBox="0 0 24 24" fill="currentColor"><path d="M12 1l2.4 2.1 3.1-.4 1.4 2.8 2.8 1.4-.4 3.1L23 12l-2.1 2.4.4 3.1-2.8 1.4-1.4 2.8-3.1-.4L12 23l-2.4-2.1-3.1.4-1.4-2.8-2.8-1.4.4-3.1L1 12l2.1-2.4-.4-3.1 2.8-1.4 1.4-2.8 3.1.4L12 1z" /><path d="M8.5 12.5l2.4 2.4 4.6-5" stroke="white" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
                        ) : null}
                      </div>
                      <span className="handle" title={m.handle}>{m.handle}</span>
                    </div>
                    <div className="reason">
                      <span className="spark"><svg viewBox="0 0 24 24" width="10" height="10" fill="currentColor"><path d="M12 3l1.8 4.5L18 9.3l-4.2 1.8L12 15.6l-1.8-4.5L6 9.3l4.2-1.8L12 3z" /></svg></span>
                      <span dangerouslySetInnerHTML={{ __html: m.reason }} />
                    </div>
                    <div className="tag-row">
                      <span className={`tag tag-tier ${tierClass[m.tier]}`}>{m.tier}</span>
                      {isContracted ? <span className="tag" style={{ background: 'var(--violet-soft)', color: 'var(--violet-ink)' }}>Contracted</span> : null}
                      {m.tags.map(t => <span key={t} className="tag">{t}</span>)}
                    </div>
                  </div>
                  <div className={`stats-col ${!hasMetricValue(m.followers) && !hasMetricValue(m.engagement) && !hasMetricValue(m.avgViews) && !hasMetricValue(m.rate) ? 'is-pending' : ''}`}>
                    <div><div className="lbl">Followers</div><div className={`val ${hasMetricValue(m.followers) ? '' : 'is-empty'}`}>{m.followers}</div></div>
                    <div><div className="lbl">Engagement</div><div className={`val eng ${hasMetricValue(m.engagement) ? '' : 'is-empty'}`}>{m.engagement}</div></div>
                    <div><div className="lbl">Avg views</div><div className={`val ${hasMetricValue(m.avgViews) ? '' : 'is-empty'}`}>{m.avgViews}</div></div>
                    <div><div className="lbl">Rate / post</div><div className={`val ${hasMetricValue(m.rate) ? '' : 'is-empty'}`}>{m.rate}</div></div>
                  </div>
                  <div className="actions-col">
                    <div className="match-ring" title={`${m.match}% match`}>
                      <svg width="74" height="74" viewBox="0 0 74 74">
                        <defs>
                          <linearGradient id={`grad-${m.id}`} x1="0" y1="0" x2="1" y2="1">
                            <stop offset="0%" stopColor="oklch(0.58 0.22 285)" />
                            <stop offset="100%" stopColor="oklch(0.74 0.18 30)" />
                          </linearGradient>
                        </defs>
                        <circle cx="37" cy="37" r="28" fill="none" stroke="var(--paper-2)" strokeWidth="6" />
                        <circle cx="37" cy="37" r="28" fill="none" stroke={`url(#grad-${m.id})`} strokeWidth="6" strokeLinecap="round"
                          strokeDasharray={`${dash} ${circ}`} style={{ transition: 'stroke-dasharray 1s' }} />
                      </svg>
                      <div className={`val ${matchClass}`}>{m.match}<span className="pct">% MATCH</span></div>
                    </div>
                    <Link href={`/profile/${encodeURIComponent(m.id)}?campaignId=${encodeURIComponent(campaignId)}`} className="row-cta">View profile <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M13 6l6 6-6 6" /></svg></Link>
                    <DeepAnalysisTrigger
                      influencerId={m.id}
                      campaignId={campaignId}
                      className="row-cta"
                      viewClassName="row-cta"
                      rerunClassName="row-cta row-cta-primary"
                      deepAnalysisReady={m.deepAnalysisReady}
                      deepAnalysisBlockReason={m.deepAnalysisBlockReason}
                    />
                    {!isContracted ? (
                      <button
                        type="button"
                        className="row-cta row-cta-contract"
                        disabled={markingContractId === m.id}
                        onClick={() => void handleMarkContracted(m.id)}
                      >
                        {markingContractId === m.id ? 'Saving…' : 'Mark contracted'}
                      </button>
                    ) : null}
                  </div>
                </article>
              );
            })
          ) : (
            <ListEmptyState
              title={emptyListState.title}
              description={emptyListState.description}
              stats={pipelineStats}
              progressPct={emptyListState.showProgress ? urlProgressPct : null}
              progressLabel={
                emptyListState.showProgress && urlProgressPct != null
                  ? `${urlProgressPct}% of discovered URLs scraped`
                  : undefined
              }
              loading={emptyListState.loading}
              action={rerunAction}
            />
          )}
        </section>

        <aside className="brief-side">
          <div className="head">
            <h4>Submitted brief</h4>
            <div className="sub">Reference</div>
          </div>
          <div className="body">
            <div className="row-k"><span className="k">Brand</span><span className="v">{liveBrief.brand}</span></div>
            <div className="row-k"><span className="k">Description</span><span className="v">{liveBrief.description}</span></div>
            <div className="row-k">
              <span className="k">Locations</span>
              <span className="v stack">
                {liveBrief.locs.length ? liveBrief.locs.map(l => <span key={l} className="pill">{l}</span>) : <span style={{ color: 'var(--muted-soft)', fontStyle: 'italic' }}>none</span>}
              </span>
            </div>
            <div className="row-k">
              <span className="k">Platforms</span>
              <span className="v stack">
                {liveBrief.platforms.length ? liveBrief.platforms.map(p => <span key={p} className="pill">{p}</span>) : <span style={{ color: 'var(--muted-soft)', fontStyle: 'italic' }}>none</span>}
              </span>
            </div>
            <div className="row-k"><span className="k">Tier</span><span className="v">{liveBrief.tier}</span></div>
            <div className="row-k"><span className="k">Budget</span><span className="v">{liveBrief.budget}</span></div>
          </div>
          <div className="conf">
            <div className="t">Pipeline status <strong>{titleize(stateStatus)}</strong></div>
            <div className="bar"></div>
            <div className="hint">
              Phase {titleize(statePhase)} · {pipelineState?.influencer_count ?? influencerResult?.total ?? 0} creators available
              {campaign?.partialResultsAvailable || pipelineState?.partial_results_available ? ' with partial results ready.' : '.'}
            </div>
          </div>
          <div className="conf" style={{ marginTop: '14px' }}>
            <div className="t">Recent activity <strong>{events.length}</strong></div>
            <div className="hint">
              {events.length ? (
                events.slice(-4).reverse().map(event => (
                  <div key={`${event.event_id}-${event.timestamp}`} style={{ marginTop: '8px' }}>
                    {eventLabel(event)}
                  </div>
                ))
              ) : (
                <span>No live events yet. Polling will keep state fresh.</span>
              )}
            </div>
          </div>
          {!loadingCampaign ? (
            <div className="foot">
              <CampaignBriefActions
                campaignId={campaignId}
                status={campaign?.status ?? stateStatus}
                label={campaign?.campaignName || campaign?.searchQuery || campaign?.product || liveBrief.description}
                onRerunStart={clearRerunState}
              />
            </div>
          ) : null}
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
              <h2>{liveBrief.description} · Creator Shortlist</h2>
              <div className="meta">
                <span><strong>Brand:</strong> {liveBrief.brand}</span>
                <span><strong>Platforms:</strong> {liveBrief.platforms.join(' + ')}</span>
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
                    <tr key={m.id}>
                      <td>{m.rank}</td>
                      <td>
                        <div className="pdf-name">{m.name}</div>
                        <span className="pdf-handle">{m.handle}</span>
                        <div className="pdf-tags">{m.tags.slice(0, 3).map(t => <span key={t} className="pdf-tag">{t}</span>)}</div>
                      </td>
                      <td>{titleize(m.platform)}</td>
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
    </div>
  );
}
