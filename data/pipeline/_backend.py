"""Make backend/app importable from the data pipeline.

The deterministic parser (backend/app/parser) and the similarity / relation
services (backend/app/ai) are shared by the pipeline and the API, so there is
one implementation of each.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
