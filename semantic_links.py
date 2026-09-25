"""Утгын (семантик) холбоос: заалт бүрийг embedding болгож, утгаар ойр заалт, зүйл, сэдвийг холбоно.

Үүсгэх зүйлс:
    (:Provision {embedding})                     + вектор индекс `provision_embedding`
    (:Provision)-[:SIMILAR_TO {score}]->(:Provision)   // өөр зүйлд байгаа, утгаар ойр заалт
    (:Article)-[:RELATED_TO {score}]->(:Article)       // агуулгаар ойр зүйлс
    (:Provision)-[:ABOUT]->(:Topic)<-[:ABOUT]-(:Article) // кластерчилсан сэдэв

Хэрэглээ:
    python semantic_links.py --law labor-2021 [--k 3] [--min-score 0.93] [--topics 30]
"""
import argparse
import os
from collections import Counter
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from fastembed import TextEmbedding
from neo4j import GraphDatabase

MODEL = "intfloat/multilingual-e5-large"
DIM = 1024


def fetch(session, law):
    # Заалт (хэсэг) нь ихэвчлэн богино тул эцэг хэсэг, зүйлийн гарчгийг контекст болгож нэмнэ
    return session.run("""
        MATCH (a:Article {law:$law})-[:HAS_PROVISION*]->(p:Provision)
        WHERE p.status <> 'хүчингүй' AND size(p.text) > 15
        OPTIONAL MATCH (parent:Provision)-[:HAS_PROVISION]->(p)
        RETURN p.uid AS uid, p.number AS number, a.uid AS article, a.title AS article_title,
               p.text AS text, parent.text AS parent_text
        ORDER BY p.uid""", law=law).data()


