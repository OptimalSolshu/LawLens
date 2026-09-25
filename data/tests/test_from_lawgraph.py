from pipeline.from_lawgraph import convert_law, convert_refs

# [ЖИШЭЭ] invented structure, not real law text.
DOC = {
    "law": {"id": "sample-law", "title": "Жишээ тухай хууль", "adopted": "2020-01-01"},
    "articles": [{"id": "art1", "number": 1, "title": "[ЖИШЭЭ]", "text": ""},
                 {"id": "art2", "number": 2, "title": "[ЖИШЭЭ]", "text": ""}],
    "provisions": [
        {"id": "1.1", "number": "1.1", "parent": "art1", "text": "[ЖИШЭЭ]", "status": "хүчинтэй"},
        {"id": "1.2", "number": "1.2", "parent": "art1", "text": "[ЖИШЭЭ]", "status": "хүчингүй"},
        {"id": "1.2.1", "number": "1.2.1", "parent": "1.2", "text": "[ЖИШЭЭ]", "status": "хүчинтэй"},
    ],
    "amendments": [],
    "references": [
        {"from": "1.1", "to": "1.2.1", "raw_text": "энэ хуулийн 1.2.1-д"},
        {"from": "1.1", "to": "art2", "raw_text": "энэ хуулийн 2 дугаар зүйлд"},
        {"from": "1.1", "to": "ch1", "raw_text": "энэ хуулийн нэгдүгээр бүлэг"},
    ],
    "external_laws": [{"name": "Тусгай зөвшөөрлийн тухай хууль", "citations": [
        {"from": "1.1", "raw_text": "Тусгай зөвшөөрлийн тухай хуулийн"}]}],
}


def test_convert():
    law = convert_law(DOC, "https://example.org/sample", {})
    assert [a.number for a in law.articles] == ["1", "2", "1.1"]  # repealed 1.2 and its child dropped
    assert law.articles[2].parent_number == "1"

    resolve = {"Тусгай зөвшөөрлийн тухай хууль": ("zovshoorliin-tukhai-khuuli", "Тусгай зөвшөөрлийн тухай хууль", True)}
    refs = convert_refs(DOC, law, resolve)
    assert len(refs) == 3  # chapter ref skipped
    missing, art, ext = refs
    assert missing.target_missing and missing.to_article_id is None
    assert art.to_number == "2" and art.to_article_id == "sample-law:2"
    assert ext.to_law_id == "zovshoorliin-tukhai-khuuli" and ext.uses_old_name and ext.to_number is None
