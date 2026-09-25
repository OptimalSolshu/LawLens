import type {
  Amendment,
  Article,
  ArticleConnections,
  ArticleImpactRequest,
  Connections,
  Draft,
  DraftDetail,
  DraftGap,
  Health,
  ImpactRequest,
  ImpactResponse,
  International,
  LawDetail,
  LawSummary,
  RelationDetail,
  SearchResponse,
} from "../types/api";

/** "" = same origin (Vite proxy / nginx). On Vercel set VITE_API_BASE to the API origin. */
export const API_BASE = ((import.meta.env.VITE_API_BASE as string | undefined) ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new ApiError(res.status, `${init?.method ?? "GET"} ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

const enc = encodeURIComponent;

export const api = {
  health: () => request<Health>("/api/health"),
  listLaws: (q = "") => request<LawSummary[]>(`/api/laws?q=${enc(q)}`),
  getLaw: (lawId: string) => request<LawDetail>(`/api/laws/${enc(lawId)}`),
  lawArticles: (lawId: string) => request<Article[]>(`/api/laws/${enc(lawId)}/articles`),
  lawConnections: (lawId: string) => request<Connections>(`/api/laws/${enc(lawId)}/connections`),
  article: (articleId: string) => request<ArticleConnections>(`/api/articles/${enc(articleId)}/connections`),
  articleImpact: (articleId: string, body: ArticleImpactRequest) =>
    request<ImpactResponse>(`/api/articles/${enc(articleId)}/impact`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  impact: (body: ImpactRequest) =>
    request<ImpactResponse>("/api/impact", { method: "POST", body: JSON.stringify(body) }),
  listDrafts: () => request<Draft[]>("/api/drafts"),
  draft: (draftId: string) => request<DraftDetail>(`/api/drafts/${enc(draftId)}`),
  draftGap: (draftId: string) => request<DraftGap>(`/api/drafts/${enc(draftId)}/gaps`),
  international: (articleId: string) =>
    request<International>(`/api/articles/${enc(articleId)}/international`),
  amendment: (articleId: string) => request<Amendment>(`/api/articles/${enc(articleId)}/amendment`),
  relation: (a: string, b: string) =>
    request<RelationDetail>(`/api/articles/${enc(a)}/relations/${enc(b)}`),
  search: (q: string) => request<SearchResponse>(`/api/search?q=${enc(q)}`),
};

/** URL of GET /api/export (CSV). Values that are null/undefined/"" are left out. */
export function exportUrl(params: Record<string, string | number | null | undefined>): string {
  const qs = Object.entries(params)
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .map(([k, v]) => `${k}=${enc(String(v))}`)
    .join("&");
  return `${API_BASE}/api/export?${qs}`;
}
