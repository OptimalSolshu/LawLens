"""Store parity: the same service assertions against Neo4j.

Runs only when NEO4J_TEST_URI (+ NEO4J_TEST_PASSWORD) point at an EMPTY, disposable
Neo4j 5 database: the test loads the [ЖИШЭЭ] sample dataset with --reset semantics.
"""
import os

import pytest

from app import config
from app.graph import driver as driver_mod
from app.graph.memory import MemoryStore
from app.services import draft_service, impact_service, law_service, search_service
from app.schemas import ImpactRequest

from .conftest import LABOR
from .test_services import check_drafts, check_graph, check_impact

URI = os.getenv("NEO4J_TEST_URI")
pytestmark = pytest.mark.skipif(not URI, reason="set NEO4J_TEST_URI to run Neo4j tests")


@pytest.fixture(scope="module")
def neo(request):
    mp = pytest.MonkeyPatch()
    mp.setattr(config, "NEO4J_URI", URI)
    mp.setattr(config, "NEO4J_USER", os.getenv("NEO4J_TEST_USER", "neo4j"))
    mp.setattr(config, "NEO4J_PASSWORD", os.getenv("NEO4J_TEST_PASSWORD", ""))
    driver_mod.get_driver.cache_clear()
    from app.graph.loader import load
    from app.graph.neo4j_store import Neo4jStore

    load(config.sample_dir(), reset=True)
    yield Neo4jStore(dataset="sample")
    driver_mod.get_driver().close()
    driver_mod.get_driver.cache_clear()
    mp.undo()


def test_graph_queries(neo):
    check_graph(neo)


def test_impact(neo):
    check_impact(neo)


def test_drafts(neo):
    check_drafts(neo)


@pytest.mark.parametrize("call", [
    lambda s: law_service.list_laws(s),
    lambda s: law_service.get_law(s, LABOR),
    lambda s: law_service.law_connections(s, LABOR),
    lambda s: law_service.article_connections(s, f"{LABOR}:80"),
    lambda s: law_service.article_connections(s, f"{LABOR}:104"),
    lambda s: impact_service.compute(s, ImpactRequest(article_id=f"{LABOR}:80.1", depth=3)),
    lambda s: impact_service.compute(s, ImpactRequest(law_id=LABOR, new_name="[ЖИШЭЭ] X", depth=2)),
    lambda s: draft_service.detail(s, "draft-sample-labor-001"),
    lambda s: search_service.search(s, "ажлын цаг"),
])
def test_same_answers_as_memory_store(neo, call):
    mem = MemoryStore(config.sample_dir(), dataset="sample")
    dump = lambda x: [i.model_dump() for i in x] if isinstance(x, list) else x.model_dump()
    assert dump(call(neo)) == dump(call(mem))


def test_vector_index_populated(neo):
    rows = neo._q("MATCH (a:Article) WHERE a.embedding IS NOT NULL RETURN count(a) AS n, "
                  "collect(DISTINCT a.embedding_model) AS m")
    assert rows[0]["n"] > 0 and rows[0]["m"] == ["demo-ngram-v1"]
    hits = neo._q("""MATCH (a:Article {article_id: $id})
                     CALL db.index.vector.queryNodes('article_embedding', 3, a.embedding) YIELD node, score
                     RETURN node.article_id AS id, score""", id=f"{LABOR}:80.1")
    assert hits[0]["id"] == f"{LABOR}:80.1"
