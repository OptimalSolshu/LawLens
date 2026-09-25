"""Parser tests. All law texts here are invented [ЖИШЭЭ] strings, not real provisions."""
import pytest

from app.parser import LawNameRegistry, extract_references, parse_amendments, parse_law_text
from app.parser.names import canonical_form
from app.parser.normalize import stem

LABOR = "khodolmoriin-tukhai-khuuli"
OSH = "khodolmoriin-ayuulgui-baidal-eruul-akhuin-tukhai-khuuli"
HYGIENE = "eruul-akhuin-tukhai-khuuli"
PERMIT = "zovshoorliin-tukhai-khuuli"
CIVIL = "irgenii-khuuli"
ZORCHIL = "zorchliin-tukhai-khuuli"


@pytest.fixture
def reg():
    r = LawNameRegistry()
    r.add_law(LABOR, "Хөдөлмөрийн тухай хууль")
    r.add_law(OSH, "Хөдөлмөрийн аюулгүй байдал, эрүүл ахуйн тухай хууль", former=["Хөдөлмөр хамгааллын тухай хууль"])
    r.add_law(HYGIENE, "Эрүүл ахуйн тухай хууль")
    r.add_law(PERMIT, "Зөвшөөрлийн тухай хууль", former=["Тусгай зөвшөөрлийн тухай хууль"])
    r.add_law(CIVIL, "Иргэний хууль")
    r.add_law("undsen-khuuli", "Үндсэн хууль", aliases=["Монгол Улсын Үндсэн хууль"], short=["ҮХ"])
    return r


NUMBERS = {
    LABOR: {"6", "6.1", "6.8", "12", "15", "15.1", "80", "80.1", "80.2", "80.1.4", "80.1.5", "80.1.6"},
    OSH: {"12", "12.1", "3.1.4"},
    PERMIT: {"15", "15.1", "15.2"},
}


def refs(text, reg, frm="zorchliin-tukhai-khuuli:6.1", numbers=NUMBERS, **kw):
    return extract_references(text, from_article_id=frm, registry=reg, numbers_by_law=numbers, **kw)


# ---- structure --------------------------------------------------------------

def test_article_and_clause_detection():
    text = """ЖИШЭЭ ТУХАЙ ХУУЛЬ
НЭГДҮГЭЭР БҮЛЭГ
12 дугаар зүйл. Ажлын цаг
12.1.[ЖИШЭЭ] Эхний хэсэг
үргэлжлэл мөр.
12.3.1.[ЖИШЭЭ] Дэд заалт
13 дүгээр зүйл.Амралт
13.1.[ЖИШЭЭ] Амралтын хэсэг
14.1.буруу дугаартай мөр нь үргэлжлэл болно
"""
    arts = parse_law_text(text, "sample")
    assert [(a.number, a.parent_number) for a in arts] == [
        ("12", None), ("12.1", "12"), ("12.3.1", "12.3"), ("13", None), ("13.1", "13")]
    assert arts[0].title == "Ажлын цаг"
    assert arts[1].text == "[ЖИШЭЭ] Эхний хэсэг үргэлжлэл мөр."
    assert arts[3].title == "Амралт"
    assert arts[4].text.endswith("үргэлжлэл болно")
    assert arts[1].article_id == "sample:12.1"


# ---- law names --------------------------------------------------------------

@pytest.mark.parametrize("form", ["хууль", "хуулийн", "хуулиар", "хуульд", "хуулийг", "хуулиас"])
def test_case_endings(reg, form):
    [m] = reg.find(f"[ЖИШЭЭ] ажилтныг Хөдөлмөрийн тухай {form} заасны дагуу")
    assert m.entry.law_id == LABOR
    assert canonical_form(m.text) == "Хөдөлмөрийн тухай хууль"


