"use client";

import { useCallback, useEffect, useState } from "react";

import {
  getCampaignFacets,
  getCampaignInfluencers,
  type CampaignFacets,
  type InfluencerListResult,
} from "@/lib/api";
import type { InfluencerRecommendation } from "@/types/influencer";

export type CampaignInfluencerFilters = {
  platform?: string;
  grade?: string;
  niche?: string;
  location?: string;
};

type UseCampaignInfluencersOptions = {
  limit?: number;
  enabled?: boolean;
};

export function useCampaignInfluencers(
  campaignId: string | undefined,
  options: UseCampaignInfluencersOptions = {}
) {
  const limit = options.limit ?? 24;
  const enabled = options.enabled ?? Boolean(campaignId);

  const [filters, setFiltersState] = useState<CampaignInfluencerFilters>({});
  const [items, setItems] = useState<InfluencerRecommendation[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [facets, setFacets] = useState<CampaignFacets | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  const buildParams = useCallback(
    (cursor?: string | null) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (filters.platform) params.set("platform", filters.platform);
      if (filters.grade) params.set("grade", filters.grade);
      if (filters.niche) params.set("niche", filters.niche);
      if (filters.location) params.set("location", filters.location);
      if (cursor) params.set("cursor", cursor);
      return params;
    },
    [filters.grade, filters.location, filters.niche, filters.platform, limit]
  );

  const applyResult = useCallback((result: InfluencerListResult, append: boolean) => {
    setItems((current) => (append ? [...current, ...result.items] : result.items));
    setNextCursor(result.nextCursor);
  }, []);

  const loadFacets = useCallback(async () => {
    if (!campaignId) return;
    const nextFacets = await getCampaignFacets(campaignId);
    setFacets(nextFacets);
    setTotal(nextFacets.total);
  }, [campaignId]);

  const refresh = useCallback(async () => {
    if (!campaignId || !enabled) return;

    try {
      setLoading(true);
      setError("");
      const [result] = await Promise.all([
        getCampaignInfluencers(campaignId, buildParams()),
        loadFacets(),
      ]);
      applyResult(result, false);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Unable to load creators");
    } finally {
      setLoading(false);
    }
  }, [applyResult, buildParams, campaignId, enabled, loadFacets]);

  const loadMore = useCallback(async () => {
    if (!campaignId || !nextCursor || loadingMore) return;

    try {
      setLoadingMore(true);
      setError("");
      const result = await getCampaignInfluencers(campaignId, buildParams(nextCursor));
      applyResult(result, true);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Unable to load more creators");
    } finally {
      setLoadingMore(false);
    }
  }, [applyResult, buildParams, campaignId, loadingMore, nextCursor]);

  const setFilters = useCallback((next: CampaignInfluencerFilters) => {
    setFiltersState(next);
  }, []);

  const clearFilters = useCallback(() => {
    setFiltersState({});
  }, []);

  useEffect(() => {
    if (!campaignId || !enabled) {
      setItems([]);
      setNextCursor(null);
      setFacets(null);
      setTotal(0);
      return;
    }

    void refresh();
  }, [campaignId, enabled, filters, refresh]);

  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  return {
    items,
    total,
    facets,
    filters,
    setFilters,
    clearFilters,
    activeFilterCount,
    loading,
    loadingMore,
    error,
    loadMore,
    hasMore: Boolean(nextCursor),
    refresh,
  };
}
