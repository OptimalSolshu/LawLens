"""Fails when a fixture in contracts/fixtures drifts from app/schemas/api.py."""
import re

import pytest

from app import config, fixtures

ARTICLE_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*:[0-9]+(\.[0-9]+)*$")
FIXTURE_FILES = sorted(p.stem for p in config.FIXTURES_DIR.glob("*.json"))
BANNED = ["зөрчилтэй", "хууль бус", "зөрчсөн нь тогтоогдсон"]


def test_every_fixture_is_registered():
    assert set(FIXTURE_FILES) == set(fixtures.RESPONSE_TYPES)


@pytest.mark.parametrize("name", FIXTURE_FILES)
def test_fixture_is_marked_sample(name):
    doc = fixtures.load(name)
    assert doc["_sample"] is True
    assert {"endpoint", "request", "response"} <= doc.keys()


@pytest.mark.parametrize("name", sorted(fixtures.RESPONSE_TYPES))
def test_fixture_matches_contract(name):
    fixtures.response(name)


@pytest.mark.parametrize("name", sorted(fixtures.REQUEST_BODY_TYPES))
def test_fixture_request_matches_contract(name):
    fixtures.REQUEST_BODY_TYPES[name].model_validate(fixtures.load(name)["request"]["body"])


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


@pytest.mark.parametrize("name", FIXTURE_FILES)
def test_ids_follow_convention(name):
    for obj in _walk(fixtures.load(name)["response"]):
        aid = obj.get("article_id")
        if isinstance(aid, str):
            assert ARTICLE_ID.match(aid), aid
            if "law_id" in obj:
                assert aid.startswith(obj["law_id"] + ":"), aid
        if isinstance(obj.get("source_url"), str):
            assert obj["source_url"].startswith("https://example.org/"), "sample laws must not link real sources"


@pytest.mark.parametrize("name", FIXTURE_FILES)
def test_sample_texts_are_labelled_and_wording_is_not_a_verdict(name):
    doc = fixtures.load(name)
    for obj in _walk(doc["response"]):
        for key in ("text", "snippet", "suggested_text"):
            if isinstance(obj.get(key), str) and obj[key]:
                heading_or_citation = obj[key] in (obj.get("title"), obj.get("raw_text")) or obj.get("text") == ""
                assert obj[key].startswith("[ЖИШЭЭ]") or heading_or_citation, (key, obj[key][:60])
    blob = str(doc["response"]).lower()
    for word in BANNED:
        assert word not in blob
