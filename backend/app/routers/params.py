"""Validated path / query parameters. Ids are opaque slugs; nothing reaches Cypher unparameterised."""
from typing import Annotated

from fastapi import Path, Query

LAW_ID = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
ARTICLE_ID = r"^[a-z0-9]+(?:-[a-z0-9]+)*:\d+(?:\.\d+)*$"
DRAFT_ID = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"

LawId = Annotated[str, Path(pattern=LAW_ID, max_length=200)]
ArticleId = Annotated[str, Path(pattern=ARTICLE_ID, max_length=240)]
DraftId = Annotated[str, Path(pattern=DRAFT_ID, max_length=200)]
OptLawId = Annotated[str | None, Query(pattern=LAW_ID, max_length=200)]
OptArticleId = Annotated[str | None, Query(pattern=ARTICLE_ID, max_length=240)]
OptDraftId = Annotated[str | None, Query(pattern=DRAFT_ID, max_length=200)]
SearchQ = Annotated[str, Query(max_length=200)]
