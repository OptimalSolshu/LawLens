"""Deterministic citation extraction (facts, method="regex", confidence 1.0).

Supported forms (CLAUDE.md §9):
    "…тухай хуулийн 15.1-д"
    "…тухай хуулийн 6 дугаар зүйлийн 8 дахь хэсэгт"
    "…тухай хуулийн 3 дугаар зүйлийн 2 дахь хэсгийн 1, 2, 4 дэх заалтад"
    "…тухай хуулийн 12 дугаар зүйлд"
    "энэ хуулийн 5.3-т", "энэ хуулийн 80.1.4, 80.1.5-д", "3.1.1-3.1.5-д" (ranges)
    "энэ зүйлийн 2 дахь хэсэгт"
    "…тухай хуулийн 7.1 дүгээр зүйлийн 1 дэх хэсэгт" (codes numbered by chapter: 7.1.1)
    "Иргэний хуулийн …", "…хуулиар / хуульд / хуулийг" (whole-law references)

A citation of a provision that does not exist in a law whose text we have is
KEPT: it points at the law with target_missing=True (and current_number when
a renumbering table knows the new number).
"""
import re
from dataclasses import asdict, dataclass

from .ids import article_id, split_article_id
from .names import SELF_ARTICLE, SELF_LAW, LawNameRegistry, NameEntry
from .normalize import CYR_LOWER

ORD = r"(?:дугаар|дүгээр)"
LOC = r"(?:дахь|дэх|дох|дөх)"
_LIST = r"\d+(?:(?:\s*,\s*|\s+болон\s+|\s+ба\s+)\d+)*"
_DOTTED = r"\d+(?:\.\d+)+"
_CASE = rf"(?:\s*-\s*[{CYR_LOWER}]+)?"

_ARTNO = r"\d+(?:\.\d+)?"  # "12", or "7.1" in codes numbered by chapter (Зөрчлийн тухай хууль, Эрүүгийн хууль)
RE_ART_PART_POINT = re.compile(
    rf"\s*({_ARTNO})\s+{ORD}\s+зүйлийн\s+(\d+)\s+{LOC}\s+хэс(?:эг|г)[{CYR_LOWER}]*\s+({_LIST})\s+{LOC}\s+заалт[{CYR_LOWER}]*")
# "... зүйлийн 4 дэх заалт": parts of the Constitution are called заалт
RE_ART_PART = re.compile(rf"\s*({_ARTNO})\s+{ORD}\s+зүйлийн\s+({_LIST})\s+{LOC}\s+(?:хэс(?:эг|г)|заалт)[{CYR_LOWER}]*")
_ART_LIST = r"\d+(?:\s*[-–]\s*\d+)?(?:(?:\s*,\s*|\s+болон\s+|\s+ба\s+)\d+(?:\s*[-–]\s*\d+)?)*"
RE_ART = re.compile(rf"\s*({_ART_LIST})\s+{ORD}\s+зүйл[{CYR_LOWER}]*")
RE_DOTTED = re.compile(rf"\s*({_DOTTED})(?:\s*[-–]\s*({_DOTTED}))?{_CASE}")
RE_BARE = re.compile(rf"\s*(\d+)\s*-\s*[{CYR_LOWER}]+")
RE_SELF_PART = re.compile(
    rf"\s*({_LIST})\s+{LOC}\s+хэс(?:эг|г)[{CYR_LOWER}]*(?:\s+({_LIST})\s+{LOC}\s+заалт[{CYR_LOWER}]*)?")
RE_SEP = re.compile(r"\s*(?:,|болон|ба)\s*")

SELF_NAME = "энэ хууль"


@dataclass
class Ref:
    """One citation; field names follow refs.jsonl (contracts/data-format.md)."""
    from_article_id: str
    to_law_id: str
    to_number: str | None
    to_article_id: str | None
    raw_text: str
    matched_name: str
    uses_old_name: bool
    target_missing: bool
    method: str = "regex"
    confidence: float = 1.0
    current_number: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _split_list(s: str) -> list[str]:
    return re.findall(r"\d+", s)


def _int_list(s: str) -> list[str]:
    """'18, 19-21 болон 24' -> ['18', '19', '20', '21', '24']"""
    out: list[str] = []
    for a, b in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", s):
        if b and int(a) < int(b) <= int(a) + 50:
            out += [str(k) for k in range(int(a), int(b) + 1)]
        else:
            out += [a] + ([b] if b else [])
    return out


def _expand_range(a: str, b: str) -> list[str]:
    pa, pb = a.rsplit(".", 1), b.rsplit(".", 1)
    if pa[0] == pb[0] and int(pa[1]) < int(pb[1]) <= int(pa[1]) + 50:
        return [f"{pa[0]}.{k}" for k in range(int(pa[1]), int(pb[1]) + 1)]
    return [a, b]


