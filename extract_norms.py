"""Claude-оор заалт бүрээс хэм хэмжээ (хэн → ямар эрх/үүрэгтэй → юу хийх → хэний өмнө) гаргаж,
ишлэл бүрийн утгын үүргийг (үл хамаарах, нөхцөл, журам, хариуцлага ...) тодорхойлж графд нэмнэ.

Үүсгэх зүйлс:
    (:Actor|:Term)-[:HAS_RIGHT|HAS_DUTY|IS_PROHIBITED|HAS_POWER|IS_LIABLE]->(:Norm)
    (:Norm)-[:TOWARDS]->(:Actor)          // хэний өмнө / хэнд чиглэсэн
    (:Norm)-[:STATED_IN]->(:Provision)
    (:Provision)-[:REFERS_TO {role}]->()  // одоо байгаа ишлэлд утгын үүрэг нэмнэ

Үр дүнг data/<law>.norms.json-д зүйл тус бүрээр кэшлэх тул дахин ажиллуулахад зөвхөн дутуу зүйлсийг API-аар дуудна.

Хэрэглээ:
    export ANTHROPIC_API_KEY=...          # эсвэл `ant auth login`
    python extract_norms.py --law labor-2021 [--articles 42,43] [--workers 4]
"""
import argparse
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from neo4j import GraphDatabase

MODEL = "claude-opus-5"

NORM_TYPES = {
    "эрх": "HAS_RIGHT",
    "үүрэг": "HAS_DUTY",
    "хориглол": "IS_PROHIBITED",
    "бүрэн эрх": "HAS_POWER",
    "хариуцлага": "IS_LIABLE",
}
REF_ROLES = ["үл хамаарах", "нөхцөл", "журам", "хариуцлага", "тодорхойлолт", "хамрах хүрээ", "дагаж мөрдөх", "бусад"]

SCHEMA = {
    "type": "object",
    "properties": {
        "norms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "provision": {"type": "string", "description": "Заалтын дугаар, жишээ 43.2.1"},
                    "subject": {"type": "string", "description": "Эрх/үүргийн эзэн оролцогч"},
                    "type": {"type": "string", "enum": list(NORM_TYPES)},
                    "action": {"type": "string", "description": "Юу хийх/хийхгүй байх, товч нэр үгийн хэллэгээр"},
                    "towards": {"type": ["string", "null"], "description": "Хэний өмнө/хэнд чиглэсэн оролцогч"},
                    "condition": {"type": ["string", "null"], "description": "Хэрэгжих нөхцөл, байхгүй бол null"},
                },
                "required": ["provision", "subject", "type", "action", "towards", "condition"],
                "additionalProperties": False,
            },
        },
        "references": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "role": {"type": "string", "enum": REF_ROLES},
                },
                "required": ["from", "to", "role"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["norms", "references"],
    "additionalProperties": False,
}

SYSTEM = """Та Монгол Улсын хөдөлмөрийн эрх зүйн шинжээч. Хуулийн нэг зүйлийн заалтуудаас хэм хэмжээний бүтэц гаргана.

norms: заалт бүрээс эрх, үүрэг, хориглол, бүрэн эрх (төрийн байгууллагын), хариуцлагыг гарга.
- Жагсаалтын оршил ("Ажил олгогч дараах үүрэгтэй:") нь subject, type-ийг өгнө; хэм хэмжээг доорх дэд заалт бүрт тусад нь гарга, оршилд биш.
- subject, towards-д аль болох өгөгдсөн оролцогчдын нэрийг яг тэр хэлбэрээр нь ашигла. Жагсаалтад байхгүй бол нэрлэн тийн ялгалгүй үндсэн хэлбэрээр бич.
- action нь 3-12 үгтэй, заалтын утгыг хадгалсан товч хэллэг байна.
- Тодорхойлолт, зорилго, хамрах хүрээ зэрэг хэм хэмжээ биш заалтыг алгас.

references: өгөгдсөн ишлэл бүрт ишилж буй заалт ишлэгдэж буй заалттай ямар утгын харилцаатайг сонго."""


def fetch_articles(session, law, only):
    rows = session.run("""
        MATCH (a:Article {law:$law})-[:HAS_PROVISION*]->(p:Provision)
        WHERE p.status <> 'хүчингүй' AND ($only IS NULL OR a.number IN $only)
        OPTIONAL MATCH (p)-[:REFERS_TO]->(t)
        WITH a, p, collect(CASE WHEN t IS NULL THEN NULL
                                ELSE {to: toString(t.number), text: left(coalesce(t.text, t.title, ''), 300)} END) AS refs
        ORDER BY a.number, p.uid
        RETURN a.uid AS uid, a.number AS number, a.title AS title,
               collect({number: p.number, text: p.text, refs: refs}) AS provisions""", law=law, only=only).data()
    return rows


def prompt(article, actors):
    lines = [f"{p['number']}. {p['text']}" for p in article["provisions"]]
    refs = [f"- {p['number']} → {r['to']}: {r['text']}" for p in article["provisions"] for r in p["refs"]]
    return (f"Оролцогчид: {', '.join(actors)}\n\n"
            f"<article number=\"{article['number']}\" title=\"{article['title']}\">\n" + "\n".join(lines) + "\n</article>\n\n"
            + ("Ишлэлүүд (ишлэгдэж буй заалтын текст):\n" + "\n".join(refs) if refs else "Ишлэл байхгүй."))


