"""Amendment wording in bills (CLAUDE.md §9).

    …"А" гэснийг "Б" гэж өөрчилсүгэй      -> replace (old_text=А, new_text=Б)
    …"А" гэсний дараа "Б" гэж нэмсүгэй    -> insert  (old_text=А, new_text=Б)
    …"А" гэснийг хассугай                 -> delete  (old_text=А)
    …-ийг хүчингүй болсонд тооцсугай      -> repeal
    …-ийг доор дурдсан агуулгатай нэмсүгэй -> add (new provision)
    …хуулийн нэрийг "Б" гэж өөрчилсүгэй   -> rename (new_text=Б)

The target law and provision come from the first citation in the sentence
(references.extract_references), so former names and missing numbers are
flagged exactly as for ordinary references.
"""
import re
from dataclasses import asdict, dataclass

from .names import LawNameRegistry
from .normalize import norm
from .references import extract_references

Q = r"[\"“”«»„]"
TXT = r"[^\"“”«»„]+"
RE_REPLACE = re.compile(rf"{Q}({TXT}){Q}\s+гэснийг\s+{Q}({TXT}){Q}\s+гэж\s+өөрчил")
RE_INSERT = re.compile(rf"{Q}({TXT}){Q}\s+гэсний\s+дараа\s+{Q}({TXT}){Q}\s+гэж\s+нэм")
RE_DELETE = re.compile(rf"{Q}({TXT}){Q}\s+гэснийг\s+хасс")
RE_RENAME = re.compile(rf"нэрийг\s+{Q}({TXT}){Q}\s+гэж\s+өөрчил")
RE_QUOTED = re.compile(rf"{Q}{TXT}{Q}")
RE_REPEAL = re.compile(r"хүчингүй\s+болсонд\s+тооц")
RE_ADD = re.compile(r"агуулгатай\s+.*нэмс|дараах\s+агуулгатай")


@dataclass
class AmendmentOp:
    op: str  # replace | insert | delete | repeal | add | rename
    law_id: str
    number: str | None
    article_id: str | None
    old_text: str | None
    new_text: str | None
    raw_text: str
    uses_old_name: bool
    target_missing: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=сүгэй\.)|(?<=сугай\.)|(?<=тугай\.)|\n+", text)
    return [p.strip() for p in parts if p and p.strip()]


def parse_amendments(text: str, *, registry: LawNameRegistry, numbers_by_law: dict[str, set[str]],
                     draft_law_id: str = "draft") -> list[AmendmentOp]:
    ops: list[AmendmentOp] = []
    for s in _sentences(text):
        if m := RE_RENAME.search(s):
            kind, old, new = "rename", None, m.group(1)
        elif m := RE_REPLACE.search(s):
            kind, old, new = "replace", m.group(1), m.group(2)
        elif m := RE_INSERT.search(s):
            kind, old, new = "insert", m.group(1), m.group(2)
        elif m := RE_DELETE.search(s):
            kind, old, new = "delete", m.group(1), None
        elif RE_REPEAL.search(s):
            kind, old, new = "repeal", None, None
        elif RE_ADD.search(s):
            kind, old, new = "add", None, None
        else:
            continue
        # quoted strings are the amended wording, not citations
        unquoted = RE_QUOTED.sub('""', s)
        refs = [r for r in extract_references(unquoted, from_article_id=f"{draft_law_id}:0", registry=registry,
                                              numbers_by_law=numbers_by_law) if r.to_law_id != draft_law_id]
        if not refs:
            continue
        with_number = [r for r in refs if r.to_number] or refs[:1]
        for r in with_number:
            ops.append(AmendmentOp(kind, r.to_law_id, r.to_number, r.to_article_id,
                                   old and old.strip(), new and new.strip(), s,
                                   r.uses_old_name, r.target_missing))
    return ops


def law_in_title(title: str, registry: LawNameRegistry) -> str | None:
    """'Зөрчлийн тухай хуульд өөрчлөлт оруулах тухай' -> law_id of the FIRST law named."""
    found = registry.find(title, include_unknown=False)
    return found[0].entry.law_id if found else None


def is_amendment_title(title: str) -> bool:
    t = norm(title)
    return "нэмэлт" in t or "өөрчлөлт" in t or "хүчингүй" in t
