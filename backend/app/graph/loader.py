"""Load a processed/ directory (contracts/data-format.md) into Neo4j.

    python -m app.graph.loader ../data/processed --reset
    python -m app.graph.loader ../contracts/fixtures/processed --reset   # [ЖИШЭЭ] sample graph

All statements are parameterised UNWIND batches. --reset wipes the API graph;
it refuses to touch a database that holds the exploration graph built by
load_neo4j.py (label :LawNode), see CLAUDE.md §10.
"""
import argparse
import json
import sys
from pathlib import Path

from ..ai.embeddings import DemoEmbedder
from .driver import get_driver
from .memory import _json, _jsonl

SCHEMA = Path(__file__).with_name("schema.cypher")
REL_TYPE = {"conflict": "CONFLICTS_WITH", "overlap": "OVERLAPS_WITH", "consistent": "CONSISTENT_WITH"}
BATCH = 500


def apply_schema(session) -> None:
    statements = "\n".join(l for l in SCHEMA.read_text().splitlines() if not l.lstrip().startswith("//"))
    for stmt in filter(None, (s.strip() for s in statements.split(";"))):
        session.run(stmt)


def _batches(rows: list[dict]):
    for i in range(0, len(rows), BATCH):
        yield rows[i:i + BATCH]


def _run(session, query: str, rows: list[dict]) -> None:
    for chunk in _batches(rows):
        session.run(query, rows=chunk)


def is_empty() -> bool:
    with get_driver().session() as s:
        return s.run("MATCH (l:Law) RETURN count(l) AS n").single()["n"] == 0


