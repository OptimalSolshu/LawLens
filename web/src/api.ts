import type {
  Amendment,
  ArticleConnections,
  Connections,
  Draft,
  DraftGap,
  Health,
  ImpactRequest,
  ImpactResponse,
  International,
  LawDetail,
  LawSummary,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`${init?.method ?? "GET"} ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

const enc = encodeURIComponent;

export const api = {
  health: () => request<Health>("/api/health"),
  listLaws: (q = "") => request<LawSummary[]>(`/api/laws?q=${enc(q)}`),
  getLaw: (lawId: string) => request<LawDetail>(`/api/laws/${enc(lawId)}`),
  lawConnections: (lawId: string) => request<Connections>(`/api/laws/${enc(lawId)}/connections`),
  article: (articleId: string) => request<ArticleConnections>(`/api/articles/${enc(articleId)}`),
  impact: (body: ImpactRequest) =>
    request<ImpactResponse>("/api/impact", { method: "POST", body: JSON.stringify(body) }),
  listDrafts: () => request<Draft[]>("/api/drafts"),
  draftGap: (draftId: string) => request<DraftGap>(`/api/drafts/${enc(draftId)}/gap`),
  international: (articleId: string) =>
    request<International>(`/api/articles/${enc(articleId)}/international`),
  amendment: (articleId: string) => request<Amendment>(`/api/articles/${enc(articleId)}/amendment`),
};
