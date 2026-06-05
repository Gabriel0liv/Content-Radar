"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { getContentItems } from "@/lib/api";
import { ContentItemListResponse } from "@/lib/types";

export function useContentItems() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Helper to get parameters from URL
  const getParam = (key: string, defaultValue: string) => {
    return searchParams.get(key) || defaultValue;
  };

  const [filters, setFilters] = useState({
    search: getParam("search", ""),
    source: getParam("source", "Todos"),
    content_type: getParam("content_type", "Todos"),
    status: getParam("status", "Todos"),
    topic_seed: getParam("topic_seed", "Todos"),
    min_score: getParam("min_score", "") ? parseFloat(getParam("min_score", "")) : 0,
    min_views: getParam("min_views", "") ? parseInt(getParam("min_views", "")) : 0,
    sort_by: getParam("sort_by", "score"),
    sort_order: getParam("sort_order", "desc"),
    limit: getParam("limit", "") ? parseInt(getParam("limit", "")) : 50,
    offset: getParam("offset", "") ? parseInt(getParam("offset", "")) : 0,
  });

  const [data, setData] = useState<ContentItemListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Debounced search state
  const [debouncedSearch, setDebouncedSearch] = useState(filters.search);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(filters.search);
    }, 400);

    return () => {
      clearTimeout(handler);
    };
  }, [filters.search]);

  // Update URL search parameters
  const updateURL = useCallback((newFilters: typeof filters) => {
    const params = new URLSearchParams();
    Object.entries(newFilters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== "" && val !== "Todos" && val !== 0) {
        params.set(key, String(val));
      }
    });
    const query = params.toString() ? `?${params.toString()}` : "";
    router.replace(`${pathname}${query}`, { scroll: false });
  }, [pathname, router]);

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const apiParams = {
        limit: filters.limit,
        offset: filters.offset,
        search: debouncedSearch,
        source: filters.source,
        content_type: filters.content_type,
        status: filters.status,
        topic_seed: filters.topic_seed,
        min_score: filters.min_score > 0 ? filters.min_score : undefined,
        min_views: filters.min_views > 0 ? filters.min_views : undefined,
        sort_by: filters.sort_by,
        sort_order: filters.sort_order,
      };

      const result = await getContentItems(apiParams);
      setData(result);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar conteúdos");
    } finally {
      setLoading(false);
    }
  }, [
    filters.limit,
    filters.offset,
    debouncedSearch,
    filters.source,
    filters.content_type,
    filters.status,
    filters.topic_seed,
    filters.min_score,
    filters.min_views,
    filters.sort_by,
    filters.sort_order
  ]);

  // Fetch when filters or debounced search changes
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Sync state changes to URL
  const handleFilterChange = useCallback((key: keyof typeof filters, value: any) => {
    setFilters((prev: typeof filters) => {
      const next = { ...prev, [key]: value };
      // Reset offset to 0 when filter condition changes (except when offset itself is changed)
      if (key !== "offset") {
        next.offset = 0;
      }
      updateURL(next);
      return next;
    });
  }, [updateURL]);

  const resetFilters = useCallback(() => {
    const defaultFilters = {
      search: "",
      source: "Todos",
      content_type: "Todos",
      status: "Todos",
      topic_seed: "Todos",
      min_score: 0,
      min_views: 0,
      sort_by: "score",
      sort_order: "desc",
      limit: 50,
      offset: 0,
    };
    setFilters(defaultFilters);
    updateURL(defaultFilters);
  }, [updateURL]);

  return {
    items: data?.items || [],
    total: data?.total || 0,
    loading,
    error,
    filters,
    setFilter: handleFilterChange,
    resetFilters,
    refresh: fetchData
  };
}
