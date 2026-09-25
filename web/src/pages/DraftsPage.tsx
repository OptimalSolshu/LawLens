import { Link, useParams } from "react-router-dom";
import { GroupedRefs } from "../components/RefList";
import { CsvLink, Empty, ErrorBox, Loading, Section, SourceLink, TypeLabel, WarnLabel } from "../components/ui";
import { useDraft, useDrafts, useLaws } from "../hooks/queries";
import { articleRoute, OP_LABEL, provisionLabel } from "../lib/format";
import type { LawGroup } from "../types/api";

function GapStatus({ status }: { status: "covered" | "missing" | "review" }) {
  if (status === "covered") return <span className="label label-fact">Тусгагдсан</span>;
  if (status === "missing") return <WarnLabel>Орхигдсон</WarnLabel>;
  return <WarnLabel>Шалгах шаардлагатай</WarnLabel>;
}

function GapTable({ rows }: { rows: { g: LawGroup; status: "covered" | "missing" | "review" }[] }) {
  if (!rows.length) return <Empty />;
  return (
    <table className="w-full border-collapse text-[0.9375rem]" data-testid="gap-table">
      <thead>
        <tr className="border-b border-line text-left text-sm text-muted">
          <th className="py-1 font-normal">Нөлөөлөлд өртөх хууль</th>
          <th className="py-1 font-normal">Төслийн багцад</th>
          <th className="py-1 font-normal">Төлөв</th>
          <th className="py-1 font-normal">Шалтгаан</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ g, status }) => (
          <tr key={g.law_id} className="border-b border-line align-top" data-testid={`gap-${status}`}>
            <td className="py-1.5 pr-3 font-semibold">{g.law_name}</td>
            <td className="py-1.5 pr-3">{status === "covered" ? "Тийм" : "Үгүй"}</td>
            <td className="py-1.5 pr-3">
              <GapStatus status={status} />
            </td>
            <td className="py-1.5 text-sm">
              {g.items.map((it) => (
                <div key={it.article_id ?? it.number}>
                  {it.article_id ? <Link to={articleRoute(it.article_id)}>{provisionLabel(it.number)}</Link> : provisionLabel(it.number)}
                  {" — "}
                  {it.explanation}
                </div>
              ))}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DraftView({ draftId }: { draftId: string }) {
  const q = useDraft(draftId);
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  const { draft, target_law, amended, cosubmitted, gap } = q.data!;
  const rows = [
    ...gap.missing.map((g) => ({ g, status: "missing" as const })),
    ...gap.covered.map((g) => ({ g, status: "covered" as const })),
    ...gap.review.map((g) => ({ g, status: "review" as const })),
  ];
  const csv = (list?: string) => ({ kind: "draft_gap", draft_id: draftId, list });
  return (
    <article data-testid="draft-view">
      <h2 className="mt-0 mb-1 text-xl font-semibold">{draft.title}</h2>
      <div className="flex flex-wrap gap-3 text-sm">
        <span>
          Үндсэн хууль: <Link to={`/laws/${target_law.law_id}`}>{target_law.name}</Link>
        </span>
        <SourceLink href={draft.source_url} />
      </div>
      {draft.new_name && (
        <p className="text-[0.9375rem]">
          Хуулийн шинэ нэр (төсөлд): <strong>{draft.new_name}</strong>
        </p>
      )}

      <Section title="Нэмэлт, өөрчлөлт оруулж буй заалтууд" count={amended.length}>
        {amended.length ? (
          <ul className="m-0 list-none p-0">
            {amended.map(({ op, article }, i) => (
              <li key={i} className="border-b border-line py-2 text-[0.9375rem]">
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="font-semibold">
                    {op.article_id ? <Link to={articleRoute(op.article_id)}>{provisionLabel(op.number)}</Link> : provisionLabel(op.number)}
                  </span>
                  <span className="label">{OP_LABEL[op.op]}</span>
                  <TypeLabel type="fact" confidence={1} />
                </div>
                {op.old_text && <div>Одоогийн: «{op.old_text}»</div>}
                {op.new_text && <div>Төсөлд: «{op.new_text}»</div>}
                {article && <p className="my-1 text-sm text-muted">Одоогийн бичвэр: {article.text}</p>}
                <p className="my-1 text-sm text-muted">Төслийн бичвэр: {op.raw_text}</p>
              </li>
            ))}
          </ul>
        ) : (
          <Empty />
        )}
      </Section>

      <Section title="Хамт өргөн мэдүүлсэн төслүүд" count={draft.cosubmitted_titles.length}>
        {draft.cosubmitted_titles.length ? (
          <ul className="m-0 list-none p-0">
            {draft.cosubmitted_titles.map((t, i) => (
              <li key={t} className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line py-1.5 text-[0.9375rem]">
                <span>{t}</span>
                <span className="text-sm text-muted">{cosubmitted[i]?.name}</span>
              </li>
            ))}
          </ul>
        ) : (
          <Empty text="Хамт өргөн мэдүүлсэн төсөл байхгүй." />
        )}
      </Section>

      <Section title="Нэмэлт, өөрчлөлт оруулах шаардлагатай байж болзошгүй хуулиуд" count={rows.length}
        note="Төслөөр өөрчлөгдөж буй заалтыг иш татсан хуулиуд. Багцад багтсан бол «Тусгагдсан», багтаагүй бол «Орхигдсон». Энэ нь ишлэлд үндэслэсэн шалгалтын санал; нэмэлт, өөрчлөлт заавал шаардлагатай гэсэн дүгнэлт биш."
        actions={<CsvLink params={csv()} />}>
        <p className="mt-0 text-[0.9375rem]" data-testid="gap-summary">
          Тусгагдсан: {gap.covered.length} · Орхигдсон: {gap.missing.length} · Шалгах шаардлагатай: {gap.review.length}
        </p>
        <GapTable rows={rows} />
      </Section>

      <Section title="Орхигдсон байж болзошгүй — дэлгэрэнгүй" count={gap.missing.reduce((n, g) => n + g.count, 0)}
        actions={<CsvLink params={csv("missing")} />}>
        <GroupedRefs groups={gap.missing} anchorLabel="Иш татсан заалт" />
      </Section>
      <Section title="Дам нөлөөлөл — шалгах шаардлагатай" count={gap.review.reduce((n, g) => n + g.count, 0)}
        actions={<CsvLink params={csv("review")} />}>
        <GroupedRefs groups={gap.review} anchorLabel="Иш татсан заалт" />
      </Section>
    </article>
  );
}

export function DraftsPage() {
  const { draftId } = useParams();
  const drafts = useDrafts();
  const laws = useLaws();
  const lawName = (id: string) => laws.data?.find((l) => l.law_id === id)?.name ?? id;
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(20rem,26rem)_minmax(0,1fr)]">
      <aside aria-label="Хуулийн төслүүд">
        <h2 className="mt-0 mb-2 text-lg font-semibold">Хуулийн төслүүд</h2>
        {drafts.isLoading ? <Loading /> : drafts.error ? <ErrorBox error={drafts.error} /> : drafts.data!.length ? (
          <ul className="m-0 list-none border-t border-line p-0">
            {drafts.data!.map((d) => (
              <li key={d.draft_id} className="border-b border-line">
                <Link to={`/drafts/${d.draft_id}`} data-testid="draft-row"
                  className={`block px-2 py-2 no-underline hover:bg-soft ${d.draft_id === draftId ? "bg-soft text-accent" : "text-ink"}`}>
                  <div className="text-[0.9375rem] font-semibold">{d.title}</div>
                  <div className="text-sm text-muted">
                    {lawName(d.target_law_id)} · Хамт өргөн мэдүүлсэн: {d.cosubmitted_law_ids.length}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <Empty text="Хуулийн төсөл бүртгэгдээгүй байна." />
        )}
      </aside>
      <section aria-label="Үр дүн" className="min-w-0">
        {draftId ? <DraftView draftId={draftId} /> : (
          <div className="max-w-3xl">
            <h2 className="mt-0 text-xl font-semibold">Хамт өргөн мэдүүлсэн төслийн шалгалт</h2>
            <p>
              Төсөл сонгоход тухайн төслөөр өөрчлөгдөж буй заалтыг иш татсан бусад хуулийг олж, хамт өргөн
              мэдүүлсэн нэмэлт, өөрчлөлтийн төслүүдэд тусгагдсан эсэхийг харуулна.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
