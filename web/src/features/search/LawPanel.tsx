import { Icon } from "../../components/Icon";
import { Panel } from "../../components/Layout";
import { ErrorState, Loading } from "../../components/States";
import { provisionLabel } from "../../lib/format";
import { useLaw } from "../../queries";

export function SourceLink({ href }: { href: string }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-accent underline">
      Эх сурвалж
      <Icon name="external" className="h-4 w-4" />
      <span className="sr-only">(шинэ цонхонд нээгдэнэ)</span>
    </a>
  );
}

/** Right column header: the selected law and, if chosen, the selected provision. */
export function LawPanel({ lawId, articleId }: { lawId: string; articleId: string | null }) {
  const law = useLaw(lawId);
  if (law.isPending) return <Panel><Loading /></Panel>;
  if (law.isError) return <Panel><ErrorState onRetry={() => law.refetch()} /></Panel>;

  const { law: l, articles } = law.data;
  const article = articles.find((a) => a.article_id === articleId);

  return (
    <div className="flex flex-col gap-5">
      <Panel>
        <h1 className="text-xl font-semibold">{l.name}</h1>
        <dl className="mt-2 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-ink-2">
          {l.former_names.length > 0 && (
            <>
              <dt>Хуучин нэр</dt>
              <dd className="text-ink">{l.former_names.join("; ")}</dd>
            </>
          )}
          {l.adopted_date && (
            <>
              <dt>Баталсан огноо</dt>
              <dd className="text-ink tabular-nums">{l.adopted_date}</dd>
            </>
          )}
          <dt>Заалтын тоо</dt>
          <dd className="text-ink">{articles.length}</dd>
        </dl>
        <div className="mt-3">
          <SourceLink href={l.source_url} />
        </div>
      </Panel>

      {article && (
        <Panel title={`${l.name}, ${provisionLabel(article.number)}`}>
          {article.title && <p className="mb-2 font-medium">{article.title}</p>}
          <p className="whitespace-pre-line">{article.text}</p>
        </Panel>
      )}
    </div>
  );
}
