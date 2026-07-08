"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL, getCampaignState, type CampaignState } from "@/lib/api";
import "./pipeline-debug.css";

// ── Types ────────────────────────────────────────────────────────────────────

type PipelineEvent = {
  type: string;
  event_id: number;
  campaign_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
};

type QueryItem = { index: number; text: string };

type SearchResult = {
  query: string;
  crawlSourceIds: string[];
  urls: string[];
};

type CrawlItem = {
  crawlSourceId: string;
  url: string;
  title?: string;
  status: "fetched" | "extracted" | "failed";
  socialLinks?: string[];
  metrics?: Record<string, unknown>;
};

type InfluencerItem = {
  id: string;
  name: string;
  grade?: string;
  finalScore?: number;
  subScores?: {
    relevance: number;
    credibility: number;
    engagement: number;
    sentiment: number;
    brand_safety: number;
  };
  explanation?: string;
};

type LogEntry = {
  ts: string;
  type: string;
  summary: string;
  eventId: number;
};

type WsStatus = "idle" | "connecting" | "connected" | "error";

// ── Helpers ──────────────────────────────────────────────────────────────────

const fmtTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  } catch { return iso.slice(11, 19); }
};

const gradeClass = (grade?: string) => {
  if (!grade) return "new";
  if (grade === "A+") return "a-plus";
  return grade.toLowerCase();
};

const initials = (name: string) =>
  name.split(/\s+/).slice(0, 2).map(w => w[0] ?? "?").join("").toUpperCase();

const logTypeClass = (type: string) => type.split(".")[0] ?? "info";

const STATE_STATUS_CLASS: Record<string, string> = {
  queued: "queued",
  running: "running",
  completed: "completed",
  partial: "partial",
  failed: "failed",
  cancelled: "cancelled",
};

const stateStatusClass = (status?: string) =>
  (status && STATE_STATUS_CLASS[status]) || "unknown";

const titleize = (s?: string) =>
  s ? s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) : "—";

const n = (v: unknown): number => (typeof v === "number" ? v : 0);

