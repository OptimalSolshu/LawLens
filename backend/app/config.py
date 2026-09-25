import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

MOCK = os.getenv("MOCK", "1") == "1"
FIXTURES_DIR = Path(os.getenv("FIXTURES_DIR", REPO_ROOT / "contracts" / "fixtures"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", REPO_ROOT / "data" / "processed"))

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
