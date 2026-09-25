// ===== LawGraph: жишээ асуулгууд (Neo4j Browser: http://localhost:7474) =====

// 1. Хуулийн бүтэц: бүлэг → зүйлийн тоо
MATCH (:Law {id:'labor-2021'})-[:HAS_CHAPTER]->(c)-[:HAS_SECTION|HAS_ARTICLE*1..2]->(a:Article)
RETURN c.number AS бүлэг, c.title AS нэр, count(a) AS зүйл ORDER BY бүлэг;

// 2. Нэг зүйлийг бүх хэсэг, заалттай нь харах (граф хэлбэрээр)
MATCH path = (:Article {number:80})-[:HAS_PROVISION*]->(:Provision) RETURN path;

// 3. Ажил олгогчид юу хориглосон бэ?
MATCH (p:Provision)-[:MENTIONS]->(:Term {name:'ажил олгогч'})
WHERE 'хориглол' IN p.modality
RETURN p.number, p.text ORDER BY p.number;

// 4. Ажилтны эрх (эрх + ажилтан дурдсан хэсэг)
MATCH (p:Provision)-[:MENTIONS]->(:Term {name:'ажилтан'})
WHERE 'эрх' IN p.modality
RETURN p.number, p.text LIMIT 25;

// 5. Нэр томьёоны тодорхойлолт, хаана хамгийн их хэрэглэгдсэн
MATCH (t:Term)-[:DEFINED_IN]->(d)
OPTIONAL MATCH (p:Provision)-[:MENTIONS]->(t)
RETURN t.name, d.number, count(p) AS дурдсан, t.definition ORDER BY дурдсан DESC;

// 6. Хамгийн олон ишлэгдсэн хэсэг/зүйл (хуулийн "төв" заалтууд)
MATCH (p:Provision)-[:REFERS_TO]->(t)
RETURN coalesce(t.number, t.title) AS заалт,
       [l IN labels(t) WHERE l <> 'LawNode'][0] AS төрөл, count(p) AS ишлэл
ORDER BY ишлэл DESC LIMIT 10;

// 7. Ишлэлийн гинжин хэлхээ (multi-hop): 65.5 → ... 3 шат хүртэл
MATCH path = (:Provision {number:'65.5'})-[:REFERS_TO*1..3]->() RETURN path;

// 8. Нэмэлт, өөрчлөлтийн түүх
MATCH (n)-[r:AMENDED_BY]->(a:AmendingLaw)
RETURN a.date AS огноо, r.type AS төрөл, collect(n.number) AS заалтууд ORDER BY огноо;

// 9. Хүчингүй болсон заалтууд
MATCH (p:Provision {status:'хүчингүй'}) RETURN p.number, p.text;

// 10. Бусад хуультай холбоо
MATCH (p:Provision)-[:CITES]->(e:ExternalLaw)
RETURN e.name, count(p) AS ишлэл, collect(p.number) AS хаанаас ORDER BY ишлэл DESC;

// 11. Маргаан шийдвэрлэх байгууллагуудын үүрэг хаана заагдсан бэ?
MATCH (a:Actor {category:'маргаан шийдвэрлэх'})<-[:MENTIONS]-(p)
RETURN a.name, count(p) AS тоо, collect(p.number)[..10] AS жишээ;

// 12. Хоёр оролцогчийг хоёуланг нь дурдсан заалт (жирэмсэн эмэгтэй + ажил олгогч)
MATCH (:Actor {name:'Жирэмсэн эмэгтэй'})<-[:MENTIONS]-(p)-[:MENTIONS]->(:Term {name:'ажил олгогч'})
RETURN p.number, p.text;

// 13. Бүрэн текст хайлт
CALL db.index.fulltext.queryNodes('provision_text', 'илүү цаг~') YIELD node, score
RETURN node.number, node.text, score LIMIT 10;

// 14. GraphRAG context: хайлтаар олдсон заалт + түүний зүйл, эцэг хэсэг, ишлэсэн заалтууд
CALL db.index.fulltext.queryNodes('provision_text', 'ажлаас халах') YIELD node, score
WITH node LIMIT 5
MATCH (a:Article)-[:HAS_PROVISION*]->(node)
OPTIONAL MATCH (node)-[:REFERS_TO]->(ref)
OPTIONAL MATCH (parent)-[:HAS_PROVISION]->(node) WHERE parent:Provision
RETURN a.number AS зүйл, a.title, parent.text AS эцэг, node.number, node.text,
       collect(DISTINCT coalesce(ref.number, ref.title)) AS ишлэл;

// ===== Утгын холбоос (semantic_links.py, extract_norms.py) =====

// 15. Сэдвүүд, тус бүрт хамаарах зүйлс
MATCH (t:Topic)<-[x:ABOUT]-(a:Article)
RETURN t.name AS сэдэв, t.size AS заалт, collect(a.number + ' ' + a.title)[..6] AS зүйлс ORDER BY заалт DESC;

// 16. Нэг заалттай утгаараа ойр, өөр зүйлд байгаа заалтууд
MATCH (p:Provision {number:'127.1'})-[r:SIMILAR_TO]-(q)
RETURN q.number, r.score, q.text ORDER BY r.score DESC;

// 17. Агуулгаар холбоотой зүйлсийн сүлжээ (граф хэлбэрээр)
MATCH path = (:Article)-[:RELATED_TO]->(:Article) RETURN path;

// 18. Вектор хайлт: асуултад утгаараа хамгийн ойр заалт (асуултыг "query: ..." хэлбэрээр embedding болгож $v-д өгнө)
// CALL db.index.vector.queryNodes('provision_embedding', 10, $v) YIELD node, score RETURN node.number, node.text, score;

// 19. Ажил олгогчийн ажилтны өмнө хүлээх үүргүүд (extract_norms.py-ийн дараа)
MATCH (:Actor {name:'ажил олгогч'})-[:HAS_DUTY]->(n:Norm)-[:TOWARDS]->(:Actor {name:'ажилтан'})
MATCH (n)-[:STATED_IN]->(p)
RETURN p.number, n.action, n.condition ORDER BY p.number;

// 20. Хэн хэний өмнө ямар эрх, үүрэгтэй — оролцогчдын нэгтгэсэн граф
MATCH (a:Actor)-[r:HAS_RIGHT|HAS_DUTY|IS_PROHIBITED|HAS_POWER|IS_LIABLE]->(:Norm)-[:TOWARDS]->(b:Actor)
RETURN a.name, type(r), b.name, count(*) AS тоо ORDER BY тоо DESC;

// 21. Үл хамаарах тохиолдлыг заасан ишлэлүүд
MATCH (p:Provision)-[r:REFERS_TO {role:'үл хамаарах'}]->(t) RETURN p.number, p.text, t.number;
