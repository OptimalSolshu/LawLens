"""Law name registry: current, former, short names and aliases -> canonical law.

Built from data/law_names.json and from laws.jsonl records. Matching in text
is case-insensitive, whitespace-tolerant, accepts the case endings
хууль / хуулийн / хуулиар / хуульд / хуулийг / хуулиас, and always prefers
the LONGEST name when two candidate names overlap.
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from .ids import law_id as slug
from .normalize import CYR_LOWER, CYR_UPPER, norm

NameKind = Literal["current", "former", "short", "alias", "unknown"]

# хууль + case endings, longest first
LAW_WORD = r"хуул(?:ийнхаа|иудын|ийн|иар|иас|ийг|ьтэй|ьд|ь)"
_NOT_LETTER_AFTER = rf"(?![{CYR_LOWER}{CYR_UPPER}])"
_NOT_LETTER_BEFORE = rf"(?<![{CYR_LOWER}{CYR_UPPER}])"

# A law name not in the registry: capitalised word + up to 8 lowercase words + "тухай хууль".
GENERIC_TUKHAI = re.compile(
    rf"{_NOT_LETTER_BEFORE}[{CYR_UPPER}][{CYR_LOWER}]*(?:,?\s+[{CYR_LOWER}]+){{0,8}}?\s+тухай\s+{LAW_WORD}{_NOT_LETTER_AFTER}"
)
SELF_LAW = re.compile(rf"{_NOT_LETTER_BEFORE}[Ээ]нэ\s+{LAW_WORD}{_NOT_LETTER_AFTER}")
SELF_ARTICLE = re.compile(rf"{_NOT_LETTER_BEFORE}[Ээ]нэ\s+зүйлийн{_NOT_LETTER_AFTER}")


@dataclass(frozen=True)
class NameEntry:
    law_id: str
    variant: str  # the name form as registered, e.g. "Тусгай зөвшөөрлийн тухай хууль"
    canonical: str  # current name of the law
    kind: NameKind


@dataclass(frozen=True)
class NameMatch:
    start: int
    end: int
    text: str  # exact text in the source, e.g. "Тусгай зөвшөөрлийн тухай хуулийн"
    entry: NameEntry


def canonical_form(name: str) -> str:
    """'Хөдөлмөрийн тухай хуулийн' -> 'Хөдөлмөрийн тухай хууль' (whitespace collapsed)."""
    name = re.sub(r"\s+", " ", name).strip()
    return re.sub(rf"{LAW_WORD}$", "хууль", name)


def _pattern(variant: str) -> str:
    words = canonical_form(variant).split(" ")
    if words[-1] == "хууль":
        words = [re.escape(w) for w in words[:-1]] + [LAW_WORD]
    else:
        words = [re.escape(w) for w in words]
    return _NOT_LETTER_BEFORE + r"\s+".join(words) + _NOT_LETTER_AFTER


class LawNameRegistry:
    def __init__(self, entries: Iterable[NameEntry] = ()):
        self._by_norm: dict[str, NameEntry] = {}
        self._compiled: list[tuple[re.Pattern, NameEntry]] = []
        for e in entries:
            self.add(e)

    # -- building -----------------------------------------------------------
    def add(self, entry: NameEntry) -> None:
        key = norm(canonical_form(entry.variant))
        existing = self._by_norm.get(key)
        # a current name always wins over the same string registered as alias
        if existing and existing.kind == "current":
            return
        self._by_norm[key] = entry
        self._compiled = [(p, e) for p, e in self._compiled if e.variant != entry.variant]
        self._compiled.append((re.compile(_pattern(entry.variant), re.IGNORECASE), entry))
        self._compiled.sort(key=lambda pe: -len(pe[1].variant))

    def add_law(self, law_id: str, name: str, former=(), short=(), aliases=()) -> None:
        self.add(NameEntry(law_id, name, name, "current"))
        for kind, variants in (("former", former), ("short", short), ("alias", aliases)):
            for v in variants:
                self.add(NameEntry(law_id, v, name, kind))

    @classmethod
    def from_sources(cls, laws: Iterable[dict] = (), law_names_file: Path | None = None) -> "LawNameRegistry":
        """laws: laws.jsonl-style dicts (law_id, name, former_names, short_names).
        law_names_file: data/law_names.json (see contracts/data-format.md)."""
        reg = cls()
        if law_names_file and law_names_file.exists():
            for rec in load_law_names(law_names_file):
                reg.add_law(rec["law_id"], rec["current_name"], rec["former_names"], rec["short_names"], rec["aliases"])
        for law in laws:
            reg.add_law(law["law_id"], law["name"], law.get("former_names", []), law.get("short_names", []),
                        law.get("aliases", []))
        return reg

    # -- lookup -------------------------------------------------------------
    def resolve(self, name: str) -> NameEntry | None:
        return self._by_norm.get(norm(canonical_form(name)))

    def entries(self) -> list[NameEntry]:
        return list(self._by_norm.values())

    def find(self, text: str, *, include_unknown: bool = True) -> list[NameMatch]:
        """Every law name in `text`, non-overlapping, longest name first.

        Registry names beat generic "... тухай хууль" matches; an unknown generic
        name resolves to the slug of its canonical form (kind="unknown").
        """
        cands: list[NameMatch] = []
        for pattern, entry in self._compiled:
            for m in pattern.finditer(text):
                cands.append(NameMatch(m.start(), m.end(), m.group(0), entry))
        chosen = _longest_non_overlapping(cands)
        if include_unknown:
            generic = []
            for m in GENERIC_TUKHAI.finditer(text):
                name = canonical_form(m.group(0))
                if self.resolve(name) is None:
                    e = NameEntry(slug(name), name, name, "unknown")
                    generic.append(NameMatch(m.start(), m.end(), m.group(0), e))
            chosen = _longest_non_overlapping(chosen, extra=generic)
        return sorted(chosen, key=lambda m: m.start)


def _longest_non_overlapping(primary: list[NameMatch], extra: list[NameMatch] = ()) -> list[NameMatch]:
    """Greedy: longer spans first; `primary` spans always beat `extra` spans."""
    out: list[NameMatch] = []
    for group in (primary, extra):
        for m in sorted(group, key=lambda m: (-(m.end - m.start), m.start)):
            if all(m.end <= o.start or m.start >= o.end for o in out):
                out.append(m)
    return out


def load_law_names(path: Path) -> list[dict]:
    """Read data/law_names.json. Accepts the documented list format
    {"laws": [{current_name, former_names, short_names, aliases, law_id?, source_url?}]}
    and the legacy map {"current name": ["former name", ...]}."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "laws" in raw:
        items = raw["laws"]
    else:
        items = [{"current_name": k, "former_names": v} for k, v in raw.items() if not k.startswith("_")]
    out = []
    for it in items:
        name = it["current_name"]
        out.append({
            "law_id": it.get("law_id") or slug(name),
            "current_name": name,
            "former_names": list(it.get("former_names", [])),
            "short_names": list(it.get("short_names", [])),
            "aliases": list(it.get("aliases", [])),
            "source_url": it.get("source_url"),
        })
    return out
