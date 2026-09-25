"""Mongolian search over law names (current, former, short), provision numbers and text.

"хөдөлмөрийн 80.1"   -> law name word + provision number
"тусгай зөвшөөрөл"   -> matches a FORMER law name
"ажлын цаг"          -> keyword in provision titles/texts ("цагийн", "цагаас" match too)
Query words are stemmed (normalize.stem) and matched as prefixes of stemmed text words.
"""
import time

from ..graph.store import GraphStore, number_key, under
from ..parser.normalize import is_number, stem, stems, tokens
from ..schemas import ArticleHit, SearchResponse
from .reference_service import article_url, excerpt, law_summary

LIMIT = 60
INDEX_TTL = 600  # s; the graph is read-only between loads, and stemming ~50k provisions takes seconds
_index: dict[int, tuple[float, list[tuple[dict, list[str]]]]] = {}


def article_index(store: GraphStore) -> list[tuple[dict, list[str]]]:
    """(article, stemmed title+text) for every provision, cached per store for INDEX_TTL."""
    now = time.monotonic()
    hit = _index.get(id(store))
    if hit and hit[0] > now:
        return hit[1]
    index = [(a, stems(f"{a.get('title') or ''} {a.get('text') or ''}")) for a in store.all_articles()]
    _index[id(store)] = (now + INDEX_TTL, index)
    return index


def _match(word: str, bag: list[str]) -> bool:
    """Prefix match either way on stems: "цалин" ~ "цалингийн", "хөдөлмөр" ~ "хөдөлмөрийн"."""
    return any(t.startswith(word) or (len(t) >= 4 and word.startswith(t)) for t in bag)


def search(store: GraphStore, q: str) -> SearchResponse:
    toks = tokens(q)[:12]
    numbers = [t for t in toks if is_number(t)]
    words = [stem(t) for t in toks if not is_number(t)]
    words = [w for w in words if len(w) >= 2]
    laws = store.laws()
    law_bags = {l["law_id"]: stems(" ".join([l["name"], *l.get("former_names", []), *l.get("short_names", [])]))
                for l in laws}
    law_hits = [l for l in laws if words and all(_match(w, law_bags[l["law_id"]]) for w in words)] if words else []

    hits: list[tuple[tuple, ArticleHit]] = []
    if numbers or words:
        by_id = {l["law_id"]: l for l in laws}
        for a, bag in article_index(store):
            law = by_id.get(a["law_id"])
            if not law:
                continue
            if numbers and not any(under(a["number"], n) for n in numbers):
                continue
            in_law = [w for w in words if _match(w, law_bags[law["law_id"]])]
            in_text = [w for w in words if _match(w, bag)]
            if any(w not in in_law and w not in in_text for w in words):
                continue
            if not numbers and not in_text:
                continue  # a law-name-only query lists the law, not every provision
            exact = any(a["number"] == n for n in numbers)
            rank = (not exact, -len(in_text), number_key(a["number"]), law["name"])
            hits.append((rank, ArticleHit(article_id=a["article_id"], law_id=law["law_id"], law_name=law["name"],
                                          number=a["number"], title=a.get("title"),
                                          snippet=excerpt(a.get("text") or a.get("title") or "", 240),
                                          source_url=article_url(law, a["number"]))))
    hits.sort(key=lambda h: h[0])
    return SearchResponse(query=q, laws=[law_summary(l) for l in law_hits], articles=[h for _, h in hits[:LIMIT]])
