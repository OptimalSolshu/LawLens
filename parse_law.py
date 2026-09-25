"""Монгол хуулийн PDF эсвэл legalinfo.mn хуудсыг бүтэцтэй JSON граф болгон задлах.

Хэрэглээ:
    python parse_law.py data/labor_law_2021.pdf --id labor-2021 -o data/labor_law_2021.json
    python parse_law.py data/raw/laws/zorchliin-tukhai-khuuli.html --id zorchliin-tukhai-khuuli \
        --title "Зөрчлийн тухай хууль" -o data/zorchliin-tukhai-khuuli.json

Дугаарлалтын гурван хэлбэр:
    "12 дугаар зүйл" + "12.3.", "12.3.1."        заалт бүтэн дугаартай (Хөдөлмөрийн тухай хууль)
    "7.1 дүгээр зүйл" + "1.", "2.1."             хэсэг зүйл дотроо дугаарлагдана → 7.1.1, 7.1.2.1
    "Хоёрдугаар зүйл." + "1."                    үгээр бичсэн зүйл (Үндсэн хууль) → 2, 2.1
"""
import argparse
import html
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
NUMBER_PART = r"\d+[⁰¹²³⁴⁵⁶⁷⁸⁹]*"  # a number, possibly with an insertion index: 9¹ (added after 9)
RE_ARTICLE = re.compile(rf"^\s*({NUMBER_PART}(?:\.{NUMBER_PART})?)\s*(?:(?:дүгээр|дугаар|дугээр|дүгаар)\s+)+зүйл\.\s*(.*)$")  # "27 дугаар дүгээр зүйл." (typo in Ойн тухай хууль)
RE_ARTICLE_WORD = re.compile(rf"^\s*((?:[{CYR_U}][{CYR_L}]+\s+)?[{CYR_U}{CYR_L}][{CYR_L}]*(?:дугаар|дүгээр))\s+зүйл\.\s*(.*)$")
RE_PROVISION = re.compile(rf"^\s*({NUMBER_PART}(?:\.{NUMBER_PART})+)\.(.*)$")
RE_ARTICLE_WORD_SUP = re.compile(rf"^\s*((?:[{CYR_U}][{CYR_L}]+\s+)?[{CYR_U}{CYR_L}][{CYR_L}]*)([\d⁰¹²³⁴⁵⁶⁷⁸⁹])\s*(?:дугаар|дүгээр)\s+зүйл\.\s*(.*)$")  # "Арван ес1 дүгээр зүйл." = 19¹
RE_LETTER_ITEM = re.compile(rf"^\s*(\d+(?:\.\d+)*)\.([{CYR_L}])\.(.*)$")  # "26.1.7.а.хөгжлийн бэрхшээлтэй хүүхдэд"
RE_NO_DOT = re.compile(rf"^\s*(\d+(?:\.\d+)+)\s+(?!(?:дэх|дахь|дох|дөх|дугаар|дүгээр)\b)([{CYR_L}].*)$")
SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
RE_BARE_ARTICLE = re.compile(rf"^\s*(\d+\.\d+)\.\s*([{CYR_U}].*)$")  # "3.6.Нийтэд тустай ажил хийлгэх шийтгэл"
RE_LOCAL_PROVISION = re.compile(r"^\s*(\d{1,3}[⁰¹²³⁴⁵⁶⁷⁸⁹]*(?:\.\d{1,3}[⁰¹²³⁴⁵⁶⁷⁸⁹]*)*)\.(?![\d⁰¹²³⁴⁵⁶⁷⁸⁹])(.*)$")
# ЕРӨНХИЙ АНГИ, ТУСГАЙ АНГИ, I ХЭСЭГ, НЭГДҮГЭЭР ХЭСЭГ, I ДЭД ХЭСЭГ: бүлгээс дээших бүтэц
RE_PART_HEAD = re.compile(rf"^\s*(?:(?:[IVXLC]+|[{CYR_U}]+)\s+(?:ДЭД\s+)?ХЭСЭГ|[{CYR_U} ]+\s+АНГИ)\s*$")
RE_AMEND = re.compile(
    r"^\s*/Энэ\s+(\S+)\s+(\d{4})\s+оны\s+(\d+)\s+(?:дүгээр|дугаар)\s+сарын\s+(\d+)-\S*\s+өдрийн\s+хуулиар\s+(.+?)\.?/\s*$"
)
RE_SIGNED = re.compile(r"^\s*МОНГОЛ УЛСЫН (?:АРДЫН )?ИХ ХУРЛЫН ДАРГ\S*(?:\s+(.+?))?\s*$")
RE_ADOPTED = re.compile(r"(\d{4})\s+оны\s+(\d+)\s+(?:(?:дүгээр|дугаар)\s+)?сарын\s+(\d+)(?:-\S+)?\s+өдөр")
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


