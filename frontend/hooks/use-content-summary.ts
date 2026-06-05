import { useState, useEffect, useCallback } from "react";
import { getContentSummary } from "@/lib/api";
import { ContentSummary } from "@/lib/types";

export function useContentSummary() {
  const [summary, setSummary] = useState<ContentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getContentSummary();
      setSummary(data);
    } catch (err: any) {
      setError(err.message || "Erro desconhecido ao carregar sumário");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return { summary, loading, error, refresh: fetchSummary };
}
