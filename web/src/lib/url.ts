import { useCallback, useEffect, useState } from "react";

export type View = "search" | "impact" | "drafts";

/** Current selection, mirrored in the URL (?view=&law=&article=) for deep links. */
export interface Selection {
  view: View;
  law: string | null;
  article: string | null;
}

const VIEWS: View[] = ["search", "impact", "drafts"];

function read(): Selection {
  const p = new URLSearchParams(window.location.search);
  const view = p.get("view") as View;
  return {
    view: VIEWS.includes(view) ? view : "search",
    law: p.get("law"),
    article: p.get("article"),
  };
}

function write(s: Selection) {
  const p = new URLSearchParams();
  if (s.view !== "search") p.set("view", s.view);
  if (s.law) p.set("law", s.law);
  if (s.article) p.set("article", s.article);
  const qs = p.toString();
  window.history.pushState(null, "", `${window.location.pathname}${qs ? `?${qs}` : ""}`);
}

export function useSelection(): [Selection, (patch: Partial<Selection>) => void] {
  const [selection, setSelection] = useState(read);

  useEffect(() => {
    const onPop = () => setSelection(read());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const update = useCallback((patch: Partial<Selection>) => {
    const next = { ...read(), ...patch };
    write(next);
    setSelection(next);
  }, []);

  return [selection, update];
}