const buildWsUrl = (campaignId: string, lastEventId = 0) => {
  const base = API_BASE_URL
    ? API_BASE_URL.replace(/^http/, "ws").replace(/\/$/, "")
    : typeof window !== "undefined"
      ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`
      : "";
  if (!base) return null;
  return `${base}/ws/campaign/${encodeURIComponent(campaignId)}?last_event_id=${lastEventId}`;
};

const summariseEvent = (type: string, payload: Record<string, unknown>): string => {
  switch (type) {
    case "campaign.started":              return "status → running";
    case "query.generation.completed":    return `${payload.query_count ?? 0} queries generated`;
    case "search.executed":               return `"${payload.query}" → ${payload.result_count ?? 0} results`;
    case "search.failed":                 return `"${payload.query}" failed: ${payload.error}`;
    case "page.fetched":                  return String(payload.url ?? "");
    case "content.extracted":             return String(payload.title || payload.url || "");
    case "crawl.failed":                  return `crawl failed: ${payload.error}`;
    case "influencer.found":              return `+${(payload.new_influencer_ids as string[] | undefined)?.length ?? 0} new`;
    case "influencers.none":              return `no mentions found in ${payload.url}`;
    case "extract.failed":                return `extraction error: ${payload.error}`;
    case "platform.enriched":             return `${String(payload.influencer_id ?? "").slice(0, 8)}… — ${payload.profiles} profiles`;
    case "score.calculated":              return `${payload.canonical_name ?? payload.influencer_id} → ${typeof payload.final_score === "number" ? payload.final_score.toFixed(1) : "?"} (${payload.grade ?? "?"})`;
    case "brand_safety.flagged":          return `${payload.flag_count} flags on ${payload.mention_label}`;
    case "campaign.completed":            return "pipeline completed";
    case "campaign.failed":               return `failed: ${payload.reason ?? payload.failure_reason}`;
    case "campaign.cancelled":            return "pipeline cancelled";
    case "heartbeat":                     return "";
    default:                              return JSON.stringify(payload).slice(0, 80);
  }
};

// ── Component ────────────────────────────────────────────────────────────────

export default function PipelineDebugPage() {
  const [inputId, setInputId]         = useState("");
  const [campaignId, setCampaignId]   = useState<string | null>(null);
  const [wsStatus, setWsStatus]       = useState<WsStatus>("idle");
  const [state, setState]             = useState<CampaignState | null>(null);

  const [queries, setQueries]         = useState<QueryItem[]>([]);
  const [searches, setSearches]       = useState<SearchResult[]>([]);
  const [crawls, setCrawls]           = useState<CrawlItem[]>([]);
  const [influencers, setInfluencers] = useState<InfluencerItem[]>([]);
  const [log, setLog]                 = useState<LogEntry[]>([]);

  const wsRef          = useRef<WebSocket | null>(null);
  const lastEventIdRef = useRef<number>(0);
  const logScrollRef   = useRef<HTMLDivElement>(null);
  const crawlScrollRef = useRef<HTMLDivElement>(null);
  const infScrollRef   = useRef<HTMLDivElement>(null);

  const pushLog = useCallback((type: string, payload: Record<string, unknown>, eventId: number, ts: string) => {
    setLog(prev => [...prev, { ts, type, summary: summariseEvent(type, payload), eventId }]);
  }, []);

  const handleEvent = useCallback((evt: PipelineEvent) => {
    const { type, payload, event_id, timestamp } = evt;
    if (event_id > 0) lastEventIdRef.current = Math.max(lastEventIdRef.current, event_id);
    pushLog(type, payload, event_id, timestamp);

    if (type === "heartbeat") {
      const hbState = payload.state;
      if (hbState && typeof hbState === "object") {
        setState(prev => ({ ...(prev ?? {}), ...(hbState as CampaignState) }));
      }
      return;
    }

    switch (type) {
      case "query.generation.completed": {
        const qs = (payload.queries as string[] | undefined) ?? [];
        setQueries(qs.map((q, i) => ({ index: i + 1, text: q })));
        break;
      }

      case "search.executed": {
        const ids = (payload.crawl_source_ids as string[] | undefined) ?? [];
        setSearches(prev => [
          ...prev,
          { query: String(payload.query ?? ""), crawlSourceIds: ids, urls: [] },
        ]);
        break;
      }

      case "page.fetched": {
        const url = String(payload.url ?? "");
        const crawlSourceId = String(payload.crawl_source_id ?? "");

        // Add to crawl panel
        setCrawls(prev => {
          if (prev.some(c => c.crawlSourceId === crawlSourceId)) return prev;
          return [...prev, { crawlSourceId, url, status: "fetched" }];
        });

        // Back-fill real URL into the search result that owns this crawl source id
        setSearches(prev => prev.map(s =>
          s.crawlSourceIds.includes(crawlSourceId) && !s.urls.includes(url)
            ? { ...s, urls: [...s.urls, url] }
            : s
        ));
        break;
      }

      case "content.extracted": {
        const crawlSourceId = String(payload.crawl_source_id ?? "");
        const title   = payload.title as string | undefined;
        const links   = (payload.social_links as string[] | undefined) ?? [];
        const metrics = (payload.metrics as Record<string, unknown> | undefined) ?? {};
        setCrawls(prev => prev.map(c =>
          c.crawlSourceId === crawlSourceId
            ? { ...c, status: "extracted", title: title || c.title, socialLinks: links, metrics }
            : c
        ));
        break;
      }

      case "crawl.failed":
      case "extract.failed": {
        const crawlSourceId = String(payload.crawl_source_id ?? "");
        setCrawls(prev => prev.map(c =>
          c.crawlSourceId === crawlSourceId ? { ...c, status: "failed" } : c
        ));
        break;
      }

      case "influencer.found": {
        const newIds = (payload.new_influencer_ids as string[] | undefined) ?? [];
        setInfluencers(prev => {
          const existing = new Set(prev.map(i => i.id));
          const added: InfluencerItem[] = newIds
            .filter(id => !existing.has(id))
            .map(id => ({ id, name: `Influencer ${id.slice(0, 8)}` }));
          return [...prev, ...added];
        });
        break;
      }

      case "score.calculated": {
        const id   = String(payload.influencer_id ?? "");
        const name = String(payload.canonical_name ?? payload.influencer_name ?? `Influencer ${id.slice(0, 8)}`);
        const sub  = payload.sub_scores as Record<string, number> | undefined;
        const updated: InfluencerItem = {
          id,
          name,
          grade:      String(payload.grade ?? ""),
          finalScore: typeof payload.final_score === "number" ? payload.final_score : undefined,
          subScores: sub ? {
            relevance:    sub.relevance ?? 0,
            credibility:  sub.credibility ?? 0,
            engagement:   sub.engagement_quality ?? sub.engagement ?? 0,
            sentiment:    sub.sentiment ?? 0,
            brand_safety: sub.brand_safety ?? 0,
          } : undefined,
          explanation: payload.explanation as string | undefined,
        };
        setInfluencers(prev => {
          if (prev.some(i => i.id === id)) return prev.map(i => i.id === id ? { ...i, ...updated } : i);
          return [...prev, updated];
        });
        break;
      }

      default:
        break;
    }
  }, [pushLog]);

  const connect = useCallback(() => {
    if (!inputId.trim()) return;
    const id = inputId.trim();
    setCampaignId(id);

    wsRef.current?.close();
    wsRef.current = null;
    lastEventIdRef.current = 0;

    setQueries([]);
    setSearches([]);
    setCrawls([]);
    setInfluencers([]);
    setLog([]);
    setState(null);

    const url = buildWsUrl(id, 0);
    if (!url) { setWsStatus("error"); return; }

    setWsStatus("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen    = () => setWsStatus("connected");
    ws.onclose   = () => setWsStatus(prev => prev === "connecting" ? "error" : "idle");
    ws.onerror   = () => setWsStatus("error");
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data as string) as PipelineEvent;
        handleEvent(data);
      } catch { /* ignore */ }
    };
  }, [inputId, handleEvent]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setWsStatus("idle");
    setCampaignId(null);
    setState(null);
  }, []);

  useEffect(() => {
    const el = logScrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [log]);

  useEffect(() => {
    const el = crawlScrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [crawls]);

  useEffect(() => {
    const el = infScrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [influencers]);

  useEffect(() => {
    if (!campaignId) return;

    const status = state?.status;
    const isTerminal =
      status === "completed" ||
      status === "partial" ||
      status === "failed" ||
      status === "cancelled";
    if (isTerminal) return;

    let cancelled = false;
    const poll = async () => {
      try {
        const next = await getCampaignState(campaignId);
        if (!cancelled) setState(next);
      } catch {
        /* keep last known state on transient errors */
      }
    };
    void poll();
    const interval = window.setInterval(poll, 2500);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [campaignId, state?.status]);

  useEffect(() => () => { wsRef.current?.close(); }, []);

  const isConnected  = wsStatus === "connected";
  const statusLabel  = { idle: "Disconnected", connecting: "Connecting…", connected: "Live", error: "Error" }[wsStatus];
  const totalUrls    = searches.reduce((acc, s) => acc + s.crawlSourceIds.length, 0);

  return (
    <div className="pdbg">
      {/* ── Header ── */}
      <div className="pdbg-header">
        <div className="pdbg-title">
          InfluenceIQ <span>/</span> Pipeline Debug
        </div>

        <div className="pdbg-id-form">
          <input
            className="pdbg-id-input"
            placeholder="Paste campaign ID (UUID)…"
            value={inputId}
            onChange={e => setInputId(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !isConnected) connect(); }}
            disabled={isConnected}
            spellCheck={false}
          />
          {isConnected ? (
            <button className="pdbg-connect-btn stop" onClick={disconnect}>
              Disconnect
            </button>
          ) : (
            <button
              className="pdbg-connect-btn"
              onClick={connect}
              disabled={!inputId.trim() || wsStatus === "connecting"}
            >
              {wsStatus === "connecting" ? "Connecting…" : "Connect"}
            </button>
          )}
        </div>

        <div className="pdbg-status">
          <div className={`pdbg-dot ${wsStatus}`} />
          {statusLabel}
          {isConnected && campaignId && (
            <span style={{ color: "#4a4e5a", fontSize: "10.5px" }}>
              &nbsp;{campaignId.slice(0, 8)}…
            </span>
          )}
        </div>
      </div>

      {/* ── Body ── */}
      <div className="pdbg-body">
        {!campaignId ? (
          <div className="pdbg-idle">
            <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" style={{ color: "#2a2e3a" }}>
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v5l3 3" />
            </svg>
            <div className="pdbg-idle-title">Paste a campaign ID and click Connect</div>
            <div className="pdbg-idle-hint">
              Events stream live: queries → web search → page crawl → influencer extraction → scoring
            </div>
          </div>
        ) : (
          <>
            {/* State strip — driven by polling + heartbeat so the page is
                never blank when the pipeline is alive but quiet. */}
            <div className="pdbg-state-strip">
              <div className={`pdbg-state-badge ${stateStatusClass(state?.status)}`}>
                <span className="pdbg-state-dot" />
                {titleize(state?.status)}
              </div>
              <div className="pdbg-state-phase">
                <span className="pdbg-state-label">Phase</span>
                <span className="pdbg-state-value">{titleize(state?.phase)}</span>
              </div>
              <div className="pdbg-state-counters">
                <span className="pdbg-state-counter">
                  <span className="pdbg-state-label">URLs</span>
                  <span className="pdbg-state-value">
                    {n(state?.urls_scraped)}/{n(state?.urls_discovered)}
                  </span>
                </span>
                <span className="pdbg-state-counter">
                  <span className="pdbg-state-label">Influencers</span>
                  <span className="pdbg-state-value">{n(state?.influencers_found)}</span>
                </span>
                <span className="pdbg-state-counter">
                  <span className="pdbg-state-label">Scores</span>
                  <span className="pdbg-state-value">{n(state?.scores_computed)}</span>
                </span>
              </div>
              {state?.partial_results_available && state?.status !== "completed" && (
                <div className="pdbg-state-partial">partial results ready</div>
              )}
            </div>

            {/* Panel 1 — LLM Queries */}
            <div className="pdbg-panel">
              <div className="pdbg-panel-head">
                <div className="pdbg-panel-icon q">Q</div>
                <div className="pdbg-panel-title">LLM Queries</div>
                <div className="pdbg-panel-count">{queries.length}</div>
              </div>
              <div className="pdbg-scroll">
                {queries.length === 0 ? (
                  <div className="pdbg-empty">Waiting for query generation…</div>
                ) : queries.map(q => (
                  <div key={q.index} className="pdbg-query">
                    <div className="pdbg-query-num">{q.index}</div>
                    <div className="pdbg-query-text">{q.text}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Panel 2 — Search Results */}
            <div className="pdbg-panel">
              <div className="pdbg-panel-head">
                <div className="pdbg-panel-icon s">S</div>
                <div className="pdbg-panel-title">Search Results</div>
                <div className="pdbg-panel-count">{totalUrls} URLs</div>
              </div>
              <div className="pdbg-scroll">
                {searches.length === 0 ? (
                  <div className="pdbg-empty">Waiting for web searches…</div>
                ) : searches.map((s, i) => (
                  <div key={i} className="pdbg-search-result">
                    <div className="pdbg-search-query-label">Query: {s.query}</div>
                    <ul className="pdbg-url-list">
                      {s.urls.length > 0
                        ? s.urls.map((u, j) => (
                            <li key={j} className="pdbg-url-item">{u}</li>
                          ))
                        : Array.from({ length: s.crawlSourceIds.length }, (_, j) => (
                            <li key={j} className="pdbg-url-item" style={{ color: "#4a4e5a" }}>
                              Loading URL {j + 1}…
                            </li>
                          ))
                      }
                    </ul>
                    {s.crawlSourceIds.length === 0 && (
                      <div style={{ color: "#4a4e5a", fontSize: "11px" }}>No results</div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Panel 3 — Pages Scraped */}
            <div className="pdbg-panel">
              <div className="pdbg-panel-head">
                <div className="pdbg-panel-icon c">C</div>
                <div className="pdbg-panel-title">Pages Scraped</div>
                <div className="pdbg-panel-count">{crawls.length}</div>
              </div>
              <div className="pdbg-scroll" ref={crawlScrollRef}>
                {crawls.length === 0 ? (
                  <div className="pdbg-empty">Waiting for page crawls…</div>
                ) : crawls.map(c => (
                  <div key={c.crawlSourceId} className="pdbg-crawl">
                    <div className="pdbg-crawl-url">{c.url}</div>
                    {c.title && <div className="pdbg-crawl-title">{c.title}</div>}
                    <div className="pdbg-crawl-meta">
                      <span className={`pdbg-badge ${c.status === "extracted" ? "ok" : c.status === "failed" ? "fail" : "pending"}`}>
                        {c.status}
                      </span>
                      {c.metrics && Object.entries(c.metrics).slice(0, 2).map(([k, v]) => (
                        <span key={k}>{k}: {typeof v === "number" ? v.toFixed(2) : String(v)}</span>
                      ))}
                    </div>
                    {c.socialLinks && c.socialLinks.length > 0 && (
                      <div className="pdbg-social-chips">
                        {c.socialLinks.slice(0, 6).map((l, i) => (
                          <span key={i} className="pdbg-chip">
                            {l.length > 32 ? l.slice(0, 32) + "…" : l}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Panel 4 — Influencers Found */}
            <div className="pdbg-panel">
              <div className="pdbg-panel-head">
                <div className="pdbg-panel-icon i">I</div>
                <div className="pdbg-panel-title">Influencers Found</div>
                <div className="pdbg-panel-count">{influencers.length}</div>
              </div>
              <div className="pdbg-scroll" ref={infScrollRef}>
                {influencers.length === 0 ? (
                  <div className="pdbg-empty">Waiting for influencer extraction…</div>
                ) : influencers.map(inf => (
                  <div key={inf.id} className="pdbg-influencer">
                    <div className="pdbg-avatar">{initials(inf.name)}</div>
                    <div className="pdbg-influencer-body">
                      <div className="pdbg-influencer-name">{inf.name}</div>
                      <div className="pdbg-influencer-meta">{inf.id.slice(0, 16)}…</div>
                      <div className="pdbg-score-row">
                        {inf.grade ? (
                          <span className={`pdbg-score-chip ${gradeClass(inf.grade)}`}>
                            Grade {inf.grade}
                          </span>
                        ) : (
                          <span className="pdbg-score-chip new">Scoring…</span>
                        )}
                        {inf.finalScore !== undefined && (
                          <span style={{ fontSize: "11px", color: "#6c6f7a" }}>
                            {inf.finalScore.toFixed(1)} / 100
                          </span>
                        )}
                      </div>
                      {inf.subScores && (
                        <div className="pdbg-sub-scores">
                          {(
                            [
                              ["REL",  inf.subScores.relevance],
                              ["CRED", inf.subScores.credibility],
                              ["ENG",  inf.subScores.engagement],
                              ["SENT", inf.subScores.sentiment],
                              ["SAFE", inf.subScores.brand_safety],
                            ] as [string, number][]
                          ).map(([label, val]) => (
                            <div key={label} className="pdbg-sub">
                              <span style={{ width: "32px", flexShrink: 0, fontSize: "9.5px" }}>{label}</span>
                              <div className="pdbg-sub-bar">
                                <div className="pdbg-sub-fill" style={{ width: `${Math.min(100, val ?? 0)}%` }} />
                              </div>
                              <span style={{ width: "28px", textAlign: "right" }}>{(val ?? 0).toFixed(0)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {inf.explanation && (
                        <div style={{ fontSize: "11px", color: "#6c6f7a", marginTop: "5px", fontFamily: "'Geist',sans-serif", lineHeight: 1.5 }}>
                          {inf.explanation}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Event Log — full-width bottom strip */}
            <div className="pdbg-log-panel pdbg-panel">
              <div className="pdbg-panel-head">
                <div className="pdbg-panel-icon" style={{ background: "rgba(255,255,255,0.04)", color: "#6c6f7a" }}>✦</div>
                <div className="pdbg-panel-title">Raw Event Log</div>
                <div className="pdbg-panel-count">
                  {log.filter(l => l.type !== "heartbeat").length} events
                </div>
              </div>
              <div className="pdbg-log-entries" ref={logScrollRef}>
                {log.length === 0 ? (
                  <div style={{ padding: "12px 16px", color: "#2a2e3a", fontSize: "11.5px" }}>
                    No events yet — events will appear here as the pipeline runs
                  </div>
                ) : log.map((entry, i) => (
                  <div
                    key={i}
                    className="pdbg-log-row"
                    style={entry.type === "heartbeat" ? { opacity: 0.25 } : undefined}
                  >
                    <span className="pdbg-log-time">{fmtTime(entry.ts)}</span>
                    <span className={`pdbg-log-type ${logTypeClass(entry.type)}`}>{entry.type}</span>
                    <span className="pdbg-log-summary">{entry.summary}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