def load(processed_dir: Path, reset: bool = False, embed: bool = True) -> dict:
    laws = _jsonl(processed_dir / "laws.jsonl")
    refs = _jsonl(processed_dir / "refs.jsonl")
    similar = _jsonl(processed_dir / "similar.jsonl")
    relations = _jsonl(processed_dir / "relations.jsonl")
    amendments = _jsonl(processed_dir / "amendments.jsonl")
    drafts = _json(processed_dir / "drafts.json", [])
    intl = _json(processed_dir / "international.json", {"sources": [], "links": []})

    law_rows, art_rows, name_rows = [], [], []
    for law in laws:
        law_rows.append({"law_id": law["law_id"], "name": law["name"], "former_names": law.get("former_names", []),
                         "short_names": law.get("short_names", []), "adopted_date": law.get("adopted_date"),
                         "source_url": law["source_url"], "text_available": law.get("text_available", True),
                         "sample": bool(law.get("_sample"))})
        for kind, names in (("current", [law["name"]]), ("former", law.get("former_names", [])),
                            ("short", law.get("short_names", []))):
            name_rows += [{"law_id": law["law_id"], "name": n, "kind": kind} for n in names]
        for a in law.get("articles", []):
            art_rows.append({**a, "law_id": law["law_id"]})
    if embed and art_rows:
        emb = DemoEmbedder()
        texts = [f"{a.get('title') or ''} {a.get('text') or ''}" for a in art_rows]
        for a, v in zip(art_rows, emb.embed(texts)):
            a["embedding"], a["embedding_model"] = v, emb.model

    with get_driver().session() as s:
        if s.run("MATCH (n:LawNode) RETURN count(n) AS n").single()["n"]:
            raise SystemExit("This Neo4j holds the exploration graph (load_neo4j.py). Use a separate database "
                             "for the API graph (docker compose service 'neo4j', see README).")
        if reset:
            s.run("MATCH (n) WHERE n:Law OR n:LawName OR n:Article OR n:Draft OR n:Source OR n:Suggestion "
                  "DETACH DELETE n")
        apply_schema(s)
        _run(s, """UNWIND $rows AS r MERGE (l:Law {law_id: r.law_id})
                   SET l.name = r.name, l.former_names = r.former_names, l.short_names = r.short_names,
                       l.adopted_date = r.adopted_date, l.source_url = r.source_url,
                       l.text_available = r.text_available, l.sample = r.sample""", law_rows)
        _run(s, """UNWIND $rows AS r MATCH (l:Law {law_id: r.law_id}) MERGE (n:LawName {name: r.name})
                   MERGE (l)-[k:KNOWN_AS]->(n) SET k.kind = r.kind""", name_rows)
        _run(s, """UNWIND $rows AS r MATCH (l:Law {law_id: r.law_id})
                   MERGE (a:Article {article_id: r.article_id})
                   SET a.law_id = r.law_id, a.number = r.number, a.parent_number = r.parent_number,
                       a.title = r.title, a.text = r.text, a.embedding = r.embedding,
                       a.embedding_model = r.embedding_model
                   MERGE (l)-[:HAS_ARTICLE]->(a)""", art_rows)
        _run(s, """UNWIND $rows AS r MATCH (c:Article {article_id: r.article_id})
                   MATCH (p:Article {article_id: r.law_id + ':' + r.parent_number})
                   MERGE (c)-[:PART_OF]->(p)""", [a for a in art_rows if a.get("parent_number")])
        ref_rows = [{k: v for k, v in r.items() if k != "_sample"} for r in refs]
        for r in ref_rows:
            r.setdefault("current_number", None)
        _run(s, """UNWIND $rows AS r MATCH (s:Article {article_id: r.from_article_id})
                   MATCH (t:Article {article_id: r.to_article_id})
                   CREATE (s)-[:REFERS_TO {to_law_id: r.to_law_id, to_number: r.to_number,
                       to_article_id: r.to_article_id, raw_text: r.raw_text, matched_name: r.matched_name,
                       uses_old_name: r.uses_old_name, target_missing: r.target_missing,
                       current_number: r.current_number, method: r.method, confidence: r.confidence}]->(t)""",
             [r for r in ref_rows if r["to_article_id"]])
        _run(s, """UNWIND $rows AS r MATCH (s:Article {article_id: r.from_article_id})
                   MATCH (t:Law {law_id: r.to_law_id})
                   CREATE (s)-[:REFERS_TO {to_law_id: r.to_law_id, to_number: r.to_number,
                       to_article_id: null, raw_text: r.raw_text, matched_name: r.matched_name,
                       uses_old_name: r.uses_old_name, target_missing: r.target_missing,
                       current_number: r.current_number, method: r.method, confidence: r.confidence}]->(t)""",
             [r for r in ref_rows if not r["to_article_id"]])
        _run(s, """UNWIND $rows AS r MATCH (a:Article {article_id: r.a_article_id})
                   MATCH (b:Article {article_id: r.b_article_id})
                   MERGE (a)-[x:SIMILAR_TO]->(b) SET x.score = r.score, x.model = r.model""", similar)
        for kind, rel in REL_TYPE.items():
            # relationship types cannot be parameters; `rel` comes from the fixed REL_TYPE map above
            _run(s, f"""UNWIND $rows AS r MATCH (a:Article {{article_id: r.a_article_id}})
                        MATCH (b:Article {{article_id: r.b_article_id}})
                        MERGE (a)-[x:{rel}]->(b) SET x.kind = r.kind, x.confidence = r.confidence,
                            x.explanation = r.explanation, x.model = r.model""",
                 [r for r in relations if r["kind"] == kind])
        _run(s, """UNWIND $rows AS r MERGE (s:Source {source_id: r.source_id})
                   SET s.kind = r.kind, s.country_or_org = r.country_or_org, s.title = r.title,
                       s.provision = r.provision, s.url = r.url, s.summary = r.summary""",
             [{"provision": None, **x} for x in intl.get("sources", [])])
        _run(s, """UNWIND $rows AS r MATCH (a:Article {article_id: r.article_id})
                   MATCH (s:Source {source_id: r.source_id})
                   MERGE (a)-[x:RELEVANT_SOURCE]->(s)
                   SET x.relevance = r.relevance, x.explanation = r.explanation, x.model = r.model""",
             [{"model": None, **x} for x in intl.get("links", [])])
        _run(s, """UNWIND $rows AS r MATCH (a:Article {article_id: r.article_id})
                   CREATE (a)-[:AMENDMENT_SUGGESTION]->(:Suggestion {article_id: r.article_id, reason: r.reason,
                       suggested_text: r.suggested_text, based_on_source_ids: r.based_on_source_ids,
                       model: r.model, confidence: r.confidence})""",
             [{"confidence": None, **{k: v for k, v in x.items() if k != "_sample"}} for x in amendments])
        draft_rows = [{"draft_id": d["draft_id"], "lawforum_id": d["lawforum_id"], "title": d["title"],
                       "target_law_id": d["target_law_id"], "new_name": d.get("new_name"),
                       "source_url": d["source_url"], "amended_article_ids": d["amended_article_ids"],
                       "cosubmitted_law_ids": d["cosubmitted_law_ids"],
                       "cosubmitted_titles": d.get("cosubmitted_titles", []),
                       "operations_json": json.dumps(d.get("operations", []), ensure_ascii=False)} for d in drafts]
        _run(s, """UNWIND $rows AS r MERGE (d:Draft {draft_id: r.draft_id})
                   SET d += r
                   WITH d, r MATCH (l:Law {law_id: r.target_law_id}) MERGE (d)-[:TARGETS]->(l)""", draft_rows)
        _run(s, """UNWIND $rows AS r MATCH (d:Draft {draft_id: r.draft_id})
                   UNWIND r.cosubmitted_law_ids AS lid MATCH (l:Law {law_id: lid})
                   MERGE (d)-[:CO_SUBMITTED_FOR]->(l)""", draft_rows)
        ops = [{"draft_id": d["draft_id"], **o} for d in drafts for o in d.get("operations", []) if o.get("article_id")]
        _run(s, """UNWIND $rows AS r MATCH (d:Draft {draft_id: r.draft_id})
                   MATCH (a:Article {article_id: r.article_id})
                   MERGE (d)-[x:AMENDS]->(a) SET x.op = r.op, x.old_text = r.old_text, x.new_text = r.new_text""",
             ops)
    counts = {"laws": len(law_rows), "articles": len(art_rows), "refs": len(refs), "similar": len(similar),
              "relations": len(relations), "drafts": len(drafts), "sources": len(intl.get("sources", []))}
    print(f"loaded {processed_dir}: {counts}")
    return counts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("processed_dir", type=Path, nargs="?", default=Path("../data/processed"))
    ap.add_argument("--reset", action="store_true", help="delete the existing API graph first")
    ap.add_argument("--no-embed", action="store_true", help="skip demo embeddings for the vector index")
    args = ap.parse_args()
    if not args.processed_dir.exists():
        sys.exit(f"not found: {args.processed_dir}")
    load(args.processed_dir, reset=args.reset, embed=not args.no_embed)
