import { useMutation } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { FlatRefs, GroupedRefs } from "../components/RefList";
import { CsvLink, Empty, ErrorBox, Loading, Section } from "../components/ui";
import { useLaw, useLaws } from "../hooks/queries";
import { api } from "../lib/api";
import { articleIdOf, provisionLabel, splitArticleId } from "../lib/format";
import type { ImpactResponse } from "../types/api";

type Kind = "text" | "renumber" | "rename";
const NOTE = "Энэ нь түр тооцоолол бөгөөд хуульд өөрчлөлт оруулахгүй.";
const DEPTH_TITLE: Record<number, string> = {
  1: "Шууд нөлөөлөл — Depth 1",
  2: "Дам нөлөөлөл — Depth 2",
  3: "Дам нөлөөлөл — Depth 3",
};

function Result({ r, csv }: { r: ImpactResponse; csv: Record<string, string | number | null | undefined> }) {
  return (
    <div data-testid="impact-result">
      <h2 className="mt-0 mb-1 text-xl font-semibold">Хэрэв энэ өөрчлөлт хийгдвэл...</h2>
      {r.change && <p className="mt-0 text-[0.9375rem]">{r.change.summary}</p>}
      <p className="border border-line bg-soft px-3 py-2 text-[0.9375rem]">{r.note}</p>
      <table className="my-3 w-full max-w-2xl border-collapse text-[0.9375rem]" data-testid="impact-totals">
        <tbody>
          <tr className="border-b border-line">
            <td className="py-1.5">Шууд нөлөөлөл (Depth 1)</td>
            <td className="py-1.5 text-right font-semibold">{r.totals.direct} заалт</td>
          </tr>
          <tr className="border-b border-line">
            <td className="py-1.5">Дам нөлөөлөл (Depth 2{r.depths.length > 2 ? "–3" : ""})</td>
            <td className="py-1.5 text-right font-semibold">{r.totals.indirect} заалт</td>
          </tr>
          <tr className="border-b border-line">
            <td className="py-1.5 font-semibold">Нийт нөлөөлөл</td>
            <td className="py-1.5 text-right font-semibold">
              {r.totals.articles} заалт, {r.totals.laws} хууль
            </td>
          </tr>
          <tr className="border-b border-line">
            <td className="py-1.5">Шинэ бичвэртэй төстэй заалт (санал)</td>
            <td className="py-1.5 text-right">{r.totals.new_similar}</td>
          </tr>
        </tbody>
      </table>
      <div className="mb-2">
        <CsvLink params={csv} label="Бүх үр дүн CSV татах" />
      </div>
      {r.depths.map((d) => (
        <Section key={d.depth} title={DEPTH_TITLE[d.depth]} count={d.count}
          note={d.depth === 1 ? "Өөрчлөгдөж буй заалтыг (эсвэл түүнийг агуулсан зүйлийг) шууд иш татсан заалт."
            : "Шууд нөлөөлөлд өртсөн заалтыг иш татсан заалт."}
          actions={<CsvLink params={{ ...csv, list: `depth${d.depth}` }} />}>
          <GroupedRefs groups={d.groups} anchorLabel="Иш татсан заалт" />
        </Section>
      ))}
      <Section title="Шинэ бичвэртэй төстэй бусад хуулийн заалт" count={r.new_similar.length}
        note="Санал: түр бичвэртэй агуулгаараа төстэй заалт. Шалгах шаардлагатай."
        actions={<CsvLink params={{ ...csv, list: "new_similar" }} />}>
        <FlatRefs items={r.new_similar} anchorLabel="Өөрчлөгдөж буй заалт" />
      </Section>
    </div>
  );
}

