from pipeline.sources import (CuratedILODataSource, LawForumApiSource, MockLawForumSource, MockLegalInfoSource,
                              MockParliamentSource)


def test_mock_sources_are_offline_and_sample():
    laws = MockLegalInfoSource().laws()
    assert any(l.name == "Хөдөлмөрийн тухай хууль" for l in laws)
    assert all("[ЖИШЭЭ]" in l.text for l in laws)
    bills = MockLawForumSource().projects("Хөдөлмөр")
    assert bills and all(b["title"].startswith("[ЖИШЭЭ]") for b in bills)
    assert MockParliamentSource().call("getMeetings") == []


def test_curated_sources_are_cited():
    for s in CuratedILODataSource().sources():
        assert s["url"].startswith("https://") and s["title"] and s["provision"]


def test_lawforum_stub_needs_text():
    stub = LawForumApiSource.to_draft_stub({"id": 1, "title": "x"})
    assert stub["text"] == "" and stub["cosubmitted"] == []
