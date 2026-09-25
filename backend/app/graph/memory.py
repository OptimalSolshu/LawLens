"""In-memory GraphStore over a processed/ directory (contracts/data-format.md)."""
import json
from collections import defaultdict
from pathlib import Path

from ..parser.ids import ancestors, article_id, split_article_id
from .store import number_key, under


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


class MemoryStore:
    backend = "memory"

    def __init__(self, processed_dir: Path, dataset: str = "real"):
        self.dataset = dataset
        self.dir = processed_dir
        laws = _jsonl(processed_dir / "laws.jsonl")
        self._laws: dict[str, dict] = {}
        self._articles: dict[str, dict] = {}
        self._by_law: dict[str, list[dict]] = defaultdict(list)
        for law in laws:
            arts = law.pop("articles", [])
            law.pop("_sample", None)
            law.setdefault("text_available", True)
            law["article_count"] = len(arts)
            self._laws[law["law_id"]] = law
            for a in arts:
                rec = {**a, "law_id": law["law_id"]}
                self._articles[a["article_id"]] = rec
                self._by_law[law["law_id"]].append(rec)
        for arts in self._by_law.values():
            arts.sort(key=lambda a: number_key(a["number"]))

        self._refs = []
        for r in _jsonl(processed_dir / "refs.jsonl"):
            r.pop("_sample", None)
            r.setdefault("current_number", None)
            r["from_law_id"], _, r["from_number"] = r["from_article_id"].partition(":")
            self._refs.append(r)
        self._to_article = defaultdict(list)
        self._to_law_other = defaultdict(list)  # missing target or whole-law refs, by law
        self._from = defaultdict(list)
        for r in self._refs:
            if r["to_article_id"]:
                self._to_article[r["to_article_id"]].append(r)
            else:
                self._to_law_other[r["to_law_id"]].append(r)
            self._from[r["from_article_id"]].append(r)

        self._similar = [self._strip(r) for r in _jsonl(processed_dir / "similar.jsonl")]
        self._relations = [self._strip(r) for r in _jsonl(processed_dir / "relations.jsonl")]
        self._amendments = [self._strip(r) for r in _jsonl(processed_dir / "amendments.jsonl")]
        intl = _json(processed_dir / "international.json", {"sources": [], "links": []})
        self._sources = {s["source_id"]: s for s in intl.get("sources", [])}
        self._links = intl.get("links", [])
        self._drafts = [self._strip(d) for d in _json(processed_dir / "drafts.json", [])]

    @staticmethod
    def _strip(rec: dict) -> dict:
        rec.pop("_sample", None)
        return rec

    # ---- laws / articles -------------------------------------------------------
    def laws(self) -> list[dict]:
        return [dict(l) for l in self._laws.values()]

    def law(self, law_id: str) -> dict | None:
        law = self._laws.get(law_id)
        return dict(law) if law else None

    def articles(self, law_id: str) -> list[dict]:
        return [dict(a) for a in self._by_law.get(law_id, [])]

    def article(self, article_id: str) -> dict | None:
        a = self._articles.get(article_id)
        return dict(a) if a else None

    def articles_by_id(self, ids: list[str]) -> dict[str, dict]:
        return {i: dict(self._articles[i]) for i in ids if i in self._articles}

    def all_articles(self) -> list[dict]:
        return [dict(a) for a in self._articles.values()]

    # ---- references --------------------------------------------------------------
    def refs_to(self, law_id, article_ids, missing_prefixes, law_level):
        out = [r for aid in article_ids for r in self._to_article.get(aid, [])]
        for r in self._to_law_other.get(law_id, []):
            if r["to_number"] is None:
                if law_level:
                    out.append(r)
            elif r["target_missing"] and (missing_prefixes is None
                                          or any(under(r["to_number"], p) for p in missing_prefixes)):
                out.append(r)
        return [dict(r) for r in out]

    def indirect_refs(self, frontier_ids, seed_ids, max_depth):
        seen = set(seed_ids) | set(frontier_ids)
        frontier, out = list(frontier_ids), []
        for depth in range(2, max_depth + 1):
            found: dict[str, list[dict]] = defaultdict(list)
            for via in frontier:
                law_id, number = split_article_id(via)
                targets = [article_id(law_id, n) for n in [number, *ancestors(number)]]
                for r in self.refs_to(law_id, targets, [], False):
                    if r["from_article_id"] not in seen:
                        found[r["from_article_id"]].append({**r, "via_article_id": via, "depth": depth})
            seen |= found.keys()
            out += [r for rs in found.values() for r in rs]
            frontier = list(found)
        return out

    def refs_from(self, article_ids):
        return [dict(r) for aid in article_ids for r in self._from.get(aid, [])]

    # ---- suggestions ---------------------------------------------------------------
    def similar(self, article_ids):
        ids = set(article_ids)
        return [dict(r) for r in self._similar if r["a_article_id"] in ids or r["b_article_id"] in ids]

    def relations(self, article_ids):
        ids = set(article_ids)
        return [dict(r) for r in self._relations if r["a_article_id"] in ids or r["b_article_id"] in ids]

    def intl_links(self, article_ids):
        ids = set(article_ids)
        return [{**self._sources[l["source_id"]], **l} for l in self._links
                if l["article_id"] in ids and l["source_id"] in self._sources]

    def intl_sources(self):
        return dict(self._sources)

    def amendments(self, article_ids):
        ids = set(article_ids)
        return sorted((dict(a) for a in self._amendments if a["article_id"] in ids), key=lambda a: a["article_id"])

    # ---- drafts -----------------------------------------------------------------------
    def drafts(self):
        return [dict(d) for d in self._drafts]

    def draft(self, draft_id):
        return next((dict(d) for d in self._drafts if d["draft_id"] == draft_id), None)