export function ImpactPage() {
  const [params, setParams] = useSearchParams();
  const initial = params.get("article");
  const laws = useLaws();
  const [lawId, setLawId] = useState<string>(initial ? splitArticleId(initial).lawId : "");
  const [number, setNumber] = useState<string>(initial ? splitArticleId(initial).number : "");
  const [kind, setKind] = useState<Kind>("text");
  const [text, setText] = useState("");
  const [newNumber, setNewNumber] = useState("");
  const [newName, setNewName] = useState("");
  const [depth, setDepth] = useState<1 | 2 | 3>(2);
  const law = useLaw(lawId || undefined);
  const textLaws = useMemo(() => (laws.data ?? []).filter((l) => l.text_available), [laws.data]);

  useEffect(() => {
    if (!lawId && textLaws.length) setLawId(textLaws[0].law_id);
  }, [lawId, textLaws]);

  const article = law.data?.articles.find((a) => a.number === number);
  useEffect(() => {
    setText(article?.text || "");
    setNewNumber("");
  }, [article?.article_id]); // reset the form only when another provision is chosen

  const articleId = lawId && number ? articleIdOf(lawId, number) : "";
  const run = useMutation({
    mutationFn: () =>
      kind === "rename"
        ? api.impact({ law_id: lawId, new_name: newName, depth })
        : api.articleImpact(articleId, {
            new_text: kind === "text" ? text : null,
            new_number: kind === "renumber" ? newNumber : null,
            depth,
          }),
  });
  const canRun =
    kind === "rename" ? !!lawId && newName.trim().length > 0 : !!articleId && (kind !== "renumber" || /^\d+(\.\d+)*$/.test(newNumber));
  const csv = {
    kind: "impact",
    article_id: kind === "rename" ? null : articleId,
    law_id: kind === "rename" ? lawId : null,
    new_text: kind === "text" ? text.slice(0, 3900) : null,
    new_number: kind === "renumber" ? newNumber : null,
    new_name: kind === "rename" ? newName : null,
    depth,
  };

  const selectArticle = (n: string) => {
    setNumber(n);
    run.reset();
    const next = new URLSearchParams(params);
    if (n) next.set("article", articleIdOf(lawId, n));
    else next.delete("article");
    setParams(next, { replace: true });
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(20rem,28rem)_minmax(0,1fr)]">
      <aside className="panel self-start" aria-label="Нөлөөллийн шинжилгээ">
        <h2 className="mt-0 mb-2 text-lg font-semibold">Нөлөөллийн шинжилгээ</h2>
        <form
          className="grid gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (canRun) run.mutate();
          }}
        >
          <label className="grid gap-1 text-[0.9375rem]">
            Хууль
            <select className="field" value={lawId} aria-label="Хууль"
              onChange={(e) => { setLawId(e.target.value); setNumber(""); run.reset(); }}>
              {textLaws.map((l) => (
                <option key={l.law_id} value={l.law_id}>
                  {l.name}
                </option>
              ))}
            </select>
          </label>
          <fieldset className="m-0 grid gap-1 border border-line p-2 text-[0.9375rem]">
            <legend className="px-1">Өөрчлөлтийн төрөл</legend>
            {([["text", "Заалтын бичвэр өөрчлөх"], ["renumber", "Заалтын дугаар өөрчлөх"], ["rename", "Хуулийн нэр өөрчлөх"]] as const).map(
              ([k, label]) => (
                <label key={k} className="flex items-center gap-2">
                  <input type="radio" name="kind" checked={kind === k} onChange={() => { setKind(k); run.reset(); }} />
                  {label}
                </label>
              ),
            )}
          </fieldset>
          {kind !== "rename" && (
            <label className="grid gap-1 text-[0.9375rem]">
              Зүйл, заалт
              <select className="field" value={number} aria-label="Зүйл, заалт" onChange={(e) => selectArticle(e.target.value)}>
                <option value="">— Сонгоно уу —</option>
                {(law.data?.articles ?? []).map((a) => (
                  <option key={a.article_id} value={a.number}>
                    {provisionLabel(a.number)} {a.title ? `. ${a.title}` : `— ${a.text.slice(0, 60)}`}
                  </option>
                ))}
              </select>
            </label>
          )}
          {kind === "text" && (
            <label className="grid gap-1 text-[0.9375rem]">
              Түр өөрчлөлтийн текст
              <textarea className="field min-h-36" value={text} onChange={(e) => setText(e.target.value)}
                aria-label="Түр өөрчлөлтийн текст" />
            </label>
          )}
          {kind === "renumber" && (
            <label className="grid gap-1 text-[0.9375rem]">
              Шинэ дугаар
              <input className="field" value={newNumber} placeholder="жишээ нь 81.1" onChange={(e) => setNewNumber(e.target.value)} />
            </label>
          )}
          {kind === "rename" && (
            <label className="grid gap-1 text-[0.9375rem]">
              Хуулийн шинэ нэр
              <input className="field" value={newName} onChange={(e) => setNewName(e.target.value)} />
            </label>
          )}
          <label className="flex items-center gap-2 text-[0.9375rem]">
            Гүн
            <select className="field w-auto" value={depth} onChange={(e) => setDepth(Number(e.target.value) as 1 | 2 | 3)}>
              <option value={1}>1 — шууд</option>
              <option value={2}>2 — дам</option>
              <option value={3}>3</option>
            </select>
          </label>
          <div>
            <button type="submit" className="btn" disabled={!canRun || run.isPending}>
              Нөлөөллийг тооцоолох
            </button>
          </div>
          <p className="m-0 text-sm text-muted">{NOTE}</p>
        </form>
      </aside>
      <section aria-label="Үр дүн" className="panel min-w-0 self-start">
        {run.isPending ? <Loading /> : run.error ? <ErrorBox error={run.error} /> : run.data ? (
          <Result r={run.data} csv={csv} />
        ) : (
          <div className="max-w-3xl">
            <h2 className="mt-0 text-xl font-semibold">Хэрэв энэ өөрчлөлт хийгдвэл...</h2>
            <p>
              Заалт сонгож түр өөрчлөлтийн текст (эсвэл шинэ дугаар, хуулийн шинэ нэр) оруулаад
              «Нөлөөллийг тооцоолох» товчийг дарна уу. Шууд болон дам нөлөөлөлд өртөх бүх заалтыг
              эх сурвалжтай нь харуулна.
            </p>
            <p className="text-sm text-muted">{NOTE}</p>
            {article && (
              <p className="border-l-2 border-accent pl-3 text-[0.9375rem]">
                Сонгосон: {law.data?.law.name}, {provisionLabel(article.number)}
              </p>
            )}
            {!textLaws.length && !laws.isLoading && <Empty />}
          </div>
        )}
      </section>
    </div>
  );
}
