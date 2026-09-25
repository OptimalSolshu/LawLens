import pytest
from fastapi.testclient import TestClient

from app import config, deps
from app.graph.memory import MemoryStore
from app.main import app

LABOR = "khodolmoriin-tukhai-khuuli"
OSH = "khodolmoriin-ayuulgui-baidal-eruul-akhuin-tukhai-khuuli"
ZORCHIL = "zorchliin-tukhai-khuuli"
ND = "niigmiin-daatgalyn-tukhai-khuuli"
MINWAGE = "khodolmoriin-kholsnii-dood-khemjeenii-tukhai-khuuli"
HED = "khodolmor-erkhleltiig-demjikh-tukhai-khuuli"


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setattr(config, "MOCK", True)
    deps._store.cache_clear()
    yield
    deps._store.cache_clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def sample_store():
    return MemoryStore(config.sample_dir(), dataset="sample")
