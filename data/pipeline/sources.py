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
    python -m pipeline.sources legalinfo URL --out raw/laws/x.pdf
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
    path: Path | None = None  # ... or a downloaded PDF for parse_law.py


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
    """Downloads law documents by URL. legalinfo.mn detail pages are rendered client-side,
    so the document (PDF) URL is configured per law in `catalog` ({law_id: (name, page_url, file_url)})."""

    def __init__(self, catalog: dict[str, tuple[str, str, str]], out_dir: Path = DATA / "raw" / "laws"):
        self.catalog, self.out_dir = catalog, out_dir

    def download(self, file_url: str, dest: Path) -> Path:
        import requests

        r = requests.get(file_url, timeout=TIMEOUT)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        return dest

    def laws(self) -> list[RawLaw]:
        return [RawLaw(lid, name, page, path=self.download(file_url, self.out_dir / f"{lid}.pdf"))
                for lid, (name, page, file_url) in self.catalog.items()]


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
    li.add_argument("url")
    li.add_argument("--out", type=Path, required=True)
    pa = sub.add_parser("parliament")
    pa.add_argument("func")
    args = ap.parse_args()
    if args.cmd == "lawforum":
        items = LawForumApiSource().projects(args.search)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(items)} projects -> {args.out}")
    elif args.cmd == "legalinfo":
        print(LegalInfoHttpSource({}).download(args.url, args.out))
    else:
        print(json.dumps(ParliamentApiSource().call(args.func), ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
