"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { getCampaignState } from "@/lib/api";
import type { CampaignState } from "@/lib/api";
import { getCampaignWebSocketUrl } from "@/lib/websocket";

const TERMINAL_STATUSES = new Set(["completed", "partial", "failed", "cancelled"]);

export function useCampaignPipeline(campaignId: string | null) {
  const [state, setState] = useState<CampaignState | null>(null);
  const [events, setEvents] = useState<Array<{ type: string; payload?: Record<string, unknown> }>>([]);
  const [connected, setConnected] = useState(false);
  const lastEventIdRef = useRef(0);

  const refresh = useCallback(async () => {
    if (!campaignId) return;
    const next = await getCampaignState(campaignId);
    setState(next);
    if (typeof next.last_event_id === "number") {
      lastEventIdRef.current = Math.max(lastEventIdRef.current, next.last_event_id);
    }
  }, [campaignId]);

  useEffect(() => {
    if (!campaignId) return;
    void refresh();
  }, [campaignId, refresh]);

  useEffect(() => {
    if (!campaignId) return;
    let cancelled = false;
    let socket: WebSocket | null = null;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let wsConnected = false;

    const startPolling = () => {
      if (pollTimer) return;
      pollTimer = setInterval(() => {
        if (wsConnected) return;
        void refresh();
      }, 2500);
    };

    try {
      socket = new WebSocket(getCampaignWebSocketUrl(campaignId, { lastEventId: lastEventIdRef.current }));
      socket.onopen = () => {
        wsConnected = true;
        setConnected(true);
        if (pollTimer) {
          clearInterval(pollTimer);
          pollTimer = null;
        }
      };
      socket.onclose = () => {
        wsConnected = false;
        setConnected(false);
        startPolling();
      };
      socket.onerror = () => {
        wsConnected = false;
        setConnected(false);
        startPolling();
      };
      socket.onmessage = (message) => {
        if (cancelled) return;
        try {
          const parsed = JSON.parse(message.data) as {
            event_id?: number;
            type?: string;
            payload?: Record<string, unknown>;
          };
          if (typeof parsed.event_id === "number") {
            lastEventIdRef.current = Math.max(lastEventIdRef.current, parsed.event_id);
          }
          if (parsed.type) {
            const type = parsed.type;
            const payload = parsed.payload;
            setEvents((current) => [...current.slice(-19), { type, payload }]);
          }
          if (parsed.type !== "heartbeat") {
            void refresh();
          }
        } catch {
          /* ignore malformed frames */
        }
      };
    } catch {
      startPolling();
    }

    return () => {
      cancelled = true;
      socket?.close();
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [campaignId, refresh]);

  const isTerminal = state?.status ? TERMINAL_STATUSES.has(String(state.status)) : false;

  return {
    state,
    events,
    connected,
    isTerminal,
    refresh,
  };
}
