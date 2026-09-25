// Mirrors backend/app/models.py (contracts/api.md). Change both together, via PR.

export type ItemType = "fact" | "suggestion";

export interface Flags {
  uses_old_name: boolean;
  target_missing: boolean;
}

/** Always describes the OTHER provision; anchor_number is the selected side. */
export interface RefItem {
  law_id: string;
  law_name: string;
  article_id: string | null;
  number: string | null;
  snippet: string;
  source_url: string;
  type: ItemType;
  confidence: number;
  flags: Flags;
  anchor_number?: string | null;
  score?: number | null;
  explanation?: string | null;
}

export interface LawGroup {
  law_id: string;
  law_name: string;
  count: number;
  items: RefItem[];
}

export interface Health {
  status: "ok";
  mock: boolean;
}

export interface LawSummary {
  law_id: string;
  name: string;
  former_names: string[];
  article_count: number;
}

export interface Law {
  law_id: string;
  name: string;
  former_names: string[];
  short_names: string[];
  adopted_date: string | null;
  source_url: string;
}

export interface Article {
  article_id: string;
  number: string;
  title: string | null;
  text: string;
}

export interface LawDetail {
  law: Law;
  articles: Article[];
}

export interface ArticleDetail extends Article {
  law_id: string;
  law_name: string;
  source_url: string;
}

export interface ConnectionTotals {
  incoming: number;
  outgoing: number;
  former_name_refs: number;
  missing_target_refs: number;
  similar: number;
  conflicts: number;
}

export interface Connections {
  incoming: LawGroup[];
  outgoing: LawGroup[];
  former_name_refs: LawGroup[];
  missing_target_refs: LawGroup[];
  similar: RefItem[];
  conflicts: RefItem[];
  totals: ConnectionTotals;
}

export interface ArticleConnections extends Connections {
  article: ArticleDetail;
}

export interface ImpactRequest {
  law_id?: string | null;
  article_id?: string | null;
  new_text?: string | null;
  new_name?: string | null;
  depth: 1 | 2 | 3;
}

export interface ImpactDepth {
  depth: number;
  groups: LawGroup[];
  count: number;
}

export interface ImpactResponse {
  depths: ImpactDepth[];
  new_similar: RefItem[];
  totals: { laws: number; articles: number; new_similar: number };
}

export interface Draft {
  draft_id: string;
  lawforum_id: string;
  title: string;
  target_law_id: string;
  new_name: string | null;
  amended_article_ids: string[];
  cosubmitted_law_ids: string[];
  source_url: string;
}

export interface DraftGap {
  draft_id: string;
  found: number;
  covered: LawGroup[];
  missing: LawGroup[];
}

export interface IntlItem {
  source_id: string;
  kind: "foreign_law" | "treaty";
  country_or_org: string;
  title: string;
  url: string;
  summary: string;
  relevance: number;
  explanation: string;
  type: "suggestion";
}

export interface International {
  article_id: string;
  foreign_laws: IntlItem[];
  treaties: IntlItem[];
}

export interface SourceRef {
  kind: "law_article" | "foreign_law" | "treaty";
  id: string;
  title: string;
  url: string;
}

export interface Amendment {
  article_id: string;
  suggested_text: string;
  reason: string;
  sources: SourceRef[];
  type: "suggestion";
  confidence: number;
  model: string;
}
