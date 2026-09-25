import { useState } from "react";
import { Icon } from "../../components/Icon";
import { Empty, ErrorState, Loading } from "../../components/States";
import { rowClass, VirtualList } from "../../components/VirtualList";
import { useDebounced } from "../../lib/useDebounced";
import { useLaws } from "../../queries";
import type { LawSummary } from "../../types";

/** Former name that matched the query, when the current name did not. */
function matchedFormerName(law: LawSummary, q: string): string | null {
  const needle = q.toLocaleLowerCase("mn");
  if (!needle || law.name.toLocaleLowerCase("mn").includes(needle)) return null;
  return law.former_names.find((n) => n.toLocaleLowerCase("mn").includes(needle)) ?? null;
}

export function LawSearch({ selectedLaw, onSelect }: { selectedLaw: string | null; onSelect: (lawId: string) => void }) {
  const [q, setQ] = useState("");
  const query = useDebounced(q.trim(), 250);
  const laws = useLaws(query);

  return (
    <div>
      <label htmlFor="law-q" className="mb-1 block font-medium">
        Хуулийн нэрээр хайх
      </label>
      <div className="relative">
        <Icon name="search" className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-2" />
        <input
          id="law-q"
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          autoComplete="off"
          aria-describedby="law-q-help"
          className="w-full rounded-sm border border-line-strong bg-white py-2 pl-9 pr-3"
        />
      </div>
      <p id="law-q-help" className="mt-1 text-sm text-ink-2">
        Одоогийн болон хуучин нэрээр хайж болно.
      </p>

      <div className="mt-3">
        {laws.isPending ? (
          <Loading />
        ) : laws.isError ? (
          <ErrorState onRetry={() => laws.refetch()} />
        ) : laws.data.length === 0 ? (
          <Empty>Хайлтад тохирох хууль олдсонгүй.</Empty>
        ) : (
          <>
            <p className="mb-1 text-sm text-ink-2" aria-live="polite">
              Илэрц: {laws.data.length} хууль
            </p>
            <VirtualList
              items={laws.data}
              getKey={(l) => l.law_id}
              selectedKey={selectedLaw}
              onSelect={(l) => onSelect(l.law_id)}
              label="Хайлтын илэрц"
              estimateSize={56}
              className="h-64"
              renderItem={(law, state) => {
                const former = matchedFormerName(law, query);
                return (
                  <div className={rowClass(state)}>
                    <div className={state.selected ? "font-semibold" : ""}>{law.name}</div>
                    {former && <div className="text-sm text-ink-2">Хуучин нэр: {former}</div>}
                    <div className="text-sm text-ink-2">{law.article_count} заалт</div>
                  </div>
                );
              }}
            />
          </>
        )}
      </div>
    </div>
  );
}