def extract(client, article, actors):
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt(article, actors)}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"зүйл {article['number']}: refusal ({response.stop_details})")
    if response.stop_reason == "max_tokens":
        raise RuntimeError(f"зүйл {article['number']}: max_tokens хүрсэн")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text), response.usage


def load(session, law, results):
    norms, refs = [], []
    for art_uid, r in results.items():
        for i, n in enumerate(r["norms"]):
            norms.append({**n, "uid": f"{art_uid}:norm{i}", "rel": NORM_TYPES[n["type"]],
                          "provision_uid": f"{law}:{n['provision']}"})
        refs += [{**x, "src": f"{law}:{x['from']}"} for x in r["references"]]

    session.run("MATCH (n:Norm {law:$law}) DETACH DELETE n", law=law)
    for rel in NORM_TYPES.values():
        # Нэр томьёо (:Term:Actor) болон бусад оролцогчийг нэрээр нь холбоно; байхгүй бол шинэ Actor үүсгэнэ
        session.run(f"""
            UNWIND $rows AS r
            MATCH (p:Provision {{uid:r.provision_uid}})
            CREATE (n:Norm:LawNode {{uid:r.uid, law:$law, type:r.type, action:r.action, condition:r.condition,
                                     subject:r.subject, towards:r.towards, provision:r.provision}})
            MERGE (n)-[:STATED_IN]->(p)
            WITH r, n
            OPTIONAL MATCH (existing:Actor {{name:r.subject}})
            WITH r, n, head(collect(existing)) AS found
            FOREACH (_ IN CASE WHEN found IS NULL THEN [1] ELSE [] END |
                MERGE (new:Actor {{name:r.subject}}) ON CREATE SET new.category='LLM-ээр илрүүлсэн'
                MERGE (new)-[:{rel}]->(n))
            FOREACH (a IN CASE WHEN found IS NULL THEN [] ELSE [found] END | MERGE (a)-[:{rel}]->(n))""",
                    rows=[n for n in norms if n["rel"] == rel], law=law)
    session.run("""
        UNWIND $rows AS r
        MATCH (n:Norm {uid:r.uid})
        OPTIONAL MATCH (existing:Actor {name:r.towards})
        WITH r, n, head(collect(existing)) AS found
        FOREACH (_ IN CASE WHEN found IS NULL THEN [1] ELSE [] END |
            MERGE (new:Actor {name:r.towards}) ON CREATE SET new.category='LLM-ээр илрүүлсэн'
            MERGE (n)-[:TOWARDS]->(new))
        FOREACH (a IN CASE WHEN found IS NULL THEN [] ELSE [found] END | MERGE (n)-[:TOWARDS]->(a))""",
                rows=[n for n in norms if n["towards"]])
    session.run("""
        UNWIND $rows AS r
        MATCH (p:Provision {uid:r.src})-[x:REFERS_TO]->(t)
        WHERE toString(t.number) = r.to
        SET x.role = r.role""", rows=refs)
    return len(norms), len(refs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--law", default="labor-2021")
    ap.add_argument("--articles", help="Зөвхөн эдгээр зүйлийг (таслалаар), жишээ 42,43")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true", help="API дуудахгүй, эхний зүйлийн prompt-ыг хэвлэнэ")
    args = ap.parse_args()
    load_dotenv(Path(__file__).parent / ".env")
    only = [int(x) for x in args.articles.split(",")] if args.articles else None
    cache_path = Path(__file__).parent / "data" / f"{args.law}.norms.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    with driver.session() as s:
        articles = fetch_articles(s, args.law, only)
        actors = [r["name"] for r in s.run("MATCH (a:Actor) WHERE a.category <> 'LLM-ээр илрүүлсэн' RETURN a.name AS name ORDER BY name")]
    if args.dry_run:
        print(SYSTEM, "\n\n", prompt(articles[0], actors), sep="")
        return
    todo = [a for a in articles if a["uid"] not in cache]
    print(f"  {len(articles)} зүйл, үүнээс {len(todo)}-г {MODEL}-оор задлана")

    if todo:
        client = anthropic.Anthropic()
        lock, tokens = threading.Lock(), {"in": 0, "out": 0}
        with ThreadPoolExecutor(args.workers) as pool:
            futures = {pool.submit(extract, client, a, actors): a for a in todo}
            for f in as_completed(futures):
                a = futures[f]
                try:
                    data, usage = f.result()
                except (anthropic.APIError, RuntimeError, json.JSONDecodeError) as e:
                    print(f"  ! зүйл {a['number']}: {e}")
                    continue
                with lock:
                    cache[a["uid"]] = data
                    tokens["in"] += usage.input_tokens
                    tokens["out"] += usage.output_tokens
                    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"  зүйл {a['number']:>3}: {len(data['norms'])} хэм хэмжээ, {len(data['references'])} ишлэл")
        print(f"  токен: оролт {tokens['in']:,} · гаралт {tokens['out']:,}")

    with driver.session() as s:
        n, r = load(s, args.law, {a["uid"]: cache[a["uid"]] for a in articles if a["uid"] in cache})
    driver.close()
    print(f"  Norm {n} · ишлэлийн үүрэг {r}")


if __name__ == "__main__":
    main()
