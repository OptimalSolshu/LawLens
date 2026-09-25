"""GraphStore over Neo4j. Every query is parameterised; ids come from validated
path parameters and are only ever passed as $parameters."""
import json

from .driver import get_driver
from .store import number_key

ART = "a{.article_id, .law_id, .number, .parent_number, .title, .text}"
REF_RETURN = """RETURN s.article_id AS from_article_id, s.law_id AS from_law_id, s.number AS from_number,
       r.to_law_id AS to_law_id, r.to_number AS to_number, r.to_article_id AS to_article_id,
       r.raw_text AS raw_text, r.matched_name AS matched_name, r.uses_old_name AS uses_old_name,
       r.target_missing AS target_missing, r.current_number AS current_number,
       r.method AS method, r.confidence AS confidence"""
# Upper bound on relationships per impact hop: PART_OF steps up to the cited article
# (numbers nest at most "12.3.1.2" deep) plus the one REFERS_TO back.
PATH_STEPS_PER_HOP = 5
LAW_FIELDS =("law_id", "name", "former_names", "short_names", "adopted_date", "source_url", "text_available")


class Neo4jStore:
    backend = "neo4j"

    def __init__(self, dataset: str = "real"):
        self.dataset = dataset
        self.driver = get_driver()

    def _q(self, query: str, **params) -> list[dict]:
        with self.driver.session() as s:
            return [r.data() for r in s.run(query, **params)]

    # ---- laws / articles -------------------------------------------------------
    def _law(self, rec: dict) -> dict:
        law = {k: rec["l"].get(k) for k in LAW_FIELDS}
        law["former_names"] = law["former_names"] or []
        law["short_names"] = law["short_names"] or []
        law["text_available"] = law["text_available"] is not False
        law["article_count"] = rec["n"]
        return law

    def laws(self):
        return [self._law(r) for r in self._q(
            "MATCH (l:Law) OPTIONAL MATCH (l)-[:HAS_ARTICLE]->(a) RETURN l{.*} AS l, count(a) AS n ORDER BY l.law_id")]

    def law(self, law_id):
        rows = self._q("MATCH (l:Law {law_id: $id}) OPTIONAL MATCH (l)-[:HAS_ARTICLE]->(a) "
                       "RETURN l{.*} AS l, count(a) AS n", id=law_id)
        return self._law(rows[0]) if rows else None

    def articles(self, law_id):
        rows = [r["a"] for r in self._q(f"MATCH (:Law {{law_id: $id}})-[:HAS_ARTICLE]->(a) RETURN {ART} AS a", id=law_id)]
        return sorted(rows, key=lambda a: number_key(a["number"]))

    def article(self, article_id):
        rows = self._q(f"MATCH (a:Article {{article_id: $id}}) RETURN {ART} AS a", id=article_id)
        return rows[0]["a"] if rows else None

    def articles_by_id(self, ids):
        rows = self._q(f"MATCH (a:Article) WHERE a.article_id IN $ids RETURN {ART} AS a", ids=list(ids))
        return {r["a"]["article_id"]: r["a"] for r in rows}

    def all_articles(self):
        return [r["a"] for r in self._q(f"MATCH (a:Article) RETURN {ART} AS a")]

    # ---- references --------------------------------------------------------------
    def refs_to(self, law_id, article_ids, missing_prefixes, law_level):
        return self._q(f"""
            CALL () {{
              MATCH (s:Article)-[r:REFERS_TO]->(t:Article) WHERE t.article_id IN $ids RETURN s, r
              UNION ALL
              MATCH (s:Article)-[r:REFERS_TO]->(:Law {{law_id: $law}})
              WHERE (r.to_number IS NULL AND $law_level)
                 OR (r.to_number IS NOT NULL AND r.target_missing
                     AND ($prefixes IS NULL OR any(p IN $prefixes WHERE r.to_number = p OR r.to_number STARTS WITH p + '.')))
              RETURN s, r
            }}
            {REF_RETURN}""", ids=list(article_ids), law=law_id, law_level=law_level, prefixes=missing_prefixes)

    def indirect_refs(self, frontier_ids, seed_ids, max_depth):
        """One traversal: a hop is (up PART_OF to a containing article/part)* then back along
        one REFERS_TO to the citing provision. Depth = 1 + REFERS_TO hops on the shortest
        path; then the (ref, via) candidates are matched against the previous depth."""
        if max_depth < 2 or not frontier_ids:
            return []
        hops = int(max_depth) - 1
        return self._q(f"""
            MATCH (f:Article WHERE f.article_id IN $frontier)
                  ((x:Article)-[e:PART_OF|REFERS_TO]-(y:Article)
                   WHERE (type(e) = 'PART_OF' AND startNode(e) = x)
                      OR (type(e) = 'REFERS_TO' AND endNode(e) = x AND NOT y.article_id IN $seeds)
                  ){{1,{hops * PATH_STEPS_PER_HOP}}}
                  (b:Article)
            WHERE type(last(e)) = 'REFERS_TO' AND NOT b.article_id IN $frontier
            WITH b, min(size([h IN e WHERE type(h) = 'REFERS_TO'])) AS refs_hops
            WHERE refs_hops <= $hops
            WITH collect({{id: b.article_id, depth: refs_hops + 1}}) AS reached
            UNWIND reached AS hit
            WITH hit, CASE hit.depth WHEN 2 THEN $frontier
                      ELSE [p IN reached WHERE p.depth = hit.depth - 1 | p.id] END AS previous
            MATCH (s:Article {{article_id: hit.id}})-[r:REFERS_TO]->(t:Article)<-[:PART_OF*0..]-(v:Article)
            WHERE v.article_id IN previous
            {REF_RETURN}, v.article_id AS via_article_id, hit.depth AS depth""",
            frontier=list(frontier_ids), seeds=list(seed_ids), hops=hops)

    def refs_from(self, article_ids):
        return self._q(f"MATCH (s:Article)-[r:REFERS_TO]->() WHERE s.article_id IN $ids {REF_RETURN}",
                       ids=list(article_ids))

    # ---- suggestions ---------------------------------------------------------------
    def similar(self, article_ids):
        return self._q("""MATCH (a:Article)-[r:SIMILAR_TO]-(:Article) WHERE a.article_id IN $ids
                          WITH DISTINCT r
                          RETURN startNode(r).article_id AS a_article_id, endNode(r).article_id AS b_article_id,
                                 r.score AS score, r.model AS model""", ids=list(article_ids))

    def relations(self, article_ids):
        return self._q("""MATCH (a:Article)-[r:CONFLICTS_WITH|OVERLAPS_WITH|CONSISTENT_WITH]-(:Article)
                          WHERE a.article_id IN $ids WITH DISTINCT r
                          RETURN startNode(r).article_id AS a_article_id, endNode(r).article_id AS b_article_id,
                                 r.kind AS kind, r.confidence AS confidence, r.explanation AS explanation,
                                 r.model AS model""", ids=list(article_ids))

    def intl_links(self, article_ids):
        rows = self._q("""MATCH (a:Article)-[r:RELEVANT_SOURCE]->(s:Source) WHERE a.article_id IN $ids
                          RETURN s{.*} AS s, a.article_id AS article_id, r.relevance AS relevance,
                                 r.explanation AS explanation, r.model AS model""", ids=list(article_ids))
        return [{**r["s"], "article_id": r["article_id"], "relevance": r["relevance"],
                 "explanation": r["explanation"], "model": r["model"]} for r in rows]

    def intl_sources(self):
        return {r["s"]["source_id"]: r["s"] for r in self._q("MATCH (s:Source) RETURN s{.*} AS s")}

    def amendments(self, article_ids):
        return [r["s"] for r in self._q(
            "MATCH (s:Suggestion) WHERE s.article_id IN $ids RETURN s{.*} AS s ORDER BY s.article_id",
            ids=list(article_ids))]

    # ---- drafts -----------------------------------------------------------------------
    @staticmethod
    def _draft(d: dict) -> dict:
        d = dict(d)
        d["operations"] = json.loads(d.pop("operations_json", None) or "[]")
        d.setdefault("new_name", None)
        d["cosubmitted_titles"] = d.get("cosubmitted_titles") or []
        return d

    def drafts(self):
        return [self._draft(r["d"]) for r in self._q("MATCH (d:Draft) RETURN d{.*} AS d ORDER BY d.draft_id")]

    def draft(self, draft_id):
        rows = self._q("MATCH (d:Draft {draft_id: $id}) RETURN d{.*} AS d", id=draft_id)
        return self._draft(rows[0]["d"]) if rows else None
