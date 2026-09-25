import pytest
from fastapi.testclient import TestClient

from app import config, fixtures
from app.main import app

client = TestClient(app)
LAW = "zovshoorliin-tukhai-khuuli"
ART = f"{LAW}:15.1"


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setattr(config, "MOCK", True)


@pytest.mark.parametrize("method,path,fixture", [
    ("get", "/api/laws", "laws_list"),
    ("get", f"/api/laws/{LAW}", "law_detail"),
    ("get", f"/api/laws/{LAW}/connections", "law_connections"),
    ("get", f"/api/articles/{ART}", "article_connections"),
    ("get", "/api/drafts", "drafts_list"),
    ("get", "/api/drafts/draft-sample-001/gap", "draft_gap"),
    ("get", f"/api/articles/{ART}/international", "article_international"),
    ("get", f"/api/articles/{ART}/amendment", "article_amendment"),
])
def test_get_endpoints_serve_fixtures(method, path, fixture):
    r = getattr(client, method)(path)
    assert r.status_code == 200, r.text
    assert r.headers["X-LawLens-Sample"] == "true"
    assert r.json() == fixtures.load(fixture)["response"]


def test_impact_serves_fixture():
    r = client.post("/api/impact", json=fixtures.load("impact")["request"]["body"])
    assert r.status_code == 200, r.text
    assert r.json() == fixtures.load("impact")["response"]


@pytest.mark.parametrize("body", [{"article_id": ART, "depth": 4}, {"depth": 1}])
def test_impact_rejects_bad_request(body):
    assert client.post("/api/impact", json=body).status_code == 422


def test_laws_search_matches_former_name():
    names = [l["name"] for l in client.get("/api/laws", params={"q": "тусгай"}).json()]
    assert names == ["Зөвшөөрлийн тухай хууль"]


def test_health_reports_mock():
    assert client.get("/api/health").json() == {"status": "ok", "mock": True}


def test_real_mode_is_501_until_implemented(monkeypatch):
    monkeypatch.setattr(config, "MOCK", False)
    assert client.get(f"/api/laws/{LAW}").status_code == 501
