"""MOCK=1: every recorded fixture replays to the identical response."""
import pytest

from app import fixtures
from app.mock.record import REQUESTS, replay

from .conftest import LABOR


@pytest.mark.parametrize("name", sorted(REQUESTS))
def test_fixture_replays(client, name):
    r = replay(client, name)
    assert r.status_code == 200, r.text
    assert r.headers["X-LawLens-Sample"] == "true"
    assert r.json() == fixtures.load(name)["response"]


@pytest.mark.parametrize("path", [
    f"/api/laws/{LABOR}", f"/api/laws/{LABOR}/articles", f"/api/laws/{LABOR}/connections",
    f"/api/articles/{LABOR}:80", f"/api/articles/{LABOR}:80/connections", f"/api/articles/{LABOR}:80.1/impact",
    f"/api/articles/{LABOR}:6/international", "/api/drafts", "/api/drafts/draft-sample-labor-001",
    "/api/drafts/draft-sample-labor-001/gap", "/api/drafts/draft-sample-labor-001/gaps", "/api/search?q=80",
])
def test_every_endpoint_answers(client, path):
    assert client.get(path).status_code == 200


def test_health_reports_mock(client):
    assert client.get("/api/health").json() == {"status": "ok", "mock": True, "dataset": "sample", "graph": "memory"}


def test_laws_search_matches_former_name(client):
    names = [l["name"] for l in client.get("/api/laws", params={"q": "хамгааллын"}).json()]
    assert names == ["Хөдөлмөрийн аюулгүй байдал, эрүүл ахуйн тухай хууль"]


@pytest.mark.parametrize("body", [{"article_id": f"{LABOR}:80.1", "depth": 4}, {"depth": 1},
                                  {"article_id": f"{LABOR}:80.1", "new_number": "abc"}])
def test_impact_rejects_bad_request(client, body):
    assert client.post("/api/impact", json=body).status_code == 422


@pytest.mark.parametrize("path,status", [
    ("/api/articles/not an id", 422), ("/api/articles/x:1'--", 422), ("/api/laws/DROP", 422),
    ("/api/articles/nope:1", 404), ("/api/laws/nope", 404), ("/api/drafts/nope", 404),
    (f"/api/articles/{LABOR}:6/amendment", 404),
])
def test_input_validation_and_404(client, path, status):
    assert client.get(path).status_code == status


def test_every_item_is_cited_and_typed(client):
    body = client.get(f"/api/articles/{LABOR}:80").json()
    items = [i for k in ("incoming", "outgoing", "former_name_refs", "missing_target_refs")
             for g in body[k] for i in g["items"]] + body["similar"] + body["conflicts"] + body["overlaps"]
    assert items
    for i in items:
        assert i["law_name"] and i["source_url"].startswith("https://") and i["number"]
        assert i["type"] in ("fact", "suggestion")
        if i["type"] == "fact":
            assert i["confidence"] == 1.0
        else:
            assert i["model"] and 0 <= i["confidence"] <= 1
    facts = {i["type"] for k in ("incoming", "outgoing") for g in body[k] for i in g["items"]}
    assert facts == {"fact"}
    assert {i["type"] for i in body["similar"] + body["conflicts"]} == {"suggestion"}
