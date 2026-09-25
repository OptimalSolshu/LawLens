// LawLens knowledge graph (Neo4j 5 Community + APOC). Applied by loader.py before loading.
// Source of truth for the graph model (CLAUDE.md §10 defers to this file).
//
// Nodes
// (:Law {law_id, name, former_names[], short_names[], adopted_date, source_url, text_available, sample})
// (:LawName {name})                                   every current / former / short name / alias
// (:Article {article_id, law_id, number, parent_number, title, text, embedding[1024], embedding_model})
// (:Draft {draft_id, lawforum_id, title, new_name, source_url, amended_article_ids[], cosubmitted_law_ids[],
//          cosubmitted_titles[], operations_json})
// (:Source {source_id, kind, country_or_org, title, provision, url, summary})   curated international source
// (:Suggestion {article_id, reason, suggested_text, based_on_source_ids[], model, confidence})
//
// Relationships (facts)
// (:Law)-[:HAS_ARTICLE]->(:Article)
// (:Article)-[:PART_OF]->(:Article)                    clause -> containing part / article
// (:Law)-[:KNOWN_AS {kind: current|former|short|alias}]->(:LawName)
// (:Article)-[:REFERS_TO {to_law_id, to_number, to_article_id, raw_text, matched_name, uses_old_name,
//                         target_missing, current_number, method, confidence}]->(:Article)
// (:Article)-[:REFERS_TO {...same...}]->(:Law)        target provision missing, or whole-law citation
// (:Draft)-[:TARGETS]->(:Law), (:Draft)-[:AMENDS {op, old_text, new_text}]->(:Article),
// (:Draft)-[:CO_SUBMITTED_FOR]->(:Law)
//
// Relationships (suggestions: always carry model + confidence/score)
// (:Article)-[:SIMILAR_TO {score, model}]->(:Article)                       stored once, query undirected
// (:Article)-[:CONFLICTS_WITH|OVERLAPS_WITH|CONSISTENT_WITH {kind, confidence, explanation, model}]->(:Article)
// (:Article)-[:RELEVANT_SOURCE {relevance, explanation, model}]->(:Source)
// (:Article)-[:AMENDMENT_SUGGESTION]->(:Suggestion)

CREATE CONSTRAINT law_id IF NOT EXISTS FOR (l:Law) REQUIRE l.law_id IS UNIQUE;
CREATE CONSTRAINT law_name IF NOT EXISTS FOR (n:LawName) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT article_id IF NOT EXISTS FOR (a:Article) REQUIRE a.article_id IS UNIQUE;
CREATE CONSTRAINT draft_id IF NOT EXISTS FOR (d:Draft) REQUIRE d.draft_id IS UNIQUE;
CREATE CONSTRAINT source_id IF NOT EXISTS FOR (s:Source) REQUIRE s.source_id IS UNIQUE;

CREATE INDEX article_law IF NOT EXISTS FOR (a:Article) ON (a.law_id);
CREATE INDEX article_number IF NOT EXISTS FOR (a:Article) ON (a.number);
CREATE INDEX suggestion_article IF NOT EXISTS FOR (s:Suggestion) ON (s.article_id);

CREATE FULLTEXT INDEX law_name_text IF NOT EXISTS FOR (n:LawName) ON EACH [n.name];
CREATE FULLTEXT INDEX article_text IF NOT EXISTS FOR (a:Article) ON EACH [a.title, a.text];

// 1024-dim: BAAI/bge-m3, intfloat/multilingual-e5-large and the offline demo embedder
CREATE VECTOR INDEX article_embedding IF NOT EXISTS
FOR (a:Article) ON (a.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}};
