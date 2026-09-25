import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { articleRoute, provisionLabel } from "../lib/format";
import type { LawGroup, RefItem } from "../types/api";
import { Empty, FlagLabels, SourceLink, TypeLabel } from "./ui";

const GRID_LAW = "grid grid-cols-1 gap-x-4 gap-y-1 md:grid-cols-[minmax(10rem,14rem)_6.5rem_minmax(0,1fr)_11rem_6rem]";
const GRID = "grid grid-cols-1 gap-x-4 gap-y-1 md:grid-cols-[6.5rem_minmax(0,1fr)_11rem_6rem]";

function Header({ lawColumn }: { lawColumn: boolean }) {
  return (
    <div className={`${lawColumn ? GRID_LAW : GRID} hidden border-b border-line pb-1 text-sm text-muted md:grid`}>
      {lawColumn && <div>Хууль</div>}
      <div>Заалт</div>
      <div>Шалтгаан, агуулга</div>
      <div>Төлөв</div>
      <div>Эх сурвалж</div>
    </div>
  );
}

/** Evidence for outdated references: original text, matched name, current name, old / current number. */
function Evidence({ item }: { item: RefItem }) {
  if (!item.flags.uses_old_name && !item.flags.target_missing) return null;
  return (
    <dl className="mt-1 mb-0 grid grid-cols-[9rem_1fr] gap-x-2 border-l-2 border-warn pl-2 text-sm">
      {item.raw_text && (
        <>
          <dt className="text-muted">Эх ишлэл</dt>
          <dd className="m-0">«{item.raw_text}»</dd>
        </>
      )}
      {item.flags.uses_old_name && (
        <>
          <dt className="text-muted">Таарсан нэр</dt>
          <dd className="m-0">{item.matched_name} (хуучин нэр)</dd>
          <dt className="text-muted">Одоогийн нэр</dt>
          <dd className="m-0">{item.law_name}</dd>
        </>
      )}
      {item.flags.target_missing && (
        <>
          <dt className="text-muted">Хуучин дугаар</dt>
          <dd className="m-0">{item.cited_number}</dd>
          <dt className="text-muted">Одоогийн дугаар</dt>
          <dd className="m-0">{item.current_number ?? "Тодорхойгүй"}</dd>
        </>
      )}
    </dl>
  );
}

function Row({
  item,
  lawColumn,
  anchorLabel,
  action,
  detail,
}: {
  item: RefItem;
  lawColumn: boolean;
  anchorLabel?: string;
  action?: (item: RefItem) => ReactNode;
  detail?: (item: RefItem) => ReactNode;
}) {
  const provision = provisionLabel(item.number);
  const extra = detail?.(item);
  return (
    <div className="border-b border-line" data-testid="ref-row">
    <div className={`${lawColumn ? GRID_LAW : GRID} py-2`}>
      {lawColumn && <div className="text-[0.9375rem]">{item.law_name}</div>}
      <div className="text-[0.9375rem] font-semibold">
        {item.article_id ? <Link to={articleRoute(item.article_id)}>{provision}</Link> : provision}
      </div>
      <div className="min-w-0 text-[0.9375rem]">
        {item.explanation && <p className="m-0">{item.explanation}</p>}
        <p className={`m-0 line-clamp-3 ${item.explanation ? "text-sm text-muted" : ""}`}>{item.snippet}</p>
        {item.anchor_number && anchorLabel && (
          <p className="m-0 text-sm text-muted">
            {anchorLabel}: {item.anchor_number}
          </p>
        )}
        {item.model && item.type === "suggestion" && <p className="m-0 text-sm text-muted">Загвар: {item.model}</p>}
        <Evidence item={item} />
        {action && <div className="mt-1">{action(item)}</div>}
      </div>
      <div className="flex flex-wrap content-start gap-1">
        <TypeLabel type={item.type} confidence={item.confidence} />
        <FlagLabels flags={item.flags} review={item.type === "suggestion"} />
      </div>
      <div>
        <SourceLink href={item.source_url} />
      </div>
    </div>
    {extra}
    </div>
  );
}

export function GroupedRefs({
  groups,
  anchorLabel,
  action,
}: {
  groups: LawGroup[];
  anchorLabel?: string;
  action?: (item: RefItem) => ReactNode;
}) {
  if (!groups.length) return <Empty />;
  return (
    <div>
      <Header lawColumn={false} />
      {groups.map((g) => (
        <div key={g.law_id} className="mt-2">
          <div className="bg-soft px-2 py-1 text-[0.9375rem] font-semibold">
            {g.law_name} <span className="font-normal text-muted">({g.count})</span>
          </div>
          {g.items.map((it, i) => (
            <Row key={`${it.article_id ?? it.number}-${i}`} item={it} lawColumn={false} anchorLabel={anchorLabel} action={action} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function FlatRefs({
  items,
  anchorLabel,
  action,
  detail,
}: {
  items: RefItem[];
  anchorLabel?: string;
  action?: (item: RefItem) => ReactNode;
  /** full-width block under a row (e.g. the side-by-side comparison) */
  detail?: (item: RefItem) => ReactNode;
}) {
  if (!items.length) return <Empty />;
  return (
    <div>
      <Header lawColumn />
      {items.map((it, i) => (
        <Row key={`${it.article_id}-${i}`} item={it} lawColumn anchorLabel={anchorLabel} action={action} detail={detail} />
      ))}
    </div>
  );
}
