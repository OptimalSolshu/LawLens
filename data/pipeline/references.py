"""Citation detection -> processed/refs.jsonl.

The implementation is shared with the API: backend/app/parser/references.py
(regex facts; former names and short names via the name registry; missing
targets kept with target_missing=True). This module re-exports it for the
pipeline.
"""
from . import _backend  # noqa: F401
from app.parser.names import LawNameRegistry, load_law_names  # noqa: E402
from app.parser.references import Ref, extract_references  # noqa: E402

__all__ = ["LawNameRegistry", "Ref", "extract_references", "load_law_names"]
