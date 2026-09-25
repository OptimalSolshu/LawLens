"""Graph queries, impact depth, draft gap, search and CSV export on the [ЖИШЭЭ] sample graph.

The same assertions run against Neo4j in test_neo4j.py (store parity).
"""
import csv
import io

import pytest

from app.schemas import ImpactRequest
from app.services import draft_service, export_service, impact_service, law_service, search_service

from .conftest import HED, LABOR, MINWAGE, ND, OSH, ZORCHIL


def ids(groups):
    return sorted(i.article_id or f"{i.law_id}:{i.number}" for g in groups for i in g.items)


def check_graph(store):
    conn = law_service.article_connections(store, f"{LABOR}:80")
    # reverse references (who cites 80.x), including a citation of a number that no longer exists
    assert ids(conn.incoming) == sorted([f"{LABOR}:91.1", f"{OSH}:12.2", f"{ZORCHIL}:6.1", f"{ZORCHIL}:6.4"])
    # forward references out of 80.x
    assert ids(conn.outgoing) == sorted([f"{OSH}:12.1", f"{OSH}:27.3"])
    # former name (Хөдөлмөр хамгааллын тухай хууль -> current OSH law)
    [old] = [i for g in conn.former_name_refs for i in g.items]
    assert old.law_id == OSH and old.matched_name == "Хөдөлмөр хамгааллын тухай хууль" and old.anchor_number == "80.3"
    # missing targets, both directions
    missing = {(i.law_id, i.number, i.article_id) for g in conn.missing_target_refs for i in g.items}
    assert missing == {(ZORCHIL, "6.4", f"{ZORCHIL}:6.4"), (OSH, "27.3", None)}
    assert conn.totals.incoming == 4 and conn.totals.missing_target_refs == 2
    # suggestions are separate and typed
    assert conn.similar[0].article_id == f"{OSH}:12.1" and conn.similar[0].type == "suggestion"
    assert conn.conflicts[0].model == "demo-llm" and conn.conflicts[0].confidence == 0.82

    # old number with a known new number (renumbering table)
    law = law_service.law_connections(store, LABOR)
    [renum] = [i for g in law.missing_target_refs for i in g.items if i.anchor_number == "131.1"]
    assert renum.current_number == "120.1" and renum.article_id == f"{ZORCHIL}:6.3"


def check_impact(store):
    r = impact_service.compute(store, ImpactRequest(article_id=f"{LABOR}:80.1", new_text="[ЖИШЭЭ] 38 цаг", depth=2))
    assert ids(r.depths[0].groups) == sorted([f"{LABOR}:80.2", f"{LABOR}:91.1", f"{OSH}:12.2", f"{ZORCHIL}:6.1"])
    # depth 2: via Зөрчил 6.1 and via 91.1 (cited as the whole article 91)
    assert ids(r.depths[1].groups) == sorted([f"{ND}:11.1", f"{ZORCHIL}:6.2"])
    assert (r.totals.direct, r.totals.indirect, r.totals.articles, r.totals.laws) == (4, 2, 6, 4)
    assert r.direct_impact == r.depths[0].groups
    assert r.note == "Энэ нь түр тооцоолол бөгөөд хуульд өөрчлөлт оруулахгүй."
    # a provision is listed once, at its smallest depth; the graph itself is not changed
    assert not set(ids(r.depths[0].groups)) & set(ids(r.depths[1].groups))
    assert law_service.get_article_or_404(store, f"{LABOR}:80.1")["text"].startswith("[ЖИШЭЭ] Ажилтны")

    d1 = impact_service.compute(store, ImpactRequest(article_id=f"{LABOR}:80.1", depth=1))
    assert len(d1.depths) == 1 and d1.totals.indirect == 0

    ren = impact_service.compute(store, ImpactRequest(law_id=HED, new_name="[ЖИШЭЭ] Шинэ нэр", depth=2))
    assert ids(ren.direct_impact) == sorted([f"{LABOR}:6.2", f"{ZORCHIL}:6.5"])
    assert all(i.flags.uses_old_name for g in ren.direct_impact for i in g.items)

    num = impact_service.compute(store, ImpactRequest(article_id=f"{LABOR}:80.1", new_number="81.1", depth=1))
    assert all(i.flags.target_missing for g in num.direct_impact for i in g.items)
    assert num.change.kind == "renumber"


def check_drafts(store):
    g = draft_service.gap(store, "draft-sample-labor-001")
    assert [x.law_id for x in g.covered] == [ZORCHIL]
    assert sorted(x.law_id for x in g.missing) == sorted([OSH, MINWAGE])
    assert [x.law_id for x in g.review] == [ND]
    assert g.found == 3
    g2 = draft_service.gap(store, "draft-sample-labor-002")  # rename bill
    assert [x.law_id for x in g2.covered] == [LABOR] and [x.law_id for x in g2.missing] == [ZORCHIL]
    d = draft_service.detail(store, "draft-sample-labor-001")
    assert [a.op.op for a in d.amended] == ["replace", "insert"]
    assert d.amended[0].article.number == "80.1" and d.cosubmitted[0].law_id == ZORCHIL


@pytest.fixture
def store(sample_store):
    return sample_store


def test_graph_queries(store):
    check_graph(store)


def test_impact_depths(store):
    check_impact(store)


def test_draft_gap(store):
    check_drafts(store)


@pytest.mark.parametrize("q,expect", [
    ("80.1", f"{LABOR}:80.1"),
    ("хөдөлмөрийн 104", f"{LABOR}:104"),
    ("ажлын цагийн", f"{ZORCHIL}:6.1"),
    ("цалингийн", f"{LABOR}:91.2"),
])
def test_search_articles(store, q, expect):
    assert expect in [a.article_id for a in search_service.search(store, q).articles]


def test_search_former_name(store):
    res = search_service.search(store, "ажил эрхлэлтийг")
    assert [l.law_id for l in res.laws] == [HED]


def test_csv_export(store):
    rows = export_service.rows(store, "connections", article_id=f"{LABOR}:80")
    text = export_service.to_csv(rows)
    assert text.startswith("﻿")
    parsed = list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))
    assert set(export_service.COLUMNS[:8]) <= set(parsed[0])
    rels = {r["relationship"] for r in parsed}
    assert {"Үүнийг иш татсан", "Үүнээс иш татсан", "Хуучин нэр / дугаар", "Заалт олдсонгүй",
            "Ижил асуудлыг зохицуулсан", "Болзошгүй зөрчил"} <= rels
    assert all(r["source_url"] for r in parsed)
    assert {r["label"] for r in parsed if r["type"] == "fact"} == {"Баримт"}
    assert any(r["label"] == "Санал, 82%" for r in parsed)
    gap = export_service.rows(store, "draft_gap", draft_id="draft-sample-labor-001", list_name="missing")
    assert {r["relationship"] for r in gap} == {"Орхигдсон"}


def test_csv_endpoint(client):
    r = client.get("/api/export", params={"kind": "impact", "article_id": f"{LABOR}:80.1", "depth": 2})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "Шууд нөлөөлөл" in r.text and "Дам нөлөөлөл" in r.text
    assert client.get("/api/export", params={"kind": "bogus"}).status_code == 422
    assert client.get("/api/export", params={"kind": "connections"}).status_code == 422
