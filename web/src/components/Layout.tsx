import { NavLink, Outlet } from "react-router-dom";
import { useHealth } from "../hooks/queries";

const MENU = [
  { to: "/laws", label: "Хууль хайх" },
  { to: "/impact", label: "Нөлөөллийн шинжилгээ" },
  { to: "/drafts", label: "Хуулийн төслүүд" },
];

export function Layout() {
  const health = useHealth();
  const sample = health.data?.dataset === "sample";
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3 px-5 py-3">
          <NavLink to="/laws" className="text-ink no-underline">
            <div className="text-xl font-semibold text-ink">Хуулийн уялдааны шинжилгээ</div>
            <div className="text-xs tracking-wide text-muted">LawLens</div>
          </NavLink>
          <nav aria-label="Үндсэн цэс" className="flex flex-wrap gap-1">
            {MENU.map((m) => (
              <NavLink
                key={m.to}
                to={m.to}
                className={({ isActive }) =>
                  `px-3 py-1.5 text-[0.9375rem] no-underline ${
                    isActive ? "border-b-2 border-accent font-semibold text-accent" : "border-b-2 border-transparent text-ink hover:text-accent"
                  }`
                }
              >
                {m.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      {sample && (
        <div className="border-b border-line bg-white" role="note" data-testid="sample-banner">
          <p className="mx-auto my-0 max-w-[1400px] px-5 py-1.5 text-sm text-warn">
            ЖИШЭЭ ӨГӨГДӨЛ: зохиомол жишээ бичвэр ([ЖИШЭЭ]). Бодит хуулийн заалт, бодит дүгнэлт биш.
          </p>
        </div>
      )}
      <main className="mx-auto w-full max-w-[1400px] flex-1 px-5 py-5">
        <Outlet />
      </main>
      <footer className="border-t border-line bg-white">
        <div className="mx-auto flex max-w-[1400px] flex-wrap justify-between gap-2 px-5 py-3 text-sm text-muted">
          <span>Монгол Улсын Их Хурал</span>
          <span>Систем санал гаргана; шийдвэрийг хууль зүйн ажилтан гаргана.</span>
        </div>
      </footer>
    </div>
  );
}
