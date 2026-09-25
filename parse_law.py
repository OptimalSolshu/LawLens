"""Монгол хуулийн PDF-ийг бүтэцтэй JSON граф болгон задлах.

Хэрэглээ:
    python parse_law.py data/labor_law_2021.pdf --id labor-2021 -o data/labor_law_2021.json
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

CYR_L = "а-яөүё"
CYR_U = "А-ЯӨҮЁ"
W = rf"[{CYR_L}{CYR_U}]"  # кирилл үсэг

RE_FOOTER = re.compile(r"^\s*\d+\s*/\s*\d+\s*$")
RE_CHAPTER = re.compile(rf"^\s*([{CYR_U} ]+?)\s*БҮЛЭГ\s*$")
RE_SECTION = re.compile(rf"^\s*([{CYR_U}][{CYR_L}]+)\s+дэд\s+бүлэг\s*$")
RE_ARTICLE = re.compile(r"^\s*(\d+)\s+(?:дүгээр|дугаар)\s+зүйл\.\s*(.*)$")
RE_PROVISION = re.compile(r"^\s*(\d+(?:\.\d+)+)\.(.*)$")
RE_AMEND = re.compile(
    r"^\s*/Энэ\s+(\S+)\s+(\d{4})\s+оны\s+(\d+)\s+(?:дүгээр|дугаар)\s+сарын\s+(\d+)-\S*\s+өдрийн\s+хуулиар\s+(.+?)\.?/\s*$"
)
RE_SIGNED = re.compile(r"^\s*МОНГОЛ УЛСЫН ИХ ХУРЛЫН ДАРГА\s+(.+?)\s*$")
RE_ADOPTED = re.compile(r"(\d{4})\s+оны\s+(\d+)\s+сарын\s+(\d+)\s+өдөр")
RE_EFFECTIVE = re.compile(r"(\d{4})\s+оны\s+(\d+)\s+(?:дүгээр|дугаар)\s+сарын\s+(\d+)-\S*\s+өдрөөс\s+эхлэн\s+дагаж\s+мөрдөнө")

ORDINALS = {  # "ЗУРГАДУГААР", "ДОЛДУГААР" гэх мэт тул угтвараар тааруулна
    "НЭГ": 1, "ХОЁР": 2, "ГУРАВ": 3, "ДӨРӨВ": 4, "ТАВ": 5, "ЗУРГ": 6, "ДОЛ": 7,
    "НАЙМ": 8, "ЕС": 9, "АРАВ": 10,
}

# Хуульд тодорхойлоогүй ч олон дурдагддаг оролцогчид / бүлгүүд.
# (нэр, ангилал, regex — жижиг үсгээр тааруулна)
ACTORS = [
    ("Хөдөлмөрийн асуудал эрхэлсэн Засгийн газрын гишүүн", "төрийн байгууллага", r"асуудал эрхэлсэн засгийн газрын гишүүн"),
    ("Хөдөлмөрийн асуудал эрхэлсэн төрийн захиргааны төв байгууллага", "төрийн байгууллага",
     r"хөдөлмөрийн асуудал эрхэлсэн төрийн захиргааны төв байгууллага\w*"),
    ("Засгийн газар", "төрийн байгууллага", r"засгийн газ(?:ар|р)\w*"),
    ("Засаг дарга", "төрийн байгууллага", r"засаг дарг\w*"),
    ("Хөдөлмөрийн хяналтын улсын байцаагч", "хяналтын байгууллага", r"(?:хөдөлмөрийн хяналтын )?улсын байцаагч\w*"),
    ("Хөдөлмөрийн хяналтын байгууллага", "хяналтын байгууллага", r"хөдөлмөрийн хяналтын байгууллага\w*"),
    ("Шүүх", "маргаан шийдвэрлэх", r"шүүх\w*"),
    ("Хөдөлмөрийн эрхийн маргаан таслах комисс", "маргаан шийдвэрлэх", r"(?:хөдөлмөрийн эрхийн )?маргаан таслах комисс\w*"),
    ("Хөдөлмөрийн зуучлагч", "маргаан шийдвэрлэх", r"(?:хөдөлмөрийн )?зуучлагч\w*"),
    ("Хөдөлмөрийн арбитр", "маргаан шийдвэрлэх", r"(?:хөдөлмөрийн )?арбитр\w*"),
    ("Гурван талт хороо", "нийгмийн түншлэл", r"(?:хөдөлмөр, нийгмийн түншлэлийн )?гурван талт\s+(?:үндэсний\s+)?хороо\w*"),
    ("Үйлдвэрчний эвлэл", "төлөөллийн байгууллага", r"үйлдвэрчний эвл\w*"),
    ("Жирэмсэн эмэгтэй", "хамгаалалттай бүлэг", r"жирэмсэн\w*"),
    ("Хөгжлийн бэрхшээлтэй хүн", "хамгаалалттай бүлэг", r"хөгжлийн бэрхшээлтэй"),
    ("Гадаадын иргэн", "хамгаалалттай бүлэг", r"гадаадын иргэн\w*"),
    ("Дагалдан ажилтан", "тусгай ажилтан", r"дагалд(?:ан|на)\w*"),
    ("Зайнаас ажиллах ажилтан", "тусгай ажилтан", r"зайнаас ажилл\w*"),
    ("Гэрээсээ ажиллах ажилтан", "тусгай ажилтан", r"гэрээсээ ажилл\w*"),
]
# Тодорхойлсон нэр томьёонуудаас ажил олгогч / ажилтны талыг илэрхийлэх нь оролцогч (Actor) мөн
PARTY_TERMS = {"ажил олгогч", "ажил олгогчийн төлөөлөгч", "ажилтан", "ажилтны төлөөлөгч", "насанд хүрээгүй ажилтан"}

KNOWN_LAWS = r"(?:Монгол Улсын\s+)?(Үндсэн|Эрүүгийн|Иргэний|Нийгмийн даатгалын ерөнхий)\s+хуул[ьи]\w*"
RE_TUKHAI_LAW = re.compile(rf"[{CYR_U}]{W}*(?:,?\s+{W}+){{0,8}}?\s+тухай\s+хуул[ьи]\w*")

NUM = r"\d+(?:\.\d+)*(?:\s+(?:дүгээр|дугаар)\s+зүйл\w*)?"
SUF = rf"(?:-[{CYR_L}]+)?"
RE_CH_REF = re.compile(rf"энэ\s+хуулийн\s+([{CYR_U}][{CYR_L}]+(?:\s+[{CYR_L}]+)?)\s+бүлэг")
RE_XREF = re.compile(rf"[Ээ]нэ\s+(хуулийн|зүйлийн)\s+({NUM}{SUF}(?:\s*(?:,|болон|-|–)\s*{NUM}{SUF})*)")


def pdf_text(pdf: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True, text=True).stdout


def chapter_number(word: str) -> int:
    word = word.replace(" ", "")
    n = 10 if word.startswith("АРВАН") else 0
    rest = word[5:] if n else word
    for k, v in ORDINALS.items():
        if rest.startswith(k):
            return n + v
    return n


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def parse_structure(text: str):
    lines = text.splitlines()
    law = {"title": None, "adopted": None, "signed_by": None, "effective": None}
    chapters, sections, articles, provisions, amendments = [], [], [], [], []
    cur_ch = cur_sec = cur_art = cur_prov = None
    head_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if RE_FOOTER.match(line) or not line.strip():
            i += 1
            continue
        if m := RE_SIGNED.match(line):
            law["signed_by"] = m.group(1)
            i += 1
            continue
        if m := RE_CHAPTER.match(line):
            title = []
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i].strip().isupper()) and not RE_ARTICLE.match(lines[i]):
                if lines[i].strip():
                    title.append(lines[i].strip())
                i += 1
            num = chapter_number(m.group(1))
            cur_ch = {"id": f"ch{num}", "number": num, "title": clean(" ".join(title)).capitalize()}
            chapters.append(cur_ch)
            cur_sec = None
            continue
        if m := RE_SECTION.match(line):
            i += 1
            while not lines[i].strip():
                i += 1
            num = chapter_number(m.group(1).upper())
            cur_sec = {"id": f"{cur_ch['id']}.sec{num}", "number": num, "title": clean(lines[i]), "chapter": cur_ch["id"]}
            sections.append(cur_sec)
            cur_prov = None
            i += 1
            continue
        if m := RE_ARTICLE.match(line):
            cur_art = {"id": f"art{m.group(1)}", "number": int(m.group(1)), "title": clean(m.group(2)),
                       "chapter": cur_ch["id"], "text": ""}
            articles.append(cur_art)
            cur_prov = None
            i += 1
            continue
        if m := RE_AMEND.match(line):
            target = cur_prov or cur_art
            kind = m.group(5)
            amendments.append({
                "target": target["id"],
                "date": f"{m.group(2)}-{int(m.group(3)):02d}-{int(m.group(4)):02d}",
                "type": "хүчингүй" if "хүчингүй" in kind else ("нэмсэн" if kind.startswith("нэмсэн") else kind.replace(" оруулсан", "")),
            })
            if "хүчингүй" in kind and target is cur_prov:
                cur_prov["status"] = "хүчингүй"
            i += 1
            continue
        m = RE_PROVISION.match(line)
        if m and cur_art and m.group(1).split(".")[0] == str(cur_art["number"]):
            num = m.group(1)
            parent = num.rsplit(".", 1)[0]
            cur_prov = {"id": num, "number": num, "level": num.count("."), "article": cur_art["id"],
                        "parent": parent if "." in parent else cur_art["id"], "text": m.group(2), "status": "хүчинтэй"}
            provisions.append(cur_prov)
            i += 1
            continue
        # үргэлжлэл мөр
        if cur_prov:
            cur_prov["text"] += " " + line.strip()
        elif cur_art:  # эхний хэсгээс өмнөх мөр = гарчгийн үргэлжлэл
            cur_art["title"] = clean(cur_art["title"] + " " + line)
        else:
            head_lines.append(line.strip())
        i += 1

    head = " ".join(head_lines)
    if m := RE_ADOPTED.search(head):
        law["adopted"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    title = [l for l in head_lines if l.isupper() and "УЛСЫН ХУУЛЬ" not in l and "/" not in l]
    law["title"] = clean(" ".join(title)).capitalize() + " хууль" if title else None
    law["edition"] = "Шинэчилсэн найруулга" if "ШИНЭЧИЛСЭН НАЙРУУЛГА" in head else None
    for p in provisions:
        p["text"] = clean(p["text"])
        if m := RE_EFFECTIVE.search(p["text"]):
            law["effective"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return law, chapters, sections, articles, provisions, amendments


def stem_pattern(term: str) -> str:
    """Нэр томьёоны сүүлийн үгийг хувилгаж таарах regex (ажилтан → ажилтны, ажилтанд ...)."""
    words = term.split()
    last = words[-1]
    if len(last) > 5 and re.search(rf"[^аэоөуүи][аэо]н$", last):  # тогтворгүй эгшиг: ажилтан → ажилтн-
        last = re.escape(last[:-2]) + r"(?:[аэо]н|н)"
    else:
        last = re.escape(last)
    return r"(?<![а-яөүё])" + r"\s+".join([re.escape(w) for w in words[:-1]] + [last]) + r"\w*"


def extract_terms(provisions):
    terms = []
    for p in provisions:
        if m := re.match(r'^"([^"]+)"\s+гэж\s+(.*)$', p["text"]):
            if p["article"] == "art4":
                terms.append({"id": "term:" + m.group(1), "name": m.group(1), "definition": clean(m.group(2)),
                              "defined_in": p["id"], "is_party": m.group(1) in PARTY_TERMS})
    return terms


def find_mentions(text: str, patterns):
    """patterns: [(node_id, regex)] — урт нь эхэлж таарч, давхцлыг хасна."""
    low = text.lower()
    spans, found = [], set()
    for node_id, rx in patterns:
        for m in re.finditer(rx, low):
            if any(m.start() < e and s < m.end() for s, e in spans):
                continue
            spans.append((m.start(), m.end()))
            found.add(node_id)
    return found


def expand_refs(chunk: str, art_num: int, scope: str):
    nums = []
    all_articles = re.search(r"зүйл", chunk) is not None
    parts = re.split(r"\s*(,|болон|–|-(?=\d))\s*", chunk)
    prev_sep = None
    for part in parts:
        if part in (",", "болон", "–", "-"):
            prev_sep = part
            continue
        m = re.match(r"(\d+(?:\.\d+)*)(\s+(?:дүгээр|дугаар)\s+зүйл)?", part)
        if not m:
            continue
        num = m.group(1)
        if scope == "зүйлийн" and not m.group(2) and not num.startswith(f"{art_num}."):
            num = f"{art_num}.{num}"
        target = f"art{num}" if m.group(2) or (all_articles and "." not in num) else num
        if prev_sep in ("-", "–") and nums and "." in num and "." in nums[-1]:
            a, b = nums[-1].rsplit(".", 1), num.rsplit(".", 1)
            if a[0] == b[0]:
                nums += [f"{a[0]}.{k}" for k in range(int(a[1]) + 1, int(b[1]))]
        nums.append(target)
        prev_sep = None
    return nums


def extract_links(articles, provisions, terms):
    prov_ids = {p["id"] for p in provisions}
    art_ids = {a["id"] for a in articles}
    term_patterns = sorted(((t["id"], stem_pattern(t["name"])) for t in terms), key=lambda x: -len(x[1]))
    actor_patterns = sorted(((f"actor:{n}", rx) for n, _, rx in ACTORS), key=lambda x: -len(x[1]))
    refs, laws, mentions = [], {}, []
    citations = {}  # гадны хуулийн нэр → [{from, raw_text}] (эх бичвэрт яг байгаагаар)
    for p in provisions:
        text = p["text"]
        art_num = int(p["article"][3:])
        for m in RE_XREF.finditer(text):
            for tgt in expand_refs(m.group(2), art_num, m.group(1)):
                if (tgt in prov_ids or tgt in art_ids) and tgt != p["id"]:
                    refs.append({"from": p["id"], "to": tgt, "raw_text": m.group(0)})
        for m in RE_CH_REF.finditer(text):
            refs.append({"from": p["id"], "to": f"ch{chapter_number(m.group(1).upper())}", "raw_text": m.group(0)})
        # гадны хууль
        masked = text
        for m in RE_TUKHAI_LAW.finditer(text):
            s = m.group(0)
            caps = [c.start() for c in re.finditer(rf"(?<!{W})[{CYR_U}]", s)]
            name = re.sub(r"хуул[ьи]\w*$", "хууль", s[caps[-1]:] if caps else s)
            name = clean(name)
            laws.setdefault(name, set()).add(p["id"])
            citations.setdefault(name, []).append({"from": p["id"], "raw_text": clean(s)})
            masked = masked.replace(s, " " * len(s))
        for m in re.finditer(KNOWN_LAWS, masked):
            laws.setdefault(f"{m.group(1)} хууль", set()).add(p["id"])
            citations.setdefault(f"{m.group(1)} хууль", []).append({"from": p["id"], "raw_text": clean(m.group(0))})
        # нэр томьёо, оролцогч
        is_def = p["article"] == "art4" and p["level"] == 2
        for tid in find_mentions(text, term_patterns):
            if not is_def:
                mentions.append({"from": p["id"], "to": tid})
        for aid in find_mentions(text, actor_patterns):
            mentions.append({"from": p["id"], "to": aid})
    ext = [{"id": "law:" + n, "name": n, "cited_by": sorted(v), "citations": citations[n]} for n, v in sorted(laws.items())]
    # давхардлыг арилгах
    refs = [dict(t) for t in {tuple(r.items()) for r in refs}]
    return refs, ext, mentions


def modality(text: str):
    t = text.lower()
    out = []
    if re.search(r"хориглоно|хориотой", t):
        out.append("хориглол")
    if re.search(r"үүрэгтэй|үүрэг хүлээнэ|\bзаавал\b", t):
        out.append("үүрэг")
    if re.search(r"эрхтэй|эрх эдэлнэ|\bболно\.?$", t):
        out.append("эрх")
    if re.search(r"хариуцлага хүлээлгэнэ|торгох|нөхөн төлүүлнэ", t):
        out.append("хариуцлага")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--id", default="labor-2021")
    ap.add_argument("-o", "--out", type=Path, default=Path("data/labor_law_2021.json"))
    args = ap.parse_args()

    law, chapters, sections, articles, provisions, amendments = parse_structure(pdf_text(args.pdf))
    law["id"] = args.id
    law["source_file"] = args.pdf.name
    terms = extract_terms(provisions)
    refs, ext_laws, mentions = extract_links(articles, provisions, terms)
    for p in provisions:
        p["modality"] = modality(p["text"])
    actors = [{"id": f"actor:{n}", "name": n, "category": c} for n, c, _ in ACTORS]

    out = {"law": law, "chapters": chapters, "sections": sections, "articles": articles, "provisions": provisions,
           "amendments": amendments, "terms": terms, "actors": actors, "external_laws": ext_laws,
           "references": refs, "mentions": mentions}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{law['title']} ({law['adopted']}) → {args.out}")
    for k in ("chapters", "sections", "articles", "provisions", "amendments", "terms", "actors", "external_laws", "references", "mentions"):
        print(f"  {k:15s} {len(out[k])}")


if __name__ == "__main__":
    main()
