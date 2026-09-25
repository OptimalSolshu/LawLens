import type { IntlItem } from "../types/api";
import { Empty, SourceLink, TypeLabel, WarnLabel } from "./ui";

export function IntlList({ items }: { items: IntlItem[] }) {
  if (!items.length) return <Empty />;
  return (
    <ul className="m-0 list-none p-0">
      {items.map((it) => (
        <li key={it.source_id} className="border-b border-line py-2" data-testid="intl-row">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div className="font-semibold">
              {it.title}
              {it.provision && <span className="font-normal">, {it.provision}</span>}
            </div>
            <div className="flex gap-1">
              <TypeLabel type="suggestion" confidence={it.relevance} />
              <WarnLabel>Шалгах шаардлагатай</WarnLabel>
            </div>
          </div>
          <div className="text-sm text-muted">
            {it.country_or_org} · {it.kind === "treaty" ? "Олон улсын гэрээ, конвенц" : "Гадаад улсын хууль тогтоомж"}
            {it.anchor_number && <> · Холбогдох заалт: {it.anchor_number}</>}
          </div>
          <p className="my-1 text-[0.9375rem]">{it.summary}</p>
          <p className="my-1 text-sm">
            <span className="text-muted">Холбоосын тайлбар: </span>
            {it.explanation}
            {it.model && <span className="text-muted"> (Загвар: {it.model})</span>}
          </p>
          <span className="break-all">
            <SourceLink href={it.url}>{it.url}</SourceLink>
          </span>
        </li>
      ))}
    </ul>
  );
}