def embed(rows, cache):
    # Ижил заалтууд бол өмнө тооцсон векторыг дахин ашиглана (CPU дээр хэдэн минут зарцуулдаг)
    uids = [r["uid"] for r in rows]
    if cache.exists():
        c = np.load(cache, allow_pickle=False)
        if list(c["uids"]) == uids and c["model"] == MODEL:
            return c["vecs"]
    passages = []
    for r in rows:
        ctx = f"{r['article_title']}. " + (f"{r['parent_text']} " if r["parent_text"] else "")
        passages.append("passage: " + ctx + r["text"])
    model = TextEmbedding(MODEL)
    vecs = np.array(list(model.embed(passages, batch_size=16)), dtype=np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    np.savez(cache, uids=np.array(uids), vecs=vecs, model=MODEL)
    return vecs


def similar_pairs(rows, vecs, k, min_score):
    sims = vecs @ vecs.T
    articles = np.array([r["article"] for r in rows])
    pairs = {}
    for i in range(len(rows)):
        # Нэг зүйлийн доторх заалтууд бүтцээрээ аль хэдийн холбоотой тул зөвхөн өөр зүйлийг хайна
        cand = np.where(articles != articles[i])[0]
        top = cand[np.argsort(-sims[i, cand])[:k]]
        for j in top:
            if sims[i, j] >= min_score:
                a, b = sorted((i, j))
                pairs[(a, b)] = float(sims[i, j])
    return [{"a": rows[a]["uid"], "b": rows[b]["uid"], "score": round(s, 4)} for (a, b), s in pairs.items()]


def article_pairs(rows, vecs, k, min_score):
    by_art = {}
    for r, v in zip(rows, vecs):
        by_art.setdefault(r["article"], []).append(v)
    uids = list(by_art)
    m = np.array([np.mean(by_art[u], axis=0) for u in uids])
    m /= np.linalg.norm(m, axis=1, keepdims=True)
    sims = m @ m.T
    np.fill_diagonal(sims, -1)
    pairs = {}
    for i in range(len(uids)):
        for j in np.argsort(-sims[i])[:k]:
            if sims[i, j] >= min_score:
                a, b = sorted((i, j))
                pairs[(a, b)] = float(sims[i, j])
    return [{"a": uids[a], "b": uids[b], "score": round(s, 4)} for (a, b), s in pairs.items()]


def kmeans(vecs, n, iters=50, seed=0):
    # k-means++ эхлэл, косинус зай (векторууд нормчлогдсон)
    rng = np.random.default_rng(seed)
    centers = [vecs[rng.integers(len(vecs))]]
    for _ in range(1, n):
        d = np.clip(1 - np.max(vecs @ np.array(centers).T, axis=1), 0, None)
        centers.append(vecs[rng.choice(len(vecs), p=d / d.sum())])
    centers = np.array(centers)
    for _ in range(iters):
        labels = np.argmax(vecs @ centers.T, axis=1)
        new = np.array([vecs[labels == c].mean(axis=0) if np.any(labels == c) else centers[c] for c in range(n)])
        new /= np.linalg.norm(new, axis=1, keepdims=True)
        if np.allclose(new, centers):
            break
        centers = new
    return labels


def topics(rows, vecs, n, law):
    labels = kmeans(vecs, n)
    out, links = [], []
    for c in range(n):
        idx = np.where(labels == c)[0]
        if not len(idx):
            continue
        # Сэдвийн нэр = кластерт хамгийн их орсон зүйлсийн гарчиг
        titles = Counter(rows[i]["article_title"] for i in idx).most_common(3)
        tid = f"{law}:topic{c}"
        out.append({"uid": tid, "name": titles[0][0], "keywords": [t for t, _ in titles], "size": int(len(idx))})
        links += [{"p": rows[i]["uid"], "t": tid} for i in idx]
    return out, links


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--law", default="labor-2021")
    ap.add_argument("--k", type=int, default=3, help="Заалт бүрт хамгийн ойр хэдэн заалтыг холбох")
    ap.add_argument("--min-score", type=float, default=0.93, help="SIMILAR_TO үүсгэх косинус ижил төстэй байдлын босго")
    ap.add_argument("--article-min-score", type=float, default=0.93)
    ap.add_argument("--topics", type=int, default=30)
    args = ap.parse_args()
    load_dotenv(Path(__file__).parent / ".env")

    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    with driver.session() as s:
        rows = fetch(s, args.law)
        print(f"  {len(rows)} заалтыг embedding болгож байна ({MODEL})...")
        vecs = embed(rows, Path(__file__).parent / "data" / f"{args.law}.emb.npz")

        s.run("""MATCH (n:LawNode {law:$law})-[r:SIMILAR_TO|RELATED_TO|ABOUT]-() DELETE r""", law=args.law)
        s.run("MATCH (t:Topic {law:$law}) DETACH DELETE t", law=args.law)
        s.run(f"""CREATE VECTOR INDEX provision_embedding IF NOT EXISTS FOR (p:Provision) ON (p.embedding)
                  OPTIONS {{indexConfig: {{`vector.dimensions`: {DIM}, `vector.similarity_function`: 'cosine'}}}}""")
        s.run("""UNWIND $rows AS r MATCH (p:Provision {uid:r.uid}) CALL db.create.setNodeVectorProperty(p, 'embedding', r.v)""",
              rows=[{"uid": r["uid"], "v": v.tolist()} for r, v in zip(rows, vecs)])

        sim = similar_pairs(rows, vecs, args.k, args.min_score)
        s.run("""UNWIND $rows AS r MATCH (a:Provision {uid:r.a}), (b:Provision {uid:r.b})
                 MERGE (a)-[x:SIMILAR_TO]->(b) SET x.score=r.score""", rows=sim)

        rel = article_pairs(rows, vecs, 3, args.article_min_score)
        s.run("""UNWIND $rows AS r MATCH (a:Article {uid:r.a}), (b:Article {uid:r.b})
                 MERGE (a)-[x:RELATED_TO]->(b) SET x.score=r.score""", rows=rel)

        tops, links = topics(rows, vecs, args.topics, args.law)
        s.run("""UNWIND $rows AS r MERGE (t:Topic:LawNode {uid:r.uid})
                 SET t.name=r.name, t.keywords=r.keywords, t.size=r.size, t.law=$law""", rows=tops, law=args.law)
        s.run("""UNWIND $rows AS r MATCH (p:Provision {uid:r.p}), (t:Topic {uid:r.t}) MERGE (p)-[:ABOUT]->(t)""", rows=links)
        s.run("""MATCH (a:Article {law:$law})-[:HAS_PROVISION*]->(:Provision)-[:ABOUT]->(t:Topic)
                 WITH a, t, count(*) AS n WHERE n >= 2 MERGE (a)-[x:ABOUT]->(t) SET x.weight=n""", law=args.law)

        print(f"  SIMILAR_TO {len(sim)} · RELATED_TO {len(rel)} · Topic {len(tops)} · ABOUT {len(links)}")
    driver.close()


if __name__ == "__main__":
    main()
