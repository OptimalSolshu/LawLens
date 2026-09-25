"""parse_law.py-ийн гаргасан JSON-ийг Neo4j руу ачаалах.

Хэрэглээ:
    python load_neo4j.py data/labor_law_2021.json [--reset]
"""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

SCHEMA = [
    "CREATE CONSTRAINT law_node_uid IF NOT EXISTS FOR (n:LawNode) REQUIRE n.uid IS UNIQUE",
    "CREATE CONSTRAINT law_id IF NOT EXISTS FOR (n:Law) REQUIRE n.id IS UNIQUE",
    "CREATE INDEX actor_name IF NOT EXISTS FOR (n:Actor) ON (n.name)",
    "CREATE CONSTRAINT extlaw_name IF NOT EXISTS FOR (n:ExternalLaw) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT amending_date IF NOT EXISTS FOR (n:AmendingLaw) REQUIRE n.date IS UNIQUE",
    "CREATE INDEX provision_number IF NOT EXISTS FOR (n:Provision) ON (n.number)",
    "CREATE INDEX article_number IF NOT EXISTS FOR (n:Article) ON (n.number)",
    "CREATE FULLTEXT INDEX provision_text IF NOT EXISTS FOR (n:Provision) ON EACH [n.text]",
    "CREATE FULLTEXT INDEX titles IF NOT EXISTS FOR (n:Article|Chapter|Section|Term) ON EACH [n.title, n.name, n.definition]",
]


def uid(law_id, local_id):
    return f"{law_id}:{local_id}"


def load(session, d):
    law = d["law"]
    L = law["id"]
    run = session.run

    run("MERGE (l:Law {id:$id}) SET l += $props", id=L, props=law)

    run("""UNWIND $rows AS r
           MATCH (l:Law {id:$law})
           MERGE (c:Chapter:LawNode {uid:r.uid}) SET c.number=r.number, c.title=r.title, c.law=$law
           MERGE (l)-[:HAS_CHAPTER]->(c)""",
        law=L, rows=[{**c, "uid": uid(L, c["id"])} for c in d["chapters"]])

    run("""UNWIND $rows AS r
           MATCH (c:Chapter {uid:r.chapter})
           MERGE (s:Section:LawNode {uid:r.uid}) SET s.number=r.number, s.title=r.title, s.law=$law
           MERGE (c)-[:HAS_SECTION]->(s)""",
        law=L, rows=[{**s, "uid": uid(L, s["id"]), "chapter": uid(L, s["chapter"])} for s in d.get("sections", [])])

    # Дэд бүлэгтэй бол дэд бүлэгт, үгүй бол бүлэгт шууд харьяална
    run("""UNWIND $rows AS r
           MATCH (parent:LawNode {uid:r.parent})
           MERGE (a:Article:LawNode {uid:r.uid}) SET a.number=r.number, a.title=r.title, a.law=$law
           MERGE (parent)-[:HAS_ARTICLE]->(a)""",
        law=L, rows=[{**a, "uid": uid(L, a["id"]), "parent": uid(L, a.get("section") or a["chapter"])}
                     for a in d["articles"]])

    arts = sorted(d["articles"], key=lambda a: a["number"])
    run("""UNWIND $rows AS r
           MATCH (a:Article {uid:r.a}), (b:Article {uid:r.b}) MERGE (a)-[:NEXT]->(b)""",
        rows=[{"a": uid(L, x["id"]), "b": uid(L, y["id"])} for x, y in zip(arts, arts[1:])])

    # Хэсэг (level 1) = :Part, заалт (level 2) = :Point
    for level, label in ((1, "Part"), (2, "Point")):
        run(f"""UNWIND $rows AS r
               MATCH (parent:LawNode {{uid:r.parent}})
               MERGE (p:Provision:{label}:LawNode {{uid:r.uid}})
               SET p.number=r.number, p.level=r.level, p.text=r.text, p.status=r.status,
                   p.modality=r.modality, p.law=$law
               MERGE (parent)-[:HAS_PROVISION]->(p)""",
            law=L, rows=[{**p, "uid": uid(L, p["id"]), "parent": uid(L, p["parent"])}
                         for p in d["provisions"] if p["level"] == level])

    run("""UNWIND $rows AS r
           MATCH (d:Provision {uid:r.defined_in})
           MERGE (t:Term:LawNode {uid:r.uid}) SET t.name=r.name, t.definition=r.definition, t.law=$law
           MERGE (t)-[:DEFINED_IN]->(d)
           FOREACH (_ IN CASE WHEN r.is_party THEN [1] ELSE [] END | SET t:Actor, t.category='хөдөлмөрийн харилцааны тал')""",
        law=L, rows=[{**t, "uid": uid(L, t["id"]), "defined_in": uid(L, t["defined_in"])} for t in d["terms"]])

    run("""UNWIND $rows AS r MERGE (a:Actor {name:r.name}) SET a.category=r.category""", rows=d["actors"])

    run("""UNWIND $rows AS r
           MATCH (p:Provision {uid:r.src})
           MERGE (e:ExternalLaw {name:r.name})
           MERGE (p)-[:CITES]->(e)""",
        rows=[{"name": e["name"], "src": uid(L, s)} for e in d["external_laws"] for s in e["cited_by"]])

    run("""UNWIND $rows AS r
           MATCH (p:Provision {uid:r.src}), (t:LawNode {uid:r.dst})
           MERGE (p)-[:REFERS_TO]->(t)""",
        rows=[{"src": uid(L, r["from"]), "dst": uid(L, r["to"])} for r in d["references"]])

    run("""UNWIND $rows AS r
           MATCH (p:Provision {uid:r.src}), (t:Term {uid:r.dst})
           MERGE (p)-[:MENTIONS]->(t)""",
        rows=[{"src": uid(L, m["from"]), "dst": uid(L, m["to"])} for m in d["mentions"] if m["to"].startswith("term:")])
    run("""UNWIND $rows AS r
           MATCH (p:Provision {uid:r.src}), (a:Actor {name:r.name})
           MERGE (p)-[:MENTIONS]->(a)""",
        rows=[{"src": uid(L, m["from"]), "name": m["to"].removeprefix("actor:")}
              for m in d["mentions"] if m["to"].startswith("actor:")])

    run("""UNWIND $rows AS r
           MATCH (n:LawNode {uid:r.target})
           MERGE (a:AmendingLaw {date:r.date})
           MERGE (n)-[x:AMENDED_BY {type:r.type}]->(a)""",
        rows=[{**a, "target": uid(L, a["target"])} for a in d["amendments"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json", type=Path)
    ap.add_argument("--reset", action="store_true", help="Энэ хуулийн өмнөх өгөгдлийг устгаад дахин ачаална")
    args = ap.parse_args()
    load_dotenv(Path(__file__).parent / ".env")
    d = json.loads(args.json.read_text(encoding="utf-8"))

    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    with driver.session() as s:
        for q in SCHEMA:
            s.run(q)
        if args.reset:
            s.run("MATCH (n:LawNode {law:$law}) DETACH DELETE n", law=d["law"]["id"])
            s.run("MATCH (l:Law {id:$law}) DETACH DELETE l", law=d["law"]["id"])
        load(s, d)
        for rec in s.run("MATCH (n) UNWIND labels(n) AS l WITH l WHERE l <> 'LawNode' RETURN l, count(*) AS c ORDER BY c DESC"):
            print(f"  {rec['l']:14s} {rec['c']}")
        for rec in s.run("MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c ORDER BY c DESC"):
            print(f"  -[{rec['t']}]-> {rec['c']}")
    driver.close()


if __name__ == "__main__":
    main()
