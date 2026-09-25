"""Fetch law texts and draft bills.

- laws  -> raw/laws/<current law name>.txt
- drafts (LAWFORUM_BASE / PARLIAMENT_BASE) -> processed/drafts.json
Credentials come from .env (PARLIAMENT_USER / PARLIAMENT_PASS), never hard-coded.
"""
import os

LAWFORUM_BASE = os.getenv("LAWFORUM_BASE", "")
PARLIAMENT_BASE = os.getenv("PARLIAMENT_BASE", "")


def fetch_laws() -> None:
    raise NotImplementedError("TODO(member 3)")


def fetch_drafts() -> None:
    raise NotImplementedError("TODO(member 3)")
