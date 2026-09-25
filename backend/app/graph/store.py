"""GraphStore: the small set of graph primitives every service uses.

Two implementations return identical plain-dict records:
- MemoryStore (app/graph/memory.py): loads a processed/ directory into memory.
  Used for MOCK=1 (sample dataset) and for GRAPH_BACKEND=memory.
- Neo4jStore (app/graph/neo4j_store.py): parameterised Cypher against the
  knowledge graph loaded by app/graph/loader.py.

Record shapes
  law:      law_id, name, former_names, short_names, adopted_date, source_url,
            text_available, article_count
  article:  article_id, law_id, number, parent_number, title, text
  ref:      from_article_id, from_law_id, from_number, to_law_id, to_number,
            to_article_id, raw_text, matched_name, uses_old_name, target_missing,
            current_number, method, confidence
  similar:  a_article_id, b_article_id, score, model
  relation: a_article_id, b_article_id, kind, confidence, explanation, model
  intl:     article_id, source_id, relevance, explanation, model + source fields
  amendment: article_id, reason, suggested_text, based_on_source_ids, model, confidence
  draft:    drafts.json record
"""
from typing import Protocol


class GraphStore(Protocol):
    dataset: str  # "sample" | "real"
    backend: str  # "memory" | "neo4j"

    def laws(self) -> list[dict]: ...
    def law(self, law_id: str) -> dict | None: ...
    def articles(self, law_id: str) -> list[dict]: ...
    def article(self, article_id: str) -> dict | None: ...
    def articles_by_id(self, ids: list[str]) -> dict[str, dict]: ...
    def all_articles(self) -> list[dict]: ...

    def refs_to(self, law_id: str, article_ids: list[str], missing_prefixes: list[str] | None,
                law_level: bool) -> list[dict]:
        """Refs whose target is one of article_ids, OR a missing provision of law_id whose
        number equals / is under one of missing_prefixes (None = any), OR (law_level) a
        whole-law reference to law_id."""

    def refs_from(self, article_ids: list[str]) -> list[dict]: ...
    def similar(self, article_ids: list[str]) -> list[dict]: ...
    def relations(self, article_ids: list[str]) -> list[dict]: ...
    def intl_links(self, article_ids: list[str]) -> list[dict]: ...
    def intl_sources(self) -> dict[str, dict]: ...
    def amendments(self, article_ids: list[str]) -> list[dict]: ...
    def drafts(self) -> list[dict]: ...
    def draft(self, draft_id: str) -> dict | None: ...


def number_key(number: str | None) -> tuple:
    if not number:
        return (10**9,)
    return tuple(int(p) if p.isdigit() else 0 for p in number.split("."))


def under(number: str | None, prefix: str) -> bool:
    return bool(number) and (number == prefix or number.startswith(prefix + "."))