RE_HTML_BLOCK = re.compile(r'<div class="w-100 pull-left responsive_mobile[^"]*"[^>]*>')


def html_text(page: str) -> str:
    """legalinfo.mn detail page -> one line per paragraph, in the layout parse_structure reads.
    The law body is a run of `responsive_mobile` blocks; print buttons and the hidden
    comparison popups are dropped."""
    starts = [m.start() for m in RE_HTML_BLOCK.finditer(page)]
    lines = []
    for a, b in zip(starts, starts[1:] + [None]):
        chunk = re.split(r"<script|<style", page[a:b])[0]
        chunk = re.sub(r'<span class="(?:icon-s|pull-right print-zuil)[^"]*".*?</span>', "", chunk, flags=re.S)
        chunk = re.sub(r'<p class="\d+[^"]*" style="display:none[^"]*"[^>]*>.*?</p>', "", chunk, flags=re.S)
        chunk = re.sub(r"(?i)</p>|<br\s*/?>|</div>|</tr>", "\n", chunk)
        chunk = re.sub(r"(?i)<sup\b[^>]*>\s*(\d+)(?:\s|&nbsp;|\xa0)*</sup>", lambda m: m.group(1).translate(SUPERSCRIPT), chunk)
        chunk = re.sub(r"(?i)</?(?:span|b|i|u|strong|em|font|a|sup|sub|o:p)\b[^>]*>", "", chunk)  # inline: "5<span>1</span>" = 51
        chunk = html.unescape(re.sub(r"<[^>]+>", " ", chunk)).replace("\xa0", " ")
        chunk = re.sub(r'(?:[a-z-]+\s*:\s*[^;"<>\n]*;?\s*)+"\s*>', " ", chunk)  # style="…; >…"> left by broken tags
        lines += [clean(line) for line in chunk.split("\n")]
    return "\n".join(line for line in lines if line)


TENS = {"арав": 10, "арван": 10, "хорь": 20, "хорин": 20, "гуч": 30, "гучин": 30, "дөч": 40, "дөчин": 40,
        "тавь": 50, "тавин": 50, "жар": 60, "жаран": 60, "дал": 70, "далан": 70, "ная": 80, "наян": 80,
        "ер": 90, "ерэн": 90}
UNITS = {"нэг": 1, "хоёр": 2, "гурав": 3, "дөрөв": 4, "тав": 5, "зургаа": 6, "зурга": 6, "долоо": 7, "дол": 7,
         "найм": 8, "ес": 9}


def ordinal_number(words: str) -> int:
    """'Хорин нэгдүгээр', 'ГУЧИН ХОЁРДУГААР', 'Далдугаар' -> 21, 32, 70 (0 if unknown)."""
    parts = re.sub(r"(дугаар|дүгээр)$", "", words.lower().strip()).split()
    n = 0
    for w in parts:
        if w in TENS:
            n += TENS[w]
        elif w in UNITS:
            n += UNITS[w]
        else:
            return 0
    return n


def chapter_number(word: str) -> int:
    if n := ordinal_number(word):
        return n
    word = word.replace(" ", "")
    n = 10 if word.startswith("АРВАН") else 0
    rest = word[5:] if n else word
    for k, v in ORDINALS.items():
        if rest.startswith(k):
            return n + v
    return n


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def normalize_number(line: str) -> str:
    """Typing slips at the start of a numbered line on legalinfo.mn."""
    line = re.sub(r"^(\s*\d+(?:\.\d+)*)\s+\.(?=\S)", r"\1.", line)  # "174.3 ./Энэ хэсгийг"
    line = re.sub(rf"^(\s*\d+(?:[⁰¹²³⁴⁵⁶⁷⁸⁹]+|(?:\.\d+[⁰¹²³⁴⁵⁶⁷⁸⁹]*)+))\.\s+(\d+[⁰¹²³⁴⁵⁶⁷⁸⁹]*\.)(?=\s*[{CYR_U}{CYR_L}])", r"\1.\2",
                  line)  # "13¹. 2. Монгол Улсаас" = 13¹.2.
    line = re.sub(r"^(\s*\d+(?:\.\d+)*\.)З\.", r"\g<1>3.", line)  # "7.З." : letter З for 3
    return re.sub(rf"^(\s*\d+(?:\.\d+)*\.)3(?=[{CYR_L}])", r"\1З", line)  # "1.3өвшөөрөлгүй": digit 3 for З


