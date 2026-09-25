import type { ReactNode } from "react";
import type { View } from "../lib/url";
import { useHealth } from "../queries";

const MENU: { view: View; label: string }[] = [
  { view: "search", label: "Хууль хайх" },
  { view: "impact", label: "Нөлөөллийн шинжилгээ" },
  { view: "drafts", label: "Хуулийн төслүүд" },
];

function Header({ view, onNavigate }: { view: View; onNavigate: (v: View) => void }) {
  return (
    <header className="border-b border-line bg-white">
      <div className="mx-auto flex h-[60px] max-w-[1440px] items-center justify-between px-6">
        <div className="flex items-center gap-10">
          <div className="leading-tight">
            <div className="text-[17px] font-semibold text-ink">Хуулийн уялдааны шинжилгээ</div>
            <div className="text-xs text-ink-2">LawLens</div>
          </div>
          <nav aria-label="Үндсэн цэс">
            <ul className="flex">
              {MENU.map((m) => {
                const current = m.view === view;
                return (
                  <li key={m.view}>
                    <a
                      href={m.view === "search" ? "?" : `?view=${m.view}`}
                      aria-current={current ? "page" : undefined}
                      onClick={(e) => {
                        e.preventDefault();
                        onNavigate(m.view);
                      }}
                      className={`block border-b-2 px-2.5 py-2 text-[15px] ${
                        current ? "border-accent text-accent" : "border-transparent text-ink hover:text-accent"
                      }`}
                    >
                      {m.label}
                    </a>
                  </li>
                );
              })}
            </ul>
          </nav>
        </div>
        <span className="text-[15px] text-ink-2" aria-disabled="true" title="Англи хэлний хувилбар бэлтгэгдээгүй байна">
          English
        </span>
      </div>
    </header>
  );
}

function MockNotice() {
  const health = useHealth();
  if (!health.data?.mock) return null;
  return (
    <div className="border-b border-line bg-white">
      <p className="mx-auto max-w-[1440px] px-6 py-1.5 text-sm text-ink-2">
        Туршилтын горим: жишээ өгөгдөл харуулж байна. Эдгээр заалт бодит хууль тогтоомж биш.
      </p>
    </div>
  );
}

function Footer() {
  return (
    <footer className="border-t border-line bg-white">
      <div className="mx-auto flex max-w-[1440px] items-center justify-between px-6 py-4 text-sm text-ink-2">
        <span>Монгол Улсын Их Хурал</span>
        <a href="https://www.parliament.mn" target="_blank" rel="noreferrer" className="text-accent underline">
          parliament.mn
        </a>
      </div>
    </footer>
  );
}

export function Layout(props: { view: View; onNavigate: (v: View) => void; children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-page text-ink">
      <Header view={props.view} onNavigate={props.onNavigate} />
      <MockNotice />
      <main className="mx-auto w-full max-w-[1440px] flex-1 px-6 py-5">{props.children}</main>
      <Footer />
    </div>
  );
}

/** Left ~30% selection, right ~70% results. */
export function TwoColumns({ left, right }: { left: ReactNode; right: ReactNode }) {
  return (
    <div className="grid grid-cols-[minmax(320px,3fr)_7fr] items-start gap-5">
      <section aria-label="Хайлт ба сонголт" className="flex flex-col gap-5">
        {left}
      </section>
      <section aria-label="Үр дүн" className="min-w-0">
        {right}
      </section>
    </div>
  );
}

export function Panel({ title, children }: { title?: ReactNode; children: ReactNode }) {
  return (
    <div className="border border-line bg-white p-4">
      {title && <h2 className="mb-3 text-base font-semibold text-ink">{title}</h2>}
      {children}
    </div>
  );
}
