"""Plain law text -> articles and clauses (CLAUDE.md §9).

    12 дугаар зүйл. Гарчиг        -> article "12"
    12 дүгээр зүйл.               -> article "12"
    12.1.Текст                    -> clause "12.1" (parent "12")
    12.3.1.Текст                  -> clause "12.3.1" (parent "12.3")

Lines that match no pattern continue the previous clause (or the article
heading if no clause has started yet). Clause numbers must belong to the
current article; anything else is treated as continuation text.
"""
import re
from dataclasses import asdict, dataclass

from .ids import article_id, parent_number

RE_ARTICLE = re.compile(r"^\s*(\d+)\s+(?:дугаар|дүгээр)\s+зүйл\.?\s*(.*)$")
RE_CLAUSE = re.compile(r"^\s*(\d+(?:\.\d+)+)\.\s*(.*)$")
RE_CHAPTER = re.compile(r"^\s*[А-ЯӨҮЁ ]+\s+БҮЛЭГ\s*$")


@dataclass
class ParsedArticle:
    article_id: str
    number: str
    parent_number: str | None
    title: str | None
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def parse_law_text(text: str, law_id: str) -> list[ParsedArticle]:
    articles: list[ParsedArticle] = []
    cur_art: ParsedArticle | None = None
    cur: ParsedArticle | None = None
    for line in text.splitlines():
        if not line.strip() or RE_CHAPTER.match(line):
            continue
        if m := RE_ARTICLE.match(line):
            num = m.group(1)
            cur_art = ParsedArticle(article_id(law_id, num), num, None, _clean(m.group(2)) or None, "")
            articles.append(cur_art)
            cur = None
            continue
        m = RE_CLAUSE.match(line)
        if m and cur_art and m.group(1).split(".")[0] == cur_art.number:
            num = m.group(1)
            cur = ParsedArticle(article_id(law_id, num), num, parent_number(num), None, _clean(m.group(2)))
            articles.append(cur)
            continue
        if cur:
            cur.text = _clean(cur.text + " " + line)
        elif cur_art:
            cur_art.text = _clean(cur_art.text + " " + line)
    return articles


def split_front_matter(raw: str) -> tuple[dict[str, str], str]:
    """Optional 'key: value' header ended by a line '---' (used by sample files)."""
    lines = raw.splitlines()
    if "---" not in [l.strip() for l in lines]:
        return {}, raw
    idx = [l.strip() for l in lines].index("---")
    meta = {}
    for l in lines[:idx]:
        if ":" in l and not l.lstrip().startswith("#"):
            k, v = l.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, "\n".join(lines[idx + 1:])