def test_longer_name_beats_substring(reg):
    [m] = reg.find("[ЖИШЭЭ] Хөдөлмөрийн аюулгүй байдал, эрүүл ахуйн тухай хуульд заасан")
    assert m.entry.law_id == OSH  # not "Эрүүл ахуйн тухай хууль"
    [m] = reg.find("[ЖИШЭЭ] Эрүүл ахуйн тухай хуульд заасан")
    assert m.entry.law_id == HYGIENE


def test_former_short_alias_resolve_to_canonical(reg):
    former = reg.find("Тусгай зөвшөөрлийн тухай хуулийн")[0].entry
    assert (former.law_id, former.kind, former.canonical) == (PERMIT, "former", "Зөвшөөрлийн тухай хууль")
    # former name is longer and contains the current name: the former name must win
    assert reg.find("Тусгай зөвшөөрлийн тухай хуулийн")[0].text == "Тусгай зөвшөөрлийн тухай хуулийн"
    assert reg.resolve("Монгол Улсын Үндсэн хуулийн").law_id == "undsen-khuuli"
    assert reg.resolve("ҮХ").kind == "short"


def test_whitespace_and_case_insensitive(reg):
    [m] = reg.find("ХӨДӨЛМӨРИЙН  ТУХАЙ\nхуулийн")
    assert m.entry.law_id == LABOR


def test_unknown_tukhai_law_gets_slug(reg):
    [m] = reg.find("[ЖИШЭЭ] Ажил олгогч Гамшгаас хамгаалах тухай хуулийн 4.1.2-т заасан")
    assert m.entry.kind == "unknown"
    assert m.entry.law_id == "gamshgaas-khamgaalakh-tukhai-khuuli"
    assert m.text.startswith("Гамшгаас")


# ---- references -------------------------------------------------------------

def test_dotted_number(reg):
    [r] = refs("[ЖИШЭЭ] Хөдөлмөрийн тухай хуулийн 15.1-д заасан", reg)
    assert (r.to_law_id, r.to_number, r.to_article_id) == (LABOR, "15.1", f"{LABOR}:15.1")
    assert r.raw_text == "Хөдөлмөрийн тухай хуулийн 15.1-д"
    assert (r.type if hasattr(r, "type") else "fact", r.confidence, r.method) == ("fact", 1.0, "regex")


def test_article_part_form(reg):
    [r] = refs("[ЖИШЭЭ] Хөдөлмөрийн тухай хуулийн 6 дугаар зүйлийн 8 дахь хэсэгт заасан", reg)
    assert r.to_number == "6.8" and not r.target_missing


@pytest.mark.parametrize("loc", ["дахь", "дэх", "дох", "дөх"])
def test_locative_variants(reg, loc):
    [r] = refs(f"[ЖИШЭЭ] Хөдөлмөрийн тухай хуулийн 6 дугаар зүйлийн 1 {loc} хэсэгт", reg)
    assert r.to_number == "6.1"


def test_article_part_point_list(reg):
    out = refs("[ЖИШЭЭ] Хөдөлмөрийн тухай хуулийн 80 дугаар зүйлийн 1 дэх хэсгийн 4, 5 болон 6 дахь заалтад", reg)
    assert [r.to_number for r in out] == ["80.1.4", "80.1.5", "80.1.6"]


def test_whole_article(reg):
    [r] = refs("[ЖИШЭЭ] Хөдөлмөрийн тухай хуулийн 12 дугаар зүйлд заасан", reg)
    assert r.to_number == "12" and r.to_article_id == f"{LABOR}:12"


def test_this_law_list_and_range(reg):
    out = refs("[ЖИШЭЭ] энэ хуулийн 80.1.4, 80.1.5-д болон 80.2-т", reg, frm=f"{LABOR}:91.1")
    assert [(r.to_law_id, r.to_number, r.matched_name) for r in out] == [
        (LABOR, "80.1.4", "энэ хууль"), (LABOR, "80.1.5", "энэ хууль"), (LABOR, "80.2", "энэ хууль")]
    out = refs("[ЖИШЭЭ] Энэ хуулийн 80.1.4-80.1.6-д", reg, frm=f"{LABOR}:91.1")
    assert [r.to_number for r in out] == ["80.1.4", "80.1.5", "80.1.6"]


