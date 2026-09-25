import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { provisionLabel } from "../lib/format";
import type { ArticleDetail } from "../types/api";
import { IntlList } from "./IntlList";
import { ErrorBox, Loading, SourceLink, TypeLabel, WarnLabel } from "./ui";

const KIND = { conflict: "Болзошгүй зөрчил", overlap: "Болзошгүй давхардал", consistent: "Нийцэж байна" } as const;

function Side({ title, a }: { title: string; a: ArticleDetail }) {
  return (
    <div className="border border-line p-3" data-testid="relation-side">
      <div className="text-sm text-muted">{title}</div>
      <div className="font-semibold">
        {a.law_name}, {provisionLabel(a.number)}
      </div>
      <p className="my-2 text-[0.9375rem]">{a.text || a.title}</p>
      <SourceLink href={a.source_url} />
    </div>
  );
}

/** Side-by-side view of a suggested overlap / conflict, with sources and a resolution suggestion. */
export function RelationPanel({ current, other, onClose }: { current: string; other: string; onClose: () => void }) {
  const q = useQuery({ queryKey: ["relation", current, other], queryFn: () => api.relation(current, other) });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  const r = q.data!;
  const [mine, theirs] = r.a.article_id === current ? [r.a, r.b] : [r.b, r.a];
  return (
    <div className="mt-2 mb-3 border border-accent p-3" data-testid="relation-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="m-0 text-base font-semibold">
          {KIND[r.kind]}: харьцуулалт
        </h4>
        <div className="flex items-center gap-1">
          <TypeLabel type="suggestion" confidence={r.confidence} />
          <WarnLabel>Шалгах шаардлагатай</WarnLabel>
          <button type="button" className="btn-plain ml-2" onClick={onClose}>
            Хаах
          </button>
        </div>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <Side title="Одоогийн заалт" a={mine} />
        <Side title="Холбогдох заалт" a={theirs} />
      </div>
      <h5 className="mt-3 mb-1 text-[0.9375rem] font-semibold">Тайлбар (санал)</h5>
      <p className="m-0 text-[0.9375rem]">{r.explanation}</p>
      <p className="m-0 text-sm text-muted">
        Загвар: {r.model}
        {r.score != null && <> · Төстэй байдлын оноо: {Math.round(r.score * 100)}%</>}
      </p>
      <h5 className="mt-3 mb-1 text-[0.9375rem] font-semibold">Олон улсын эх сурвалж</h5>
      <IntlList items={r.international} />
      <h5 className="mt-3 mb-1 text-[0.9375rem] font-semibold">Шийдлийн санал</h5>
      {r.resolution ? (
        <div className="border border-dashed border-line p-3" data-testid="resolution">
          <div className="mb-1 flex gap-1">
            <TypeLabel type="suggestion" confidence={r.resolution.confidence} />
            <WarnLabel>Шалгах шаардлагатай</WarnLabel>
          </div>
          <p className="m-0 text-sm text-muted">Санал болгож буй найруулга ({r.resolution.article_id.split(":")[1]}):</p>
          <p className="my-1 text-[0.9375rem]">{r.resolution.suggested_text}</p>
          <p className="my-1 text-[0.9375rem]">{r.resolution.reason}</p>
          <p className="m-0 text-sm text-muted">Үндэслэсэн эх сурвалж:</p>
          <ul className="my-1 pl-5 text-sm">
            {r.resolution.sources.map((s) => (
              <li key={s.id}>
                <SourceLink href={s.url}>{s.title}</SourceLink>
              </li>
            ))}
          </ul>
          <p className="m-0 text-sm text-muted">Загвар: {r.resolution.model}. Эцсийн шийдвэрийг хууль зүйн ажилтан гаргана.</p>
        </div>
      ) : (
        <p className="m-0 text-muted">Шийдлийн санал бэлтгэгдээгүй.</p>
      )}
    </div>
  );
}
