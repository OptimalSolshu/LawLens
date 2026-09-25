import { useVirtualizer } from "@tanstack/react-virtual";
import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { isArticleLevel, provisionLabel } from "../lib/format";
import type { Article } from "../types/api";

/** Virtualised list of a law's articles and clauses (the real Labor Law has 1,000+ rows). */
export function ArticleList({ lawId, articles, selected }: { lawId: string; articles: Article[]; selected?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const rows = useVirtualizer({
    count: articles.length,
    getScrollElement: () => ref.current,
    estimateSize: (i) => (isArticleLevel(articles[i].number) ? 44 : 58),
    overscan: 12,
  });
  useEffect(() => {
    const i = articles.findIndex((a) => a.number === selected);
    if (i >= 0) rows.scrollToIndex(i, { align: "center" });
    // scroll only when the selection or the list changes, not on every virtualizer render
  }, [selected, articles]);

  return (
    <div ref={ref} className="h-[62vh] overflow-auto border border-line" data-testid="article-list">
      <div className="relative w-full" style={{ height: rows.getTotalSize() }}>
        {rows.getVirtualItems().map((row) => {
          const a = articles[row.index];
          const top = isArticleLevel(a.number);
          const depth = a.number.split(".").length - 1;
          const active = a.number === selected;
          return (
            <Link
              key={a.article_id}
              ref={rows.measureElement}
              data-index={row.index}
              to={`/laws/${lawId}/${a.number}`}
              className={`absolute left-0 block w-full border-b border-line py-1.5 pr-2 text-[0.9375rem] no-underline ${
                active ? "bg-soft text-accent" : "text-ink hover:bg-soft"
              }`}
              style={{ transform: `translateY(${row.start}px)`, paddingLeft: `${0.6 + depth * 0.9}rem` }}
              aria-current={active ? "true" : undefined}
            >
              {top ? (
                <span className="font-semibold">
                  {provisionLabel(a.number)}. {a.title}
                </span>
              ) : (
                <span className="line-clamp-2">
                  <span className="font-semibold">{a.number}.</span> {a.text}
                </span>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
