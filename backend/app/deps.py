"""Which GraphStore serves the API (see app/graph/store.py)."""
from functools import cache
from pathlib import Path

from . import config
from .graph.memory import MemoryStore
from .graph.store import GraphStore


@cache
def _store(mock: bool, backend: str, sample_dir: Path, processed_dir: Path) -> GraphStore:
    if mock:
        return MemoryStore(sample_dir, dataset="sample")
    if backend == "memory":
        return MemoryStore(processed_dir, dataset="real")
    from .graph.neo4j_store import Neo4jStore

    return Neo4jStore(dataset="real")


def get_store() -> GraphStore:
    return _store(config.MOCK, config.GRAPH_BACKEND, config.sample_dir(), config.PROCESSED_DIR)
