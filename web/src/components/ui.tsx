import type { ReactNode } from "react";
import { exportUrl } from "../lib/api";
import { typeLabel } from "../lib/format";
import type { Flags, ItemType } from "../types/api";

export function Loading() {
  return <p className="py-3 text-muted">Уншиж байна...</p>;
}

export function Empty({ text = "Мэдээлэл олдсонгүй." }: { text?: string }) {
  return <p className="py-2 text-muted">{text}</p>;
}

export function ErrorBox({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <p className="border border-warn px-3 py-2 text-warn" role="alert">
      Мэдээлэл авахад алдаа гарлаа. ({msg})
    </p>
  );
}

/** "Баримт" or "Санал, 82%". */
export function TypeLabel({ type, confidence }: { type: ItemType; confidence: number }) {
  return (
    <span className={`label ${type === "fact" ? "label-fact" : "label-suggestion"}`}>
      {typeLabel(type, confidence)}
    </span>
  );
}

export function WarnLabel({ children }: { children: ReactNode }) {
  return <span className="label label-warn">{children}</span>;
}

export function FlagLabels({ flags, review = false }: { flags: Flags; review?: boolean }) {
  const warn = flags.uses_old_name || flags.target_missing || review;
  return (
    <>
      {flags.uses_old_name && <WarnLabel>Хуучин нэр</WarnLabel>}
      {flags.target_missing && <WarnLabel>Заалт олдсонгүй</WarnLabel>}
      {warn && <WarnLabel>Шалгах шаардлагатай</WarnLabel>}
    </>
  );
}

export function SourceLink({ href, children = "Эх сурвалж" }: { href: string; children?: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer noopener" className="text-sm">
      {children}
    </a>
  );
}

export function CsvLink({ params, label = "CSV татах" }: { params: Record<string, string | number | null | undefined>; label?: string }) {
  return (
    <a className="btn-plain" href={exportUrl(params)} download>
      {label}
    </a>
  );
}

export function Section({
  id,
  title,
  count,
  note,
  actions,
  children,
}: {
  id?: string;
  title: string;
  count?: number;
  note?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section id={id} className="border-t border-line pt-3 pb-4" aria-label={title}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="m-0 text-[1.0625rem] font-semibold">
          {title}
          {count !== undefined && <span className="ml-2 font-normal text-muted">({count})</span>}
        </h3>
        {actions}
      </div>
      {note && <p className="mt-1 mb-2 text-sm text-muted">{note}</p>}
      <div className="mt-2">{children}</div>
    </section>
  );
}
