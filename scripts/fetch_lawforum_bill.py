#!/usr/bin/env python3
"""Save a real LawForum bill with its co-submitted bills as data/raw/drafts/<id>.json.

    python scripts/fetch_lawforum_bill.py 11072 --cosubmitted-file 17296 \\
        --target-law "Хөдөлмөрийн аюулгүй байдал, эрүүл ахуйн тухай хууль" \\
        --new-name "Хөдөлмөрийн аюулгүй байдал, эрүүл мэндийн тухай хууль"

The public LawForum API has bill metadata only, so the bill text is read from the
project page (lawforum.parliament.mn/project/<id>) and the co-submitted bills from the
page's "Хамт өргөн мэдүүлсэн хуулийн төслүүд" attachment (a .doc, converted to text
with LibreOffice). --target-law/--new-name are for a revised law (шинэчилсэн найруулга)
that replaces a law under a new title: the gap analysis then treats every citation of
the old law as needing an amendment.
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://lawforum.parliament.mn"
HEAD = re.compile(r"^\s*Төсөл\s*$|^\s*МОНГОЛ УЛСЫН ХУУЛЬ\s*$")


def page_text(project_id: int) -> tuple[str, str]:
    """(title, bill text) from the project page: articles and parts, without the page's comment widgets."""
    h = requests.get(f"{BASE}/project/{project_id}", timeout=120).text
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    lines = [re.sub(r"\s+", " ", html.unescape(x)).strip() for x in re.sub(r"<[^>]+>", "\n", h).split("\n")]
    lines = [x for x in lines if x and x not in {"comment", "thumb_up_alt", "thumb_down_alt"} and not x.isdigit()]
    start = next(i for i, x in enumerate(lines) if re.match(r"^1 (?:дүгээр|дугаар) зүйл\.", x))
    end = next((i for i, x in enumerate(lines) if "download file" in x or x.startswith("insert_drive_file")), len(lines))
    body, out = lines[start:end], []
    for x in body:  # "1 дүгээр зүйл." and its title come on separate lines
        if out and re.match(r"^\d+[¹²³]? (?:дүгээр|дугаар) зүйл\.$", out[-1]):
            out[-1] += x
        else:
            out.append(x)
    title = next((x for x in lines if x.upper().startswith("ХӨДӨЛМӨР") or "ТУХАЙ" in x.upper()), "")
    return title, "\n".join(out)


def doc_text(file_id: int) -> str:
    r = requests.get(f"{BASE}/files/{file_id}/?d=1", timeout=120)
    r.raise_for_status()
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        sys.exit("LibreOffice (soffice) is needed to read the .doc attachment")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "cosubmitted.doc"
        src.write_bytes(r.content)
        subprocess.run([soffice, "--headless", "--convert-to", "txt:Text", "--outdir", tmp, str(src)],
                       check=True, capture_output=True)
        return (Path(tmp) / "cosubmitted.txt").read_text(encoding="utf-8-sig")


def split_bills(text: str) -> list[dict]:
    """Each bill starts with 'Төсөл' / 'МОНГОЛ УЛСЫН ХУУЛЬ'; its title is the upper-case block before '1 дүгээр зүйл'."""
    bills, cur = [], None
    for line in text.splitlines():
        s = line.strip()
        if HEAD.match(s):
            if cur is None or cur["body"]:
                cur = {"title": [], "body": []}
                bills.append(cur)
            continue
        if cur is None or not s:
            continue
        if not cur["body"] and s.isupper() and not re.search(r"\d", s):
            cur["title"].append(s)
        elif cur["title"] and (cur["body"] or re.match(r"^1 (?:дүгээр|дугаар) зүйл", s)):
            if s.startswith("ГАРЫН"):
                continue
            cur["body"].append(s)
    out = []
    for b in bills:
        if not b["title"] or not b["body"]:
            continue
        title = " ".join(b["title"])
        title = title[0] + title[1:].lower()  # "ХӨДӨЛМӨРИЙН ТУХАЙ ХУУЛЬД ..." -> sentence case
        out.append({"title": title, "text": "\n".join(b["body"])})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_id", type=int)
    ap.add_argument("--cosubmitted-file", type=int, help="LawForum file id of the co-submitted bills (.doc)")
    ap.add_argument("--target-law", help="law the bill amends or replaces, as named in law_names.json")
    ap.add_argument("--new-name", help="new name of that law (revised law under a new title)")
    args = ap.parse_args()

    meta = requests.get(f"{BASE}/LawForumAPI/api/v1/projects/{args.project_id}", timeout=120).json()
    _, text = page_text(args.project_id)
    cos = split_bills(doc_text(args.cosubmitted_file)) if args.cosubmitted_file else []
    draft = {"lawforum_id": str(args.project_id), "title": meta["title"],
             "source_url": f"{BASE}/project/{args.project_id}", "text": text, "cosubmitted": cos}
    if args.cosubmitted_file:
        draft["cosubmitted_source_url"] = f"{BASE}/files/{args.cosubmitted_file}/?d=1"
    if args.target_law:
        draft["target_law"] = args.target_law
    if args.new_name:
        draft["new_name"] = args.new_name
    out = ROOT / "data" / "raw" / "drafts" / f"{args.project_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(draft, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{meta['title']}\n  {len(text)} chars, {len(cos)} co-submitted bills -> {out.relative_to(ROOT)}")
    for c in cos:
        print("   ", c["title"])


if __name__ == "__main__":
    main()
