"""Source adapters: where raw legal material comes from.

Each source has an interface, an offline Mock implementation (used by the demo
and tests) and a real implementation that talks to the live service. Nothing in
the API depends on these at request time; they only feed the pipeline.

    LegalInfoSource   legalinfo.mn law texts                 Mock: [ЖИШЭЭ] sample files
    LawForumSource    lawforum.parliament.mn bills           Mock: [ЖИШЭЭ] sample drafts
    ParliamentSource  Parliament API (agenda, votes)         Mock: empty
    ILODataSource     curated ILO / foreign sources          curated file only (no scraping)

CLI (real services, credentials from .env):
    python -m pipeline.sources lawforum --search "Хөдөлмөр"   -> raw/lawforum/projects.json
    python -m pipeline.sources legalinfo find "Зөрчлийн тухай хууль"   -> lawId candidates
    python -m pipeline.sources legalinfo fetch [--force]              -> raw/laws/<law_id>.html (catalog)
    python -m pipeline.sources parliament getMeetings
"""
import argparse
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[1]
TIMEOUT = 30


@dataclass
class RawLaw:
    law_id: str
    name: str
    source_url: str
    text: str | None = None  # plain text (sample) ...
    path: Path | None = None  # ... or a downloaded PDF / legalinfo.mn page for parse_law.py


# ---- legalinfo.mn ---------------------------------------------------------------

class LegalInfoSource(ABC):
    @abstractmethod
    def laws(self) -> list[RawLaw]: ...


class MockLegalInfoSource(LegalInfoSource):
    """[ЖИШЭЭ] sample law texts in data/fixtures/sample/laws/*.txt."""

    def __init__(self, folder: Path = DATA / "fixtures" / "sample" / "laws"):
        self.folder = folder

    def laws(self) -> list[RawLaw]:
        from .parser import split_front_matter

        out = []
        for f in sorted(self.folder.glob("*.txt")):
            meta, body = split_front_matter(f.read_text(encoding="utf-8"))
            out.append(RawLaw(meta["law_id"], meta["name"], meta["source_url"], text=body))
        return out


class LegalInfoHttpSource(LegalInfoSource):
    """legalinfo.mn. A law's detail page (detail?lawId=N) carries the full consolidated
    text server-side, so the page itself is the document: parse_law.py reads the saved
    .html. Laws are listed in data/legalinfo_catalog.json by their legalinfo lawId,
    found with find() and checked by a person before they are added."""

    BASE = "https://legalinfo.mn"
    CATALOG = DATA / "legalinfo_catalog.json"

    def __init__(self, catalog: Path = CATALOG, out_dir: Path = DATA / "raw" / "laws"):
        self.catalog, self.out_dir = catalog, out_dir

    @classmethod
    def page_url(cls, legalinfo_id: str) -> str:
        return f"{cls.BASE}/mn/detail?lawId={legalinfo_id}"

    def entries(self) -> list[dict]:
        return json.loads(self.catalog.read_text(encoding="utf-8"))["laws"]

    def find(self, name: str) -> list[tuple[str, str]]:
        """Laws in force whose title matches `name` exactly: [(lawId, title)]. The site's list
        endpoint also returns amending laws and court decisions that mention the name."""
        import re

        import requests

        def norm(s: str) -> str:
            s = re.sub(r"/?\s*шинэчилсэн найруулга\s*/?", "", s.lower())
            return re.sub(r"\s+", " ", re.sub(r"^монгол улсын\s+", "", s)).strip(" ,/")

        want = {norm(name), norm(re.sub(r"\s*хууль$", "", name))}
        found = {}
        for page in range(1, 51):  # 20 results a page, oldest lawId first
            r = requests.post(f"{self.BASE}/mn/ajaxList", timeout=TIMEOUT,
                              data={"title": re.sub(r"\s*хууль$", "", name), "isvalid": "1", "page": page})
            r.raise_for_status()
            items = re.findall(r"detail\?lawId=(\d+)[^>]*>(.*?)</a>", r.json()["Html"], re.S)
            if not items:
                break
            for lid, title in items:
                title = re.sub(r"<[^>]+>|\s+", " ", title).strip()
                if title and norm(title) in want:
                    found.setdefault(lid, title)
        return list(found.items())

    def download(self, entry: dict, force: bool = False) -> Path:
        import requests

        dest = self.out_dir / f"{entry['law_id']}.html"
        if dest.exists() and not force:
            return dest
        r = requests.get(self.page_url(entry["legalinfo_id"]), timeout=120)
        r.raise_for_status()
        if "responsive_mobile" not in r.text:
            raise RuntimeError(f"{entry['law_id']}: no law text in {r.url}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(r.text, encoding="utf-8")
        return dest

    def laws(self) -> list[RawLaw]:
        return [RawLaw(e["law_id"], e["name"], self.page_url(e["legalinfo_id"]), path=self.download(e))
                for e in self.entries()]


# ---- LawForum -----------------------------------------------------------------------

class LawForumSource(ABC):
    @abstractmethod
    def projects(self, search: str = "", page_size: int = 50) -> list[dict]: ...

    @abstractmethod
    def project(self, project_id: int | str) -> dict: ...


class MockLawForumSource(LawForumSource):
    """[ЖИШЭЭ] bills in data/fixtures/sample/drafts/*.json (title + amendment text + co-submitted bills)."""

    def __init__(self, folder: Path = DATA / "fixtures" / "sample" / "drafts"):
        self.items = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]

    def projects(self, search="", page_size=50):
        return [d for d in self.items if search.lower() in d["title"].lower()][:page_size]

    def project(self, project_id):
        return next(d for d in self.items if d["lawforum_id"] == str(project_id))