def test_article_numbered_by_chapter(reg):
    reg.add_law(ZORCHIL, "Зөрчлийн тухай хууль")
    numbers = {**NUMBERS, ZORCHIL: {"7.1", "7.1.1", "7.1.2", "7.1.2.1"}}
    out = refs("[ЖИШЭЭ] Зөрчлийн тухай хуулийн 7.1 дүгээр зүйлийн 1 дэх хэсэг, 7.1 дүгээр зүйлийн 2 дахь хэсгийн 1 дэх заалт",
               reg, frm=f"{LABOR}:6.1", numbers=numbers)
    assert [(r.to_number, r.target_missing) for r in out] == [("7.1.1", False), ("7.1.2.1", False)]
    [r] = refs("[ЖИШЭЭ] Зөрчлийн тухай хуулийн 7.1 дүгээр зүйлд", reg, frm=f"{LABOR}:6.1", numbers=numbers)
    assert r.to_article_id == f"{ZORCHIL}:7.1"
    # "энэ зүйлийн" inside such a code refers to article 7.1, not to a non-existent article 7
    [r] = refs("[ЖИШЭЭ] энэ зүйлийн 2 дахь хэсэгт", reg, frm=f"{ZORCHIL}:7.1.1", numbers=numbers)
    assert r.to_article_id == f"{ZORCHIL}:7.1.2"


def test_constitution_part_called_zaalt(reg):
    [r] = refs("[ЖИШЭЭ] Монгол Улсын Үндсэн хуулийн 16 дугаар зүйлийн 4 дэх заалтад", reg)
    assert (r.to_law_id, r.to_number) == ("undsen-khuuli", "16.4")


def test_this_article_part(reg):
    [r] = refs("[ЖИШЭЭ] энэ зүйлийн 2 дахь хэсэгт заасан", reg, frm=f"{LABOR}:80.1")
    assert r.to_article_id == f"{LABOR}:80.2"


def test_this_law_without_number_is_ignored(reg):
    assert refs("[ЖИШЭЭ] энэ хуульд заасан журмаар", reg, frm=f"{LABOR}:80.1") == []


def test_named_law_without_number_is_whole_law_reference(reg):
    [r] = refs("[ЖИШЭЭ] харилцааг Иргэний хуулиар зохицуулна.", reg)
    assert (r.to_law_id, r.to_number, r.to_article_id, r.target_missing) == (CIVIL, None, None, False)


def test_former_name_flagged(reg):
    [r] = refs("[ЖИШЭЭ] Тусгай зөвшөөрлийн тухай хуулийн 15.1-д", reg)
    assert r.uses_old_name and r.to_law_id == PERMIT and r.to_article_id == f"{PERMIT}:15.1"
    assert r.matched_name == "Тусгай зөвшөөрлийн тухай хууль"


def test_missing_target_kept_with_law(reg):
    [r] = refs("[ЖИШЭЭ] Хөдөлмөрийн тухай хуулийн 131.1-д заасан", reg,
               renumbering={LABOR: {"131.1": "80.2"}})
    assert r.target_missing and r.to_article_id is None
    assert r.to_law_id == LABOR and r.to_number == "131.1"
    assert r.current_number == "80.2"


def test_old_name_and_old_number_together(reg):
    [r] = refs("[ЖИШЭЭ] Хөдөлмөр хамгааллын тухай хуулийн 27.3-т", reg)
    assert r.uses_old_name and r.target_missing and r.to_law_id == OSH


