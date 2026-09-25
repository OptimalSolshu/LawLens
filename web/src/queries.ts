import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "./api";

export const useHealth = () => useQuery({ queryKey: ["health"], queryFn: api.health });

export const useLaws = (q: string) =>
  useQuery({ queryKey: ["laws", q], queryFn: () => api.listLaws(q), placeholderData: keepPreviousData });

export const useLaw = (lawId: string | null) =>
  useQuery({ queryKey: ["law", lawId], queryFn: () => api.getLaw(lawId!), enabled: !!lawId });