def _article_of(number: str, known: set[str] | None) -> str:
    """The article a provision belongs to: '80.1.4' -> '80'; in a code numbered by chapter,
    where no article '7' exists, '7.1.2' -> '7.1'."""
    parts = number.split(".")
    if known is not None and parts[0] not in known and len(parts) > 1 and ".".join(parts[:2]) in known:
        return ".".join(parts[:2])
    return parts[0]


def _locator(text: str, pos: int) -> tuple[list[str], int] | None:
    """Match ONE provision locator at pos. Returns (numbers, end) or None."""
    if m := RE_ART_PART_POINT.match(text, pos):
        return [f"{m.group(1)}.{m.group(2)}.{p}" for p in _split_list(m.group(3))], m.end()
    if m := RE_ART_PART.match(text, pos):
        return [f"{m.group(1)}.{p}" for p in _split_list(m.group(2))], m.end()
    if m := RE_ART.match(text, pos):
        return _int_list(m.group(1)), m.end()
    if m := RE_DOTTED.match(text, pos):
        nums = _expand_range(m.group(1), m.group(2)) if m.group(2) else [m.group(1)]
        return nums, m.end()
    if m := RE_BARE.match(text, pos):
        return [m.group(1)], m.end()
    return None


def _self_article_locator(text: str, pos: int, art: str) -> tuple[list[str], int] | None:
    if m := RE_SELF_PART.match(text, pos):
        parts = _split_list(m.group(1))
        if m.group(2):
            return [f"{art}.{parts[0]}.{p}" for p in _split_list(m.group(2))], m.end()
        return [f"{art}.{p}" for p in parts], m.end()
    if m := RE_DOTTED.match(text, pos):
        nums = _expand_range(m.group(1), m.group(2)) if m.group(2) else [m.group(1)]
        return [n if n.startswith(f"{art}.") else f"{art}.{n}" for n in nums], m.end()
    return None


def _locators(text: str, pos: int, one) -> tuple[list[str], int]:
    """Consume a list of locators joined by ',', 'болон', 'ба'."""
    nums: list[str] = []
    first = one(text, pos)
    if not first:
        return nums, pos
    nums += first[0]
    pos = first[1]
    while (sep := RE_SEP.match(text, pos)) and (nxt := one(text, sep.end())):
        nums += nxt[0]
        pos = nxt[1]
    return nums, pos


def extract_references(
    text: str,
    *,
    from_article_id: str,
    registry: LawNameRegistry,
    numbers_by_law: dict[str, set[str]],
    renumbering: dict[str, dict[str, str]] | None = None,
) -> list[Ref]:
    """All citations in one provision's text.

    numbers_by_law: provision numbers of every law whose TEXT is loaded; a law
    missing from this map is known by name only, so target_missing cannot be
    decided and stays False.
    """
    self_law, from_number = split_article_id(from_article_id)
    renumbering = renumbering or {}
    spans: list[tuple[int, int, NameEntry | None, str]] = []  # start, end, entry(None=self), matched text

    for m in registry.find(text):
        spans.append((m.start, m.end, m.entry, m.text))
    for m in SELF_LAW.finditer(text):
        if all(m.end() <= s or m.start() >= e for s, e, *_ in spans):
            spans.append((m.start(), m.end(), None, m.group(0)))

    refs: list[Ref] = []
    for start, end, entry, _matched in sorted(spans, key=lambda s: s[0]):
        numbers, stop = _locators(text, end, _locator)
        raw = re.sub(r"\s+", " ", text[start:stop]).strip()
        if entry is None:
            to_law, matched_name, old = self_law, SELF_NAME, False
            if not numbers:
                continue  # "энэ хуульд заасан" without a number carries no target
        else:
            to_law, matched_name, old = entry.law_id, entry.variant, entry.kind == "former"
        known = numbers_by_law.get(to_law)
        for num in numbers or [None]:
            if num is None:
                refs.append(Ref(from_article_id, to_law, None, None, raw, matched_name, old, False))
                continue
            missing = known is not None and num not in known
            refs.append(Ref(
                from_article_id, to_law, num,
                None if (missing or known is None) else article_id(to_law, num),
                raw, matched_name, old, missing,
                current_number=renumbering.get(to_law, {}).get(num) if missing else None,
            ))

    art = _article_of(from_number, numbers_by_law.get(self_law))
    for m in SELF_ARTICLE.finditer(text):
        numbers, stop = _locators(text, m.end(), lambda t, p: _self_article_locator(t, p, art))
        raw = re.sub(r"\s+", " ", text[m.start():stop]).strip()
        known = numbers_by_law.get(self_law)
        for num in numbers:
            missing = known is not None and num not in known
            refs.append(Ref(from_article_id, self_law, num,
                            None if (missing or known is None) else article_id(self_law, num),
                            raw, "энэ зүйл", False, missing))

    seen, out = set(), []
    for r in refs:
        key = (r.to_law_id, r.to_number)
        if key in seen or r.to_article_id == from_article_id:
            continue
        seen.add(key)
        out.append(r)
    return out