def test_unknown_text_law_is_never_missing(reg):
    [r] = refs("[ЖИШЭЭ] Иргэний хуулийн 343 дугаар зүйлд", reg)
    assert r.to_number == "343" and r.to_article_id is None and not r.target_missing


def test_multiple_laws_in_one_sentence(reg):
    out = refs("[ЖИШЭЭ] Хөдөлмөрийн тухай хуулийн 15.1, Зөвшөөрлийн тухай хуулийн 15.2-т", reg)
    assert [(r.to_law_id, r.to_number) for r in out] == [(LABOR, "15.1"), (PERMIT, "15.2")]


# ---- amendments -------------------------------------------------------------

def test_amendment_wording(reg):
    text = (
        '1 дүгээр зүйл.[ЖИШЭЭ] Хөдөлмөрийн тухай хуулийн 80.1 дэх хэсгийн "40 цаг" гэснийг "38 цаг" гэж өөрчилсүгэй.\n'
        '2 дугаар зүйл.[ЖИШЭЭ] Хөдөлмөрийн тухай хуулийн 15.1-ийн "ажилтан" гэсний дараа "ажил горилогч" гэж нэмсүгэй.\n'
        '3 дугаар зүйл.[ЖИШЭЭ] Тусгай зөвшөөрлийн тухай хуулийн 15.2-ын “хүчингүй болгоно” гэснийг хассугай.\n'
        '4 дүгээр зүйл.[ЖИШЭЭ] Хөдөлмөрийн тухай хуулийн 6.8 дахь хэсгийг хүчингүй болсонд тооцсугай.\n'
    )
    ops = parse_amendments(text, registry=reg, numbers_by_law=NUMBERS)
    assert [(o.op, o.law_id, o.number) for o in ops] == [
        ("replace", LABOR, "80.1"), ("insert", LABOR, "15.1"), ("delete", PERMIT, "15.2"), ("repeal", LABOR, "6.8")]
    assert (ops[0].old_text, ops[0].new_text) == ("40 цаг", "38 цаг")
    assert (ops[1].old_text, ops[1].new_text) == ("ажилтан", "ажил горилогч")
    assert ops[2].old_text == "хүчингүй болгоно" and ops[2].uses_old_name


def test_stemming():
    assert stem("хөдөлмөрийн") == "хөдөлмөр"
    assert stem("хуулийн") == "хуул"
    assert stem("80.1") == "80.1"


def test_article_lists_and_ranges(reg):
    out = refs("[ЖИШЭЭ] энэ хуулийн 6, 12 болон 15 дугаар зүйлд", reg, frm=f"{LABOR}:80.1")
    assert [r.to_number for r in out] == ["6", "12", "15"]
    out = refs("[ЖИШЭЭ] Хөдөлмөрийн тухай хуулийн 12-15 дугаар зүйлд", reg)
    assert [r.to_number for r in out] == ["12", "13", "14", "15"]
    assert [r.target_missing for r in out] == [False, True, True, False]


def test_rename_and_quoted_names_are_not_citations(reg):
    text = ('1 дүгээр зүйл.[ЖИШЭЭ] Зөвшөөрлийн тухай хуулийн нэрийг "Зөвшөөрөл, мэдэгдлийн тухай хууль" гэж өөрчилсүгэй.\n'
            '2 дугаар зүйл.[ЖИШЭЭ] Хөдөлмөрийн тухай хуулийн 15.1-ийн "Тусгай зөвшөөрлийн тухай хуулийн" гэснийг '
            '"Зөвшөөрлийн тухай хуулийн" гэж өөрчилсүгэй.')
    ops = parse_amendments(text, registry=reg, numbers_by_law=NUMBERS)
    assert [(o.op, o.law_id, o.number, o.new_text) for o in ops] == [
        ("rename", PERMIT, None, "Зөвшөөрөл, мэдэгдлийн тухай хууль"),
        ("replace", LABOR, "15.1", "Зөвшөөрлийн тухай хуулийн")]
