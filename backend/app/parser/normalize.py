"""Mongolian text normalisation shared by the parser and search.

Deterministic and dependency-free: case folding, whitespace, and a small
suffix stripper good enough for prefix matching of inflected words
("хөдөлмөрийн" -> "хөдөлмөр", "хуулийн" -> "хуул").
"""
import re

CYR_LOWER = "а-яөүё"
CYR_UPPER = "А-ЯӨҮЁ"
LETTER = f"[{CYR_LOWER}{CYR_UPPER}a-zA-Z]"

# Longest first; only stripped when at least MIN_STEM letters remain.
_SUFFIXES = sorted(
    {
        "уудын", "үүдийн", "иудын", "нуудын",
        "ийнх", "ынх", "ийн", "ын", "ний", "ны", "ий", "ы",
        "ийг", "ыг", "г",
        "аар", "ээр", "оор", "өөр", "иар", "иэр", "гаар", "гээр",
        "аас", "ээс", "оос", "өөс", "иас", "гаас", "гээс",
        "тай", "тэй", "той",
        "руу", "рүү", "луу", "лүү",
        "ад", "эд", "од", "өд", "ид", "д", "т",
        "ь", "н",
    },
    key=len,
    reverse=True,
)
MIN_STEM = 3

_WS = re.compile(r"\s+")
_TOKEN = re.compile(rf"\d+(?:\.\d+)*|[{CYR_LOWER}a-z]+")
_QUOTES = str.maketrans({"“": '"', "”": '"', "«": '"', "»": '"', "„": '"', " ": " "})


def norm(s: str) -> str:
    """Case-fold, unify quotes, collapse whitespace."""
    return _WS.sub(" ", s.translate(_QUOTES)).strip().casefold()


def stem(word: str) -> str:
    w = word.casefold()
    if w[:1].isdigit():
        return w
    for suf in _SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= MIN_STEM:
            return w[: -len(suf)]
    return w


def tokens(s: str) -> list[str]:
    return _TOKEN.findall(norm(s))


def stems(s: str) -> list[str]:
    return [stem(t) for t in tokens(s)]


def is_number(token: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)*", token))
