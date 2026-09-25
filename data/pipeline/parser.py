"""Plain law text -> articles (backend/app/parser/law_text.py).

PDF laws from legalinfo.mn go through ../parse_law.py first (pdftotext layout
parser, keeps repeal/amendment notes) and then pipeline.from_lawgraph.
Plain-text laws (e.g. the [ЖИШЭЭ] sample files) use parse_law_text directly.
"""
from . import _backend  # noqa: F401
from app.parser.law_text import parse_law_text, split_front_matter  # noqa: E402

__all__ = ["parse_law_text", "split_front_matter"]
