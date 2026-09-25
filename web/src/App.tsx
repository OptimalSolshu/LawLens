import { useVirtualizer } from "@tanstack/react-virtual";
import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { LawSummary } from "./types";

// Placeholder page: law list from GET /api/laws. Member 2 replaces this.
export default function App() {
  const [q, setQ] = useState("");
  const [laws, setLaws] = useState<LawSummary[]>([]);
  const [mock, setMock] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.health().then((h) => setMock(h.mock)).catch(() => {});
  }, []);

  useEffect(() => {
    api
      .listLaws(q)
      .then((l) => {
        setLaws(l);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [q]);

  const scrollRef = useRef<HTMLDivElement>(null);
  const rows = useVirtualizer({
    count: laws.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 64,
  });

  return (
    <div className="mx-auto max-w-3xl p-6 font-sans text-slate-900">
      {mock && (
        <div className="mb-4 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          ЖИШЭЭ ӨГӨГДӨЛ: mock API. Бодит хууль тогтоомж биш. (Sample data, not real legal content.)
        </div>
      )}
      <h1 className="mb-4 text-2xl font-semibold">LawLens</h1>
      <input
        className="mb-4 w-full rounded border border-slate-300 px-3 py-2"
        placeholder="Хуулийн одоогийн эсвэл хуучин нэрээр хайх…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {error && <p className="text-red-700">{error}</p>}
      <div ref={scrollRef} className="h-[70vh] overflow-auto rounded border border-slate-200">
        <div className="relative w-full" style={{ height: rows.getTotalSize() }}>
          {rows.getVirtualItems().map((row) => {
            const law = laws[row.index];
            return (
              <div
                key={law.law_id}
                className="absolute left-0 w-full border-b border-slate-100 px-4 py-2"
                style={{ height: row.size, transform: `translateY(${row.start}px)` }}
              >
                <div className="font-medium">{law.name}</div>
                <div className="text-sm text-slate-500">
                  {law.article_count} заалт
                  {law.former_names.length > 0 && <> · хуучин нэр: {law.former_names.join(", ")}</>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
