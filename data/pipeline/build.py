"""Build a complete processed/ directory (contracts/data-format.md) from
parsed laws, name registries, drafts and curated international sources.

Used by scripts/seed_demo.py (the [ЖИШЭЭ] sample dataset) and by
scripts/build_processed_data.py (real data). Facts (refs.jsonl) come only from
the deterministic parser; similar/relations/links/amendments are suggestions
and always carry a model name.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import _backend  # noqa: F401  (sys.path for backend/app)
from app.ai.embeddings import Embedder, min_score
from app.ai.relations import LLMRelationService, Provision
from app.graph.store import number_key
from app.parser import LawNameRegistry, extract_references, load_law_names, parse_amendments
from app.parser.amendments import law_in_title
from app.parser.names import NameEntry

from .schemas import (AmendmentRec, DraftRec, InternationalFile, LawRec, RefRec, RelationRec,
                      SimilarRec)

STUB_URL = "https://legalinfo.mn/mn"


@dataclass
class BuildInput:
    laws: list[dict]  # laws.jsonl-shaped dicts with articles (text_available laws)
    law_names_files: list[Path] = field(default_factory=list)
    renumbering: dict[str, dict[str, str]] = field(default_factory=dict)
    # {lawforum_id, title, source_url, text, cosubmitted[], target_law?, new_name?}
    drafts: list[dict] = field(default_factory=list)
    intl_sources: list[dict] = field(default_factory=list)
    intl_links: list[dict] = field(default_factory=list)
    sample: bool = False
    stub_url: str = STUB_URL


@dataclass
class BuildOutput:
    laws: list[LawRec]
    refs: list[RefRec]
    similar: list[SimilarRec]
    relations: list[RelationRec]
    drafts: list[DraftRec]
    international: InternationalFile
    amendments: list[AmendmentRec]

    def write(self, out: Path) -> None:
        out.mkdir(parents=True, exist_ok=True)
        dump = lambda r: r.model_dump_json(by_alias=True, exclude={"sample"} if not r.sample else None)
        for name, recs in (("laws.jsonl", self.laws), ("refs.jsonl", self.refs), ("similar.jsonl", self.similar),
                           ("relations.jsonl", self.relations), ("amendments.jsonl", self.amendments)):
            (out / name).write_text("".join(dump(r) + "\n" for r in recs), encoding="utf-8")
        drafts = [json.loads(dump(d)) for d in self.drafts]
        (out / "drafts.json").write_text(json.dumps(drafts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (out / "international.json").write_text(
            json.dumps(json.loads(dump(self.international)), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def summary(self) -> str:
        return (f"{len(self.laws)} laws ({sum(not l.text_available for l in self.laws)} name-only), "
                f"{sum(len(l.articles) for l in self.laws)} articles, {len(self.refs)} refs "
                f"({sum(r.uses_old_name for r in self.refs)} old name, {sum(r.target_missing for r in self.refs)} missing), "
                f"{len(self.similar)} similar, {len(self.relations)} relations, {len(self.drafts)} drafts, "
                f"{len(self.international.links)} intl links, {len(self.amendments)} amendment suggestions")


def similar_pairs(texts: list[str], groups: list[str], embedder: Embedder, block: int = 512):
    """(i, j, cosine) for i < j in different groups with cosine >= the model's threshold.
    Embeddings are unit vectors, so cosine is a dot product: one matrix product per block
    of rows instead of a Python loop over every pair (≈10^8 pairs for the connected laws)."""
    if not texts:
        return
    vectors = np.asarray(embedder.embed(texts), dtype=np.float64)
    group_ids = np.unique(np.asarray(groups), return_inverse=True)[1]
    threshold = min_score(embedder.model)
    for start in range(0, len(texts), block):
        scores = vectors[start:start + block] @ vectors.T
        rows = np.arange(start, min(start + block, len(texts)))[:, None]
        cols = np.arange(len(texts))[None, :]
        keep = (cols > rows) & (group_ids[rows] != group_ids[cols]) & (scores >= threshold)
        for r, c in zip(*np.nonzero(keep)):
            yield int(rows[r, 0]), int(c), float(scores[r, c])


SIMILAR_TOP_K = 3  # per provision; ~50k provisions otherwise give >150k pairs, mostly weak n-gram overlaps


def top_k_per_article(similar: list[SimilarRec], k: int) -> list[SimilarRec]:
    """Keep a pair when it is among the k best for either of its provisions, best first."""
    ranked = sorted(similar, key=lambda r: (-r.score, r.a_article_id, r.b_article_id))
    seen: dict[str, int] = {}
    keep = []
    for r in ranked:
        if seen.get(r.a_article_id, 0) < k or seen.get(r.b_article_id, 0) < k:
            keep.append(r)
        for aid in (r.a_article_id, r.b_article_id):
            seen[aid] = seen.get(aid, 0) + 1
    return keep


def build(inp: BuildInput, embedder: Embedder, relations: LLMRelationService) -> BuildOutput:
    s = {"_sample": True} if inp.sample else {}
    names_meta = [rec for f in inp.law_names_files for rec in load_law_names(f)]
    registry = LawNameRegistry.from_sources(inp.laws)
    for rec in names_meta:
        law = next((l for l in inp.laws if l["law_id"] == rec["law_id"] or l["name"] == rec["current_name"]), None)
        if law is None:
            registry.add_law(rec["law_id"], rec["current_name"], rec["former_names"], rec["short_names"], rec["aliases"])
        else:  # a parsed law: its aliases ("Монгол Улсын Их Хурлын тухай хууль") resolve to it too
            for v in rec["aliases"]:
                registry.add(NameEntry(law["law_id"], v, law["name"], "alias"))
    numbers = {l["law_id"]: {a["number"] for a in l["articles"]} for l in inp.laws}
    articles = {a["article_id"]: (l, a) for l in inp.laws for a in l["articles"]}

    # ---- facts: references --------------------------------------------------
    refs: list[RefRec] = []
    for law in inp.laws:
        for a in law["articles"]:
            for r in extract_references(a["text"] or "", from_article_id=a["article_id"], registry=registry,
                                        numbers_by_law=numbers, renumbering=inp.renumbering):
                refs.append(RefRec(**r.to_dict(), **s))

    # ---- laws (+ name-only stubs for cited laws without text) ----------------
    laws = [LawRec(**{**l, **s}) for l in inp.laws]
    known = {l.law_id for l in laws}
    meta_by_id = {m["law_id"]: m for m in names_meta}
    for r in refs:
        if r.to_law_id in known:
            continue
        entry = next((e for e in registry.entries() if e.law_id == r.to_law_id), None)
        m = meta_by_id.get(r.to_law_id, {})
        name = entry.canonical if entry else r.matched_name
        laws.append(LawRec(law_id=r.to_law_id, name=name, former_names=m.get("former_names", []),
                           short_names=m.get("short_names", []), adopted_date=None,
                           source_url=m.get("source_url") or inp.stub_url, articles=[], text_available=False, **s))
        known.add(r.to_law_id)

    # ---- suggestions: similar provisions ---------------------------------------
    linked = {frozenset((r.from_article_id, r.to_article_id)) for r in refs if r.to_article_id}
    texts = [(aid, a["text"]) for aid, (_, a) in articles.items() if a["text"]]
    similar: list[SimilarRec] = []
    for i, j, score in similar_pairs([t for _, t in texts], [aid.split(":")[0] for aid, _ in texts], embedder):
        ai, bj = texts[i][0], texts[j][0]
        if frozenset((ai, bj)) in linked:
            continue
        a_id, b_id = sorted((ai, bj))
        similar.append(SimilarRec(a_article_id=a_id, b_article_id=b_id, score=round(min(score, 1.0), 3),
                                  model=embedder.model, **s))
    similar = top_k_per_article(similar, SIMILAR_TOP_K)

    # ---- suggestions: relation judgements + resolution -------------------------
    def prov(aid: str) -> Provision:
        law, a = articles[aid]
        return Provision(article_id=aid, law_name=law["name"], number=a["number"], text=a["text"])

    sources = {src["source_id"]: src for src in inp.intl_sources}
    links_by_article: dict[str, list[str]] = {}
    for ln in inp.intl_links:
        links_by_article.setdefault(ln["article_id"], []).append(ln["source_id"])
    rels: list[RelationRec] = []
    amendments: list[AmendmentRec] = []
    for sim in similar:
        a, b = prov(sim.a_article_id), prov(sim.b_article_id)
        j = relations.judge(a, b)
        rels.append(RelationRec(a_article_id=a.article_id, b_article_id=b.article_id, kind=j.kind,
                                confidence=j.confidence, explanation=j.explanation, model=j.model, **s))
        if j.kind == "consistent":
            continue
        src_ids = sorted(set(links_by_article.get(a.article_id, []) + links_by_article.get(b.article_id, [])))
        res = relations.suggest_resolution(a, b, j, [sources[i] for i in src_ids if i in sources])
        if res:
            art = res.article_id or a.article_id
            amendments.append(AmendmentRec(article_id=art, reason=res.reason, suggested_text=res.suggested_text,
                                           based_on_source_ids=res.based_on_source_ids + [a.article_id, b.article_id],
                                           model=res.model, confidence=res.confidence, **s))

    # ---- drafts ----------------------------------------------------------------
    drafts: list[DraftRec] = []
    for d in inp.drafts:
        # a revised law (шинэчилсэн найруулга) under a new title names the law it replaces
        # in target_law/new_name; its own text is the new law, not amendment wording
        replaces = d.get("target_law")
        ops = [] if replaces else parse_amendments(d["text"], registry=registry, numbers_by_law=numbers)
        target = law_in_title(replaces or d["title"], registry) or (ops[0].law_id if ops else None)
        if target is None:
            continue
        cos = [c["title"] for c in d.get("cosubmitted", [])]
        cos_ids = [x for x in (law_in_title(t, registry) for t in cos) if x and x != target]
        rename = d.get("new_name") or next((o.new_text for o in ops if o.op == "rename" and o.law_id == target), None)
        drafts.append(DraftRec(
            draft_id=f"draft-{d['lawforum_id']}", lawforum_id=d["lawforum_id"], title=d["title"],
            target_law_id=target, new_name=rename,
            amended_article_ids=sorted({o.article_id for o in ops if o.article_id and o.law_id == target},
                                       key=lambda x: number_key(x.split(":")[1])),
            cosubmitted_law_ids=list(dict.fromkeys(cos_ids)), source_url=d["source_url"],
            operations=[o.to_dict() for o in ops], cosubmitted_titles=cos, **s))

    # ---- international -----------------------------------------------------------
    intl = InternationalFile(sources=inp.intl_sources,
                             links=[ln for ln in inp.intl_links if ln["article_id"] in articles], **s)
    return BuildOutput(laws, refs, similar, rels, drafts, intl, amendments)
