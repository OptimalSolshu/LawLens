import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

# MOCK=1: serve the [ЖИШЭЭ] sample dataset from contracts/fixtures/processed with the
# in-memory graph. No Neo4j, no LLM, no network.
MOCK = os.getenv("MOCK", "1") == "1"
FIXTURES_DIR = Path(os.getenv("FIXTURES_DIR", REPO_ROOT / "contracts" / "fixtures"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", REPO_ROOT / "data" / "processed"))

# MOCK=0: real data/processed, queried through Neo4j (default) or loaded in memory.
GRAPH_BACKEND = os.getenv("GRAPH_BACKEND", "neo4j")
# Load PROCESSED_DIR into Neo4j at startup when the graph is empty (docker compose).
SEED_ON_START = os.getenv("SEED_ON_START", "0") == "1"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]


def sample_dir() -> Path:
    return FIXTURES_DIR / "processed"
