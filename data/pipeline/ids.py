"""Shared id conventions (contracts/data-format.md)."""
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