class LawForumApiSource(LawForumSource):
    """Public LawForum API (swagger: /LawForumAPI/swagger/v1/swagger.json).
    Returns bill METADATA (title, category, stage, dates). Bill text and the list of
    co-submitted bills are not part of the public API; they must be added to
    data/raw/drafts/*.json before the gap analysis can run on a real bill."""

    def __init__(self, base: str | None = None):
        self.base = (base or os.getenv("LAWFORUM_BASE", "https://lawforum.parliament.mn")).rstrip("/")

    def _get(self, path: str, **params):
        import requests

        r = requests.get(f"{self.base}/LawForumAPI/api/v1/{path}", params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()

    def projects(self, search="", page_size=50):
        return self._get("projects", search=search, pageSize=page_size, page=1)["items"]

    def project(self, project_id):
        return self._get(f"projects/{int(project_id)}")

    @staticmethod
    def to_draft_stub(p: dict) -> dict:
        """Metadata -> data/raw/drafts/*.json skeleton; `text` and `cosubmitted` must be filled from the bill."""
        return {"lawforum_id": str(p["id"]), "title": p["title"],
                "source_url": f"https://lawforum.parliament.mn/project/{p['id']}", "text": "", "cosubmitted": []}


# ---- Parliament API ------------------------------------------------------------------

class ParliamentSource(ABC):
    @abstractmethod
    def call(self, func: str, **params) -> dict | list: ...


class MockParliamentSource(ParliamentSource):
    def call(self, func, **params):
        return []


class ParliamentApiSource(ParliamentSource):
    """POST /api/login -> bearer token; POST /ParliamentService {"func": ...} (CLAUDE.md §8).
    Credentials: PARLIAMENT_USER / PARLIAMENT_PASS from .env, never hard-coded."""

    FUNCS = {"getAgendaList", "getAgendaVoteList", "getMeetings", "getVotingList", "getVotingResult"}

    def __init__(self, base: str | None = None):
        self.base = (base or os.getenv("PARLIAMENT_BASE", "http://202.21.104.13/ParliamentAPI")).rstrip("/")
        self._token: str | None = None

    def _login(self) -> str:
        import requests

        user, password = os.getenv("PARLIAMENT_USER"), os.getenv("PARLIAMENT_PASS")
        if not user or not password:
            raise RuntimeError("set PARLIAMENT_USER and PARLIAMENT_PASS in .env")
        r = requests.post(f"{self.base}/api/login", json={"username": user, "password": password}, timeout=TIMEOUT)
        r.raise_for_status()
        body = r.json()
        return body.get("token") or body.get("access_token") or body["accessToken"]

    def call(self, func, **params):
        import requests

        if func not in self.FUNCS:
            raise ValueError(f"unsupported func {func}")
        self._token = self._token or self._login()
        r = requests.post(f"{self.base}/ParliamentService", json={"func": func, **params},
                          headers={"Authorization": f"Bearer {self._token}"}, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()


# ---- ILO / foreign law ----------------------------------------------------------------

class ILODataSource(ABC):
    @abstractmethod
    def sources(self) -> list[dict]: ...


class CuratedILODataSource(ILODataSource):
    """Hand-curated records (data/international/sources.json). NATLEX / NORMLEX pages are
    behind a browser challenge; entries are added by a person who opened the page."""

    def __init__(self, path: Path = DATA / "international" / "sources.json"):
        self.path = path

    def sources(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8"))["sources"]


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(DATA.parent / ".env")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    lf = sub.add_parser("lawforum")
    lf.add_argument("--search", default="Хөдөлмөр")
    lf.add_argument("--out", type=Path, default=DATA / "raw" / "lawforum" / "projects.json")
    li = sub.add_parser("legalinfo")
    li.add_argument("action", choices=["find", "fetch"])
    li.add_argument("name", nargs="?", help="law name for find")
    li.add_argument("--force", action="store_true", help="fetch: download again even if saved")
    pa = sub.add_parser("parliament")
    pa.add_argument("func")
    args = ap.parse_args()
    if args.cmd == "lawforum":
        items = LawForumApiSource().projects(args.search)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(items)} projects -> {args.out}")
    elif args.cmd == "legalinfo" and args.action == "find":
        for lid, title in LegalInfoHttpSource().find(args.name):
            print(lid, title, LegalInfoHttpSource.page_url(lid))
    elif args.cmd == "legalinfo":
        import time

        src = LegalInfoHttpSource()
        for e in src.entries():
            print(src.download(e, force=args.force))
            time.sleep(1)  # one page a second; the site is a public government service
    else:
        print(json.dumps(ParliamentApiSource().call(args.func), ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
