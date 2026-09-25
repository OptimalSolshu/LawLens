"""Citation detection -> processed/refs.jsonl.

Starter references.py goes here (it was not in the repo at scaffold time).
Resolve law names against current AND former names (law_names.json); set
uses_old_name / target_missing per contracts/data-format.md.
"""
from .schemas import LawRec, RefRec


def find_refs(law: LawRec, laws_by_name: dict[str, LawRec], former_to_current: dict[str, str]) -> list[RefRec]:
    raise NotImplementedError("TODO(member 3): regex pass, then LLM for leftovers (method='llm')")
