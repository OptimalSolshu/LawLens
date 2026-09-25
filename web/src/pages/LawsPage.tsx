import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArticleList } from "../components/ArticleList";
import { GroupedRefs } from "../components/RefList";
import { CsvLink, Empty, ErrorBox, Loading, Section, SourceLink } from "../components/ui";
import { useDebounced, useLaw, useLawConnections, useLaws, useSearch } from "../hooks/queries";
import { articleIdOf, articleRoute, provisionLabel } from "../lib/format";
import type { LawSummary } from "../types/api";
import { ArticleView } from "./ArticleView";

function LawRow({ law }: { law: LawSummary }) {
  return (
    <li className="border-b border-line">
      <Link to={`/laws/${law.law_id}`} className="block px-2 py-2 text-ink no-underline hover:bg-soft" data-testid="law-row">
        <div className="font-semibold">{law.name}</div>
        <div className="text-sm text-muted">
          {law.text_available ? `${law.article_count} зүйл, заалт` : "Бичвэр ачаалагдаагүй (зөвхөн нэрээр иш татагдсан)"}
          {law.former_names.length > 0 && <> · Хуучин нэр: {law.former_names.join(", ")}</>}
        </div>
      </Link>
    </li>
  );
}

function SearchResults({ q }: { q: string }) {
  const s = useSearch(q);
  if (s.isLoading) return <Loading />;
  if (s.error) return <ErrorBox error={s.error} />;
  const d = s.data!;
  if (!d.laws.length && !d.articles.length) return <Empty />;
  return (
    <div data-testid="search-results">
      {d.laws.length > 0 && (
        <>
          <div className="mt-2 text-sm font-semibold text-muted">Хууль ({d.laws.length})</div>
          <ul className="m-0 list-none p-0">
            {d.laws.map((l) => (
              <LawRow key={l.law_id} law={l} />
            ))}
          </ul>
        </>
      )}
      {d.articles.length > 0 && (
        <>
          <div className="mt-3 flex items-center justify-between text-sm font-semibold text-muted">
            <span>Заалт ({d.articles.length})</span>
            <CsvLink params={{ kind: "search", q }} />
          </div>
          <ul className="m-0 list-none p-0">
            {d.articles.map((a) => (
              <li key={a.article_id} className="border-b border-line">
                <Link to={articleRoute(a.article_id)} className="block px-2 py-1.5 text-ink no-underline hover:bg-soft">
                  <div className="text-sm text-muted">{a.law_name}</div>
                  <div className="text-[0.9375rem]">
                    <span className="font-semibold">{provisionLabel(a.number)}</span>
                    {a.title && <>. {a.title}</>}
                  </div>
                  <div className="line-clamp-2 text-sm">{a.snippet}</div>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function LawOverview({ lawId }: { lawId: string }) {
  const law = useLaw(lawId);
  const conn = useLawConnections(lawId);
  if (law.isLoading) return <Loading />;
  if (law.error) return <ErrorBox error={law.error} />;
  const l = law.data!.law;
  const csv = (list?: string) => ({ kind: "law_connections", law_id: lawId, list });
  return (
    <div data-testid="law-overview">
      <h2 className="mt-0 mb-1 text-2xl font-semibold">{l.name}</h2>
      <div className="flex flex-wrap gap-3 text-sm text-muted">
        {l.adopted_date && <span>Баталсан: {l.adopted_date}</span>}
        {l.former_names.length > 0 && <span>Хуучин нэр: {l.former_names.join(", ")}</span>}
        <SourceLink href={l.source_url} />
        <CsvLink params={csv()} />
      </div>
      <p className="max-w-3xl text-[0.9375rem]">
        {l.text_available
          ? "Зүүн талын жагсаалтаас зүйл, заалт сонгоно уу. Доор энэ хуулийг бусад хуультай холбосон бүх ишлэлийг харуулав."
          : "Энэ хуулийн бичвэр системд ачаалагдаагүй; зөвхөн бусад хуулиас иш татсан ишлэлийг харуулна."}
      </p>
      {conn.isLoading ? <Loading /> : conn.error ? <ErrorBox error={conn.error} /> : (
        <>
          <Section title="Энэ хуулийг иш татсан бусад хуулийн заалт" count={conn.data!.totals.incoming}
            actions={<CsvLink params={csv("incoming")} />}>
            <GroupedRefs groups={conn.data!.incoming} anchorLabel="Иш татсан заалт" />
          </Section>
          <Section title="Энэ хуулиас иш татсан бусад хууль" count={conn.data!.totals.outgoing}
            actions={<CsvLink params={csv("outgoing")} />}>
            <GroupedRefs groups={conn.data!.outgoing} anchorLabel="Иш татсан хэсэг" />
          </Section>
          <Section title="Хуучин нэр / дугаар ашигласан" count={conn.data!.totals.former_name_refs}
            actions={<CsvLink params={csv("former_name_refs")} />}>
            <GroupedRefs groups={conn.data!.former_name_refs} anchorLabel="Холбогдох заалт" />
          </Section>
          <Section title="Заалт олдсонгүй" count={conn.data!.totals.missing_target_refs}
            actions={<CsvLink params={csv("missing_target_refs")} />}>
            <GroupedRefs groups={conn.data!.missing_target_refs} anchorLabel="Холбогдох заалт" />
          </Section>
        </>
      )}
    </div>
  );
}

function Intro() {
  return (
    <div className="max-w-3xl" data-testid="intro">
      <h2 className="mt-0 text-2xl font-semibold">Хөдөлмөрийн тухай хууль ба холбогдох хуулиуд</h2>
      <p className="text-[1rem]">
        Хөдөлмөрийн тухай хуультай холбоотой бүх заалтыг нэг дор харуулна: үүнийг иш татсан, үүнээс иш татсан,
        хуучин нэр болон хуучин дугаараар хийсэн ишлэл, олдохгүй заалт, ижил асуудлыг зохицуулсан заалт, болзошгүй
        давхардал, зөрчил, олон улсын эх сурвалж.
      </p>
      <ul className="text-[0.9375rem]">
        <li>Зүүн талаас хууль сонгож, зүйл, заалтаа сонгоно.</li>
        <li>Хайлт: хуулийн нэр, хуучин нэр, заалтын дугаар (жишээ нь 80.1) эсвэл түлхүүр үгээр.</li>
        <li>Жагсаалт бүрийг CSV хэлбэрээр татаж авах боломжтой.</li>
      </ul>
      <p className="text-sm text-muted">
        Систем шийдвэр гаргахгүй: баримт нь бичвэрт шууд байгаа ишлэл, санал нь шалгах шаардлагатай тооцоолол.
      </p>
    </div>
  );
}

export function LawsPage() {
  const { lawId, number } = useParams();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const debounced = useDebounced(q.trim());
  const laws = useLaws();
  const law = useLaw(lawId);

  const setQ = (v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set("q", v);
    else next.delete("q");
    next.delete("compare");
    setParams(next, { replace: true });
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(20rem,26rem)_minmax(0,1fr)]">
      <aside aria-label="Хууль хайх">
        <h2 className="mt-0 mb-2 text-lg font-semibold">Хууль хайх</h2>
        <input
          className="field"
          type="search"
          placeholder="Хууль, заалт хайх"
          aria-label="Хууль, заалт хайх"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <div className="mt-3">
          {debounced ? (
            <SearchResults q={debounced} />
          ) : lawId ? (
            <>
              <Link to="/laws" className="text-sm">
                ← Бүх хууль
              </Link>
              <div className="mt-1 mb-2 font-semibold">{law.data?.law.name}</div>
              {law.isLoading ? <Loading /> : law.error ? <ErrorBox error={law.error} /> : law.data!.articles.length ? (
                <ArticleList lawId={lawId} articles={law.data!.articles} selected={number} />
              ) : (
                <Empty text="Энэ хуулийн бичвэр ачаалагдаагүй." />
              )}
            </>
          ) : laws.isLoading ? (
            <Loading />
          ) : laws.error ? (
            <ErrorBox error={laws.error} />
          ) : (
            <ul className="m-0 list-none border-t border-line p-0">
              {laws.data!.map((l) => (
                <LawRow key={l.law_id} law={l} />
              ))}
            </ul>
          )}
        </div>
      </aside>
      <section aria-label="Үр дүн" className="min-w-0">
        {lawId && number ? (
          <ArticleView key={number} articleId={articleIdOf(lawId, number)} />
        ) : lawId ? (
          <LawOverview lawId={lawId} />
        ) : (
          <Intro />
        )}
      </section>
    </div>
  );
}
