// LawLens graph schema (Neo4j 5). Applied by loader.py before loading.
//
// (:Law {law_id, name, former_names[], short_names[], adopted_date, source_url})
// (:Article {article_id, law_id, number, parent_number, title, text, embedding[1024]})
// (:Draft {draft_id, lawforum_id, title, new_name, source_url})
// (:IntlSource {source_id, kind, country_or_org, title, url, summary})
//
// (:Law)-[:HAS_ARTICLE]->(:Article)
// (:Article)-[:CHILD_OF]->(:Article)
// (:Article)-[:REFERS_TO {raw_text, matched_name, uses_old_name, method, confidence}]->(:Article)
// (:Article)-[:REFERS_TO_MISSING {to_number, raw_text, matched_name, uses_old_name, method, confidence}]->(:Law)
// (:Article)-[:SIMILAR {score, model}]->(:Article)                 stored once, query undirected
// (:Article)-[:RELATION {kind, confidence, explanation, model}]->(:Article)
// (:Draft)-[:TARGETS]->(:Law), (:Draft)-[:AMENDS]->(:Article), (:Draft)-[:COSUBMITS]->(:Law)
// (:Article)-[:INTL_LINK {relevance, explanation}]->(:IntlSource)
// (:Article)-[:AMENDMENT_SUGGESTION]->(:Suggestion {reason, suggested_text, based_on_source_ids[], model})

CREATE CONSTRAINT law_id IF NOT EXISTS FOR (l:Law) REQUIRE l.law_id IS UNIQUE;
CREATE CONSTRAINT article_id IF NOT EXISTS FOR (a:Article) REQUIRE a.article_id IS UNIQUE;
CREATE CONSTRAINT draft_id IF NOT EXISTS FOR (d:Draft) REQUIRE d.draft_id IS UNIQUE;
CREATE CONSTRAINT intl_source_id IF NOT EXISTS FOR (s:IntlSource) REQUIRE s.source_id IS UNIQUE;

CREATE INDEX article_law IF NOT EXISTS FOR (a:Article) ON (a.law_id);

// current + former names searchable together
CREATE FULLTEXT INDEX law_names IF NOT EXISTS FOR (l:Law) ON EACH [l.name, l.former_names_text];

// BAAI/bge-m3 dense vectors
CREATE VECTOR INDEX article_embedding IF NOT EXISTS
FOR (a:Article) ON (a.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}};
