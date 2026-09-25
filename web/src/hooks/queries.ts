import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

export const useHealth = () => useQuery({ queryKey: ["health"], queryFn: api.health, staleTime: Infinity });

export const useLaws = () => useQuery({ queryKey: ["laws"], queryFn: () => api.listLaws() });

export const useLaw = (lawId: string | undefined) =>
  useQuery({ queryKey: ["law", lawId], queryFn: () => api.getLaw(lawId!), enabled: !!lawId });

export const useLawConnections = (lawId: string | undefined) =>
  useQuery({ queryKey: ["law-connections", lawId], queryFn: () => api.lawConnections(lawId!), enabled: !!lawId });

export const useArticle = (articleId: string | undefined) =>
  useQuery({ queryKey: ["article", articleId], queryFn: () => api.article(articleId!), enabled: !!articleId });

export const useInternational = (articleId: string | undefined) =>
  useQuery({
    queryKey: ["international", articleId],
    queryFn: () => api.international(articleId!),
    enabled: !!articleId,
  });

export const useSearch = (q: string) =>
  useQuery({ queryKey: ["search", q], queryFn: () => api.search(q), enabled: q.trim().length > 0 });

export const useDrafts = () => useQuery({ queryKey: ["drafts"], queryFn: api.listDrafts });

export const useDraft = (draftId: string | undefined) =>
  useQuery({ queryKey: ["draft", draftId], queryFn: () => api.draft(draftId!), enabled: !!draftId });

/** Debounced value for search-as-you-type. */
export function useDebounced<T>(value: T, ms = 250): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}