def is_structural(line: str) -> bool:
    return bool(RE_CHAPTER.match(line) or RE_SECTION.match(line) or RE_PART_HEAD.match(line)
                or RE_ARTICLE.match(line) or RE_ARTICLE_WORD.match(line) or RE_LOCAL_PROVISION.match(line))


def is_heading(line: str) -> bool:
    """An all-capitals line (АНГИ / ХЭСЭГ titles, running heads): never provision text."""
    s = line.strip()
    return len(s) > 3 and s.isupper() and re.search(rf"[{CYR_U}]{{3}}", s) is not None


def uses_local_numbers(lines: list[str]) -> bool:
    """True when parts are numbered inside their article ("1.", "2.1.") rather than in full ("12.1.")."""
    if any(RE_ARTICLE_WORD.match(l) or ((m := RE_ARTICLE.match(l)) and "." in m.group(1)) for l in lines):
        return True
    full = sum(1 for l in lines if RE_PROVISION.match(l))
    single = sum(1 for l in lines if re.match(r"^\s*\d{1,3}\.(?!\d)\S", l))
    return full < single


def latest_versions(provisions: list[dict]) -> list[dict]:
    """legalinfo.mn keeps a repealed provision next to the one later added under the same
    number, and shows an amended wording (in force from a later date) after the old one.
    Keep one per number: the later one, unless it is repealed and the earlier is not."""
    out: dict[str, dict] = {}
    for p in provisions:
        old = out.get(p["id"])
        if old is None or not (p["status"] == "хүчингүй" and old["status"] != "хүчингүй"):
            out[p["id"]] = p if old is None else {**p, "id": old["id"]}
    return list(out.values())


