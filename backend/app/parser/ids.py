"""Id conventions (contracts/data-format.md). Same algorithm as data/pipeline/ids.py."""
import re

_MN_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "ye", "ё": "yo", "ж": "j", "з": "z",
    "и": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "ө": "o", "п": "p",
    "р": "r", "с": "s", "т": "t", "у": "u", "ү": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "sh", "ъ": "i", "ы": "y", "ь": "i", "э": "e", "ю": "yu", "я": "ya",
}


def law_id(name: str) -> str:
    """ASCII slug of a law's current name: 'Зөвшөөрлийн тухай хууль' -> 'zovshoorliin-tukhai-khuuli'."""
    latin = "".join(_MN_LATIN.get(c, c) for c in name.strip().lower())
    return re.sub(r"[^a-z0-9]+", "-", latin).strip("-")


def article_id(law_id: str, number: str) -> str:
    return f"{law_id}:{number}"


def split_article_id(aid: str) -> tuple[str, str]:
    law, _, number = aid.partition(":")
    return law, number


def ancestors(number: str) -> list[str]:
    """'80.1.2' -> ['80.1', '80']"""
    parts = number.split(".")
    return [".".join(parts[:i]) for i in range(len(parts) - 1, 0, -1)]


def parent_number(number: str) -> str | None:
    return number.rsplit(".", 1)[0] if "." in number else None
