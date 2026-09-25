"""Bills in the build: amendment wording, and a revised law that replaces a law under a new title."""
from pipeline import _backend  # noqa: F401  (sys.path for backend/app)
from app.ai.embeddings import DemoEmbedder
from app.ai.relations import PrecomputedRelationService
from pipeline.build import BuildInput, build

URL = "https://example.org/lawlens-sample"


def law(law_id, name, articles):
    return {"law_id": law_id, "name": name, "former_names": [], "short_names": [], "adopted_date": None,
            "source_url": URL, "articles": [{"article_id": f"{law_id}:{n}", "number": n, "parent_number": None,
                                             "title": None, "text": t} for n, t in articles]}


LAWS = [
    law("osh", "[ЖИШЭЭ] Аюулгүй ажиллагааны тухай хууль", [("15.1", "[ЖИШЭЭ] Тусгай хувцсаар хангана.")]),
    law("other", "[ЖИШЭЭ] Хэмнэлтийн тухай хууль",
        [("8.2", "[ЖИШЭЭ] Аюулгүй ажиллагааны тухай хуулийн 15.1-д заасан хувцас хамаарахгүй.")]),
]


def run(draft):
    inp = BuildInput(laws=LAWS, drafts=[draft], sample=True)
    return build(inp, DemoEmbedder(), PrecomputedRelationService(None)).drafts[0]


def test_revised_law_under_new_title_replaces_the_named_law():
    d = run({"lawforum_id": "1", "title": "[ЖИШЭЭ] АЮУЛГҮЙ АЖИЛЛАГАА, ЭРҮҮЛ МЭНДИЙН ТУХАЙ (Шинэчилсэн найруулга)",
             "source_url": URL, "text": "1 дүгээр зүйл.[ЖИШЭЭ] Энэ хуулийн 5.1-д заасныг хүчингүй болсонд тооцсугай.",
             "target_law": "[ЖИШЭЭ] Аюулгүй ажиллагааны тухай хууль",
             "new_name": "[ЖИШЭЭ] Аюулгүй ажиллагаа, эрүүл мэндийн тухай хууль",
             "cosubmitted": [{"title": "[ЖИШЭЭ] Хэмнэлтийн тухай хуульд өөрчлөлт оруулах тухай", "text": ""}]})
    assert d.target_law_id == "osh" and d.new_name == "[ЖИШЭЭ] Аюулгүй ажиллагаа, эрүүл мэндийн тухай хууль"
    assert d.operations == [] and d.amended_article_ids == []  # the new law's text is not amendment wording
    assert d.cosubmitted_law_ids == ["other"]


def test_amendment_bill_targets_the_law_in_its_title():
    d = run({"lawforum_id": "2", "title": "[ЖИШЭЭ] Аюулгүй ажиллагааны тухай хуульд өөрчлөлт оруулах тухай",
             "source_url": URL, "cosubmitted": [],
             "text": "1 дүгээр зүйл.[ЖИШЭЭ] Аюулгүй ажиллагааны тухай хуулийн 15.1 дэх хэсгийг хүчингүй болсонд тооцсугай."})
    assert d.target_law_id == "osh" and d.new_name is None
    assert d.amended_article_ids == ["osh:15.1"]