def parse_structure(text: str, html_input: bool = False):
    lines = text.splitlines()
    law = {"title": None, "adopted": None, "signed_by": None, "effective": None}
    chapters, sections, articles, provisions, amendments = [], [], [], [], []
    cur_ch = cur_sec = cur_art = cur_prov = None
    head_lines = []
    local = uses_local_numbers(lines)
    dotted_articles = any((m := RE_ARTICLE.match(l)) and "." in m.group(1) for l in lines)
    i = 0
    while i < len(lines):
        line = lines[i] = normalize_number(lines[i])
        if html_input and cur_art and not local and (nd := RE_NO_DOT.match(line)) \
                and nd.group(1).rsplit(".", 1)[0] in {p["id"] for p in provisions[-50:]}:
            line = f"{nd.group(1)}.{nd.group(2)}"  # "9.1.3 машин механизм": number without its closing dot
        if RE_FOOTER.match(line) or not line.strip():
            i += 1
            continue
        if m := RE_SIGNED.match(line):
            law["signed_by"] = m.group(1) or (clean(lines[i + 1]) if i + 1 < len(lines) else None)
            break  # the law ends at the signature; what follows is annexes / page chrome
        if m := RE_CHAPTER.match(line):
            title = []
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines) and not lines[i].strip().isupper() and not is_structural(lines[i]):
                title.append(lines[i].strip())  # sentence-case chapter title (legalinfo.mn)
                i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i].strip().isupper()) and not RE_ARTICLE.match(lines[i]) \
                    and not RE_CHAPTER.match(lines[i]) and not RE_PART_HEAD.match(lines[i]):
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
        if RE_PART_HEAD.match(line):  # АНГИ / ХЭСЭГ and their capitalised titles
            i += 1
            while i < len(lines) and (not lines[i].strip() or is_heading(lines[i])) and not is_structural(lines[i]):
                i += 1
            continue
        m = RE_ARTICLE.match(line)
        if not m and dotted_articles and (bare := RE_BARE_ARTICLE.match(line)):
            nxt = next((l.strip() for l in lines[i + 1:] if l.strip()), "")
            if nxt.startswith("/Энэ зүйлийг"):  # an added article printed without "дугаар зүйл"
                m = bare
        word = None if m else RE_ARTICLE_WORD.match(line)
        sup = None if (m or word) else RE_ARTICLE_WORD_SUP.match(line)
        if sup and ordinal_number(sup.group(1) + "дүгээр"):
            raw = f"{ordinal_number(sup.group(1) + 'дүгээр')}{sup.group(2).translate(SUPERSCRIPT)}"
            cur_art = {"id": f"art{raw}", "number": raw, "title": clean(sup.group(3)),
                       "chapter": cur_ch["id"] if cur_ch else None, "text": ""}
            articles.append(cur_art)
            cur_prov = None
            i += 1
            continue
        if m or (word and ordinal_number(word.group(1))):
            raw = m.group(1) if m else str(ordinal_number(word.group(1)))
            cur_art = {"id": f"art{raw}", "number": int(raw) if raw.isdecimal() else raw, "title": clean((m or word).group(2)),
                       "chapter": cur_ch["id"] if cur_ch else None, "text": ""}
            articles.append(cur_art)
            cur_prov = None
            i += 1
            continue
        if m := RE_AMEND.match(line):
            target = cur_prov or cur_art
            if target is None:
                i += 1
                continue
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
        if cur_prov and (li := RE_LETTER_ITEM.match(line)) and (
                li.group(1) == cur_prov["id"] or f"{cur_art['number']}.{li.group(1)}" == cur_prov["id"]):
            cur_prov["text"] += f" {li.group(2)}.{li.group(3).strip()}"
            i += 1
            continue
        if (cur_art and not local and isinstance(cur_art["number"], int) and (m := RE_PROVISION.match(line))
                and m.group(1) == f"{cur_art['number'] + 1}.1"):
            # the next article's first part with no heading line (Нийгмийн халамжийн тухай хууль: 3.1 after 2)
            cur_art = {"id": f"art{cur_art['number'] + 1}", "number": cur_art["number"] + 1, "title": "",
                       "chapter": cur_ch["id"] if cur_ch else None, "text": ""}
            articles.append(cur_art)
        num = None
        if cur_art and local:
            if (m := RE_LOCAL_PROVISION.match(line)) and int(m.group(1).split(".")[0].rstrip("⁰¹²³⁴⁵⁶⁷⁸⁹")) <= 200:
                num = f"{cur_art['number']}.{m.group(1)}"
        elif cur_art and (m := RE_PROVISION.match(line)) and m.group(1).split(".")[0] == str(cur_art["number"]):
            num = m.group(1)
        if num:
            parent = num.rsplit(".", 1)[0]
            cur_prov = {"id": num, "number": num, "level": num.count("."), "article": cur_art["id"],
                        "parent": parent if parent != str(cur_art["number"]) else cur_art["id"],
                        "text": m.group(2), "status": "хүчинтэй"}
            provisions.append(cur_prov)
            if (a := RE_AMEND.match(m.group(2))) and "хүчингүй" in a.group(5):  # "12.3./Энэ хэсгийг ... хүчингүй .../"
                cur_prov["status"] = "хүчингүй"
            i += 1
            continue
        if cur_art and html_input and is_heading(line):
            i += 1
            continue
        # үргэлжлэл мөр
        if cur_prov:
            cur_prov["text"] += " " + line.strip()
        elif cur_art and html_input:  # legalinfo.mn: гарчиг нэг мөрөнд; дараагийн мөр нь зүйлийн бичвэр
            cur_art["text"] = clean(cur_art["text"] + " " + line)
        elif cur_art:  # эхний хэсгээс өмнөх мөр = гарчгийн үргэлжлэл
            cur_art["title"] = clean(cur_art["title"] + " " + line)
        else:
            head_lines.append(line.strip())
        i += 1

    provisions = latest_versions(provisions)
    head = " ".join(head_lines)
    if m := RE_ADOPTED.search(head):
        law["adopted"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    title = [l for l in head_lines if l.isupper() and "УЛСЫН ХУУЛЬ" not in l and "/" not in l]
    law["title"] = clean(" ".join(title)).capitalize() + " хууль" if title else None
    law["edition"] = "Шинэчилсэн найруулга" if "ШИНЭЧИЛСЭН НАЙРУУЛГА" in head.upper() else None
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


def expand_refs(chunk: str, art_num: str, scope: str):
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
        art_num = p["article"][3:]
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
        for tid in sorted(find_mentions(text, term_patterns)):
            if not is_def:
                mentions.append({"from": p["id"], "to": tid})
        for aid in sorted(find_mentions(text, actor_patterns)):
            mentions.append({"from": p["id"], "to": aid})
    ext = [{"id": "law:" + n, "name": n, "cited_by": sorted(v), "citations": citations[n]} for n, v in sorted(laws.items())]
    # давхардлыг арилгах
    refs = list({tuple(r.items()): r for r in refs}.values())
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
    ap.add_argument("pdf", type=Path, help="law PDF, or a saved legalinfo.mn detail page (.html)")
    ap.add_argument("--id", default="labor-2021")
    ap.add_argument("--title", help="official name (overrides the title read from the document head)")
    ap.add_argument("-o", "--out", type=Path, default=Path("data/labor_law_2021.json"))
    args = ap.parse_args()

    if args.pdf.suffix.lower() in (".html", ".htm"):
        text, html_input = html_text(args.pdf.read_text(encoding="utf-8")), True
    else:
        text, html_input = pdf_text(args.pdf), False
    law, chapters, sections, articles, provisions, amendments = parse_structure(text, html_input)
    if args.title:
        law["title"] = args.title
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
