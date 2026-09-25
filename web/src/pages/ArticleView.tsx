import { Link, useSearchParams } from "react-router-dom";
import { GroupedRefs, FlatRefs } from "../components/RefList";
import { IntlList } from "../components/IntlList";
import { RelationPanel } from "../components/RelationPanel";
import { CsvLink, ErrorBox, Loading, Section, SourceLink } from "../components/ui";
import { useArticle, useInternational, useLaw } from "../hooks/queries";
import { provisionLabel, splitArticleId } from "../lib/format";
import type { RefItem } from "../types/api";

export function ArticleView({ articleId }: { articleId: string }) {
  const q = useArticle(articleId);
  const intl = useInternational(articleId);
  const { lawId, number } = splitArticleId(articleId);
  const law = useLaw(lawId);
  const [params, setParams] = useSearchParams();
  const compare = params.get("compare"); // other provision id
  const anchor = params.get("anchor"); // selected-side clause number

  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  const c = q.data!;
  const a = c.article;
  const children = (law.data?.articles ?? []).filter((x) => x.number.startsWith(`${number}.`));
  const csv = (list?: string) => ({ kind: "connections", article_id: articleId, list });
  const intlCount = (intl.data?.treaties.length ?? 0) + (intl.data?.foreign_laws.length ?? 0);

  const setCompare = (it: RefItem | null) => {
    const next = new URLSearchParams(params);
    if (it?.article_id) {
      next.set("compare", it.article_id);
      next.set("anchor", it.anchor_number ?? a.number);
    } else {
      next.delete("compare");
      next.delete("anchor");
    }
    setParams(next, { replace: true });
  };
  const isOpen = (it: RefItem) =>
    !!it.article_id && compare === it.article_id && (anchor ?? a.number) === (it.anchor_number ?? a.number);
  const compareAction = (it: RefItem) =>
    it.article_id && (
      <button type="button" className="btn-plain" onClick={() => setCompare(isOpen(it) ? null : it)}>
        {isOpen(it) ? "Харьцуулалтыг хаах" : "Харьцуулах"}
      </button>
    );
  const compareDetail = (it: RefItem) =>
    isOpen(it) && (
      <RelationPanel current={`${lawId}:${it.anchor_number ?? a.number}`} other={it.article_id!} onClose={() => setCompare(null)} />
    );

  return (
    <article data-testid="article-view">
      <div className="text-sm text-muted">{a.law_name}</div>
      <h2 className="mt-0 mb-1 text-2xl font-semibold">
        {provisionLabel(a.number)}
        {a.title && <span className="font-normal">. {a.title}</span>}
      </h2>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <SourceLink href={a.source_url} />
        <Link className="btn-plain" to={`/impact?article=${encodeURIComponent(a.article_id)}`}>
          Нөлөөллийн шинжилгээ хийх
        </Link>
        <CsvLink params={csv()} label="Бүх жагсаалт CSV татах" />
      </div>
      {a.text && <p className="my-3 max-w-4xl text-[1rem]">{a.text}</p>}
      {children.length > 0 && (
        <details className="my-2 max-w-4xl" open={children.length <= 6}>
          <summary className="cursor-pointer text-[0.9375rem] text-accent">Хэсэг, заалтууд ({children.length})</summary>
          <ol className="m-0 list-none p-0">
            {children.map((ch) => (
              <li key={ch.article_id} className="border-b border-line py-1 text-[0.9375rem]">
                <Link to={`/laws/${lawId}/${ch.number}`} className="font-semibold">
                  {ch.number}.
                </Link>{" "}
                {ch.text}
              </li>
            ))}
          </ol>
        </details>
      )}

      <h3 className="mt-5 mb-1 text-lg font-semibold">Холбогдох заалтууд</h3>
      <p className="mt-0 text-sm text-muted">
        Сонгосон {provisionLabel(a.number)} болон түүний доторх хэсэг, заалтуудтай холбоотой бүх заалт. Баримт нь
        бичвэрт шууд байгаа ишлэл; санал нь загварын тооцоолол бөгөөд шалгах шаардлагатай.
      </p>

      <div className="mt-3 mb-1 text-sm font-semibold tracking-wide text-muted">БАРИМТ</div>
      <Section id="incoming" title="1. Үүнийг иш татсан" count={c.totals.incoming}
        note="Энэ заалтыг иш татсан бусад заалт (хууль тус бүрээр)."
        actions={<CsvLink params={csv("incoming")} />}>
        <GroupedRefs groups={c.incoming} anchorLabel="Иш татсан заалт" />
      </Section>
      <Section id="outgoing" title="2. Үүнээс иш татсан" count={c.totals.outgoing}
        note="Энэ заалтын бичвэрт иш татсан заалт, хууль."
        actions={<CsvLink params={csv("outgoing")} />}>
        <GroupedRefs groups={c.outgoing} anchorLabel="Иш татсан хэсэг" />
      </Section>
      <Section id="old-name" title="3. Хуучин нэр / дугаар ашигласан" count={c.totals.former_name_refs}
        note="Хуулийн хуучин нэрээр хийсэн ишлэл. Бичвэрийг систем өөрчлөхгүй."
        actions={<CsvLink params={csv("former_name_refs")} />}>
        <GroupedRefs groups={c.former_name_refs} anchorLabel="Холбогдох заалт" />
      </Section>
      <Section id="missing" title="4. Заалт олдсонгүй" count={c.totals.missing_target_refs}
        note="Иш татсан дугаар одоогийн бичвэрт байхгүй (хүчингүй болсон эсвэл дугаар өөрчлөгдсөн байж болзошгүй)."
        actions={<CsvLink params={csv("missing_target_refs")} />}>
        <GroupedRefs groups={c.missing_target_refs} anchorLabel="Холбогдох заалт" />
      </Section>

      <div className="mt-5 mb-1 text-sm font-semibold tracking-wide text-muted">САНАЛ — ШАЛГАХ ШААРДЛАГАТАЙ</div>
      <Section id="similar" title="5. Ижил асуудлыг зохицуулсан" count={c.totals.similar}
        note="Шууд иш татаагүй боловч агуулгаараа төстэй заалт (embedding-ийн оноо)."
        actions={<CsvLink params={csv("similar")} />}>
        <FlatRefs items={c.similar} anchorLabel="Сонгосон заалт" />
      </Section>
      <Section id="overlaps" title="6. Болзошгүй давхардал" count={c.totals.overlaps}
        actions={<CsvLink params={csv("overlaps")} />}>
        <FlatRefs items={c.overlaps} anchorLabel="Сонгосон заалт" action={compareAction} detail={compareDetail} />
      </Section>
      <Section id="conflicts" title="7. Болзошгүй зөрчил" count={c.totals.conflicts}
        actions={<CsvLink params={csv("conflicts")} />}>
        <FlatRefs items={c.conflicts} anchorLabel="Сонгосон заалт" action={compareAction} detail={compareDetail} />
      </Section>
      <Section id="international" title="8. Олон улсын эх сурвалж" count={intlCount}
        note="ОУХБ-ын конвенц, гадаад улсын хууль тогтоомжийн жишээ (гараар сонгосон эх сурвалж)."
        actions={<CsvLink params={{ kind: "international", article_id: articleId }} />}>
        {intl.isLoading ? <Loading /> : intl.error ? <ErrorBox error={intl.error} /> : (
          <IntlList items={[...(intl.data?.treaties ?? []), ...(intl.data?.foreign_laws ?? [])]} />
        )}
      </Section>
    </article>
  );
}
