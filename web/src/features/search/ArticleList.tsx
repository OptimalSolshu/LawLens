import { useMemo, useState } from "react";
import { Empty, ErrorState, Loading } from "../../components/States";
import { rowClass, VirtualList } from "../../components/VirtualList";
import { useLaw } from "../../queries";

export function ArticleList({
  lawId,
  selectedArticle,
  onSelect,
}: {
  lawId: string;
  selectedArticle: string | null;
  onSelect: (articleId: string) => void;
}) {
  const law = useLaw(lawId);
  const [filter, setFilter] = useState("");

  const articles = useMemo(() => {
    const all = law.data?.articles ?? [];
    const f = filter.trim().toLocaleLowerCase("mn");
    if (!f) return all;
    return all.filter((a) => a.number.startsWith(f) || (a.title ?? "").toLocaleLowerCase("mn").includes(f));
  }, [law.data, filter]);

  if (law.isPending) return <Loading />;
  if (law.isError) return <ErrorState onRetry={() => law.refetch()} />;

  return (
    <div>
      <h2 className="mb-2 font-semibold">
        Заалтууд <span className="font-normal text-ink-2">({law.data.articles.length})</span>
      </h2>
      <label htmlFor="article-filter" className="mb-1 block text-sm">
        Дугаар эсвэл гарчгаар шүүх
      </label>
      <input
        id="article-filter"
        type="search"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        autoComplete="off"
        className="mb-2 w-full rounded-sm border border-line-strong bg-white px-3 py-1.5"
      />
      {articles.length === 0 ? (
        <Empty>Шүүлтүүрт тохирох заалт олдсонгүй.</Empty>
      ) : (
        <VirtualList
          items={articles}
          getKey={(a) => a.article_id}
          selectedKey={selectedArticle}
          onSelect={(a) => onSelect(a.article_id)}
          label="Хуулийн заалтууд"
          estimateSize={42}
          className="h-[45vh]"
          renderItem={(a, state) => (
            <div className={`flex gap-3 ${rowClass(state)}`}>
              <span className="w-16 shrink-0 font-medium tabular-nums">{a.number}</span>
              <span className={a.title ? "" : "text-ink-2"}>{a.title ?? "Гарчиггүй"}</span>
            </div>
          )}
        />
      )}
    </div>
  );
}
