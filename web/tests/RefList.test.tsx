import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { FlatRefs, GroupedRefs } from "../src/components/RefList";
import type { RefItem } from "../src/types/api";

const fact: RefItem = {
  law_id: "zorchliin-tukhai-khuuli",
  law_name: "Зөрчлийн тухай хууль",
  article_id: "zorchliin-tukhai-khuuli:6.4",
  number: "6.4",
  snippet: "[ЖИШЭЭ] бичвэр",
  source_url: "https://example.org/x#6.4",
  type: "fact",
  confidence: 1,
  flags: { uses_old_name: false, target_missing: true },
  anchor_number: "80.5",
  cited_number: "80.5",
  current_number: null,
  raw_text: "Хөдөлмөрийн тухай хуулийн 80.5-д",
  explanation: "80.5 дугаартай заалт олдсонгүй.",
};

const suggestion: RefItem = {
  ...fact,
  article_id: "osh:12.1",
  number: "12.1",
  type: "suggestion",
  confidence: 0.82,
  flags: { uses_old_name: false, target_missing: false },
  model: "demo-llm",
};

describe("RefList", () => {
  it("shows a fact with its warnings, old number and source", () => {
    render(
      <MemoryRouter>
        <GroupedRefs groups={[{ law_id: fact.law_id, law_name: fact.law_name, count: 1, items: [fact] }]} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Баримт")).toBeInTheDocument();
    expect(screen.getByText("Заалт олдсонгүй")).toBeInTheDocument();
    expect(screen.getByText("Шалгах шаардлагатай")).toBeInTheDocument();
    expect(screen.getByText("Хуучин дугаар").nextSibling).toHaveTextContent("80.5");
    expect(screen.getByText("Одоогийн дугаар").nextSibling).toHaveTextContent("Тодорхойгүй");
    expect(screen.getByRole("link", { name: "Эх сурвалж" })).toHaveAttribute("href", fact.source_url);
  });

  it("labels a suggestion with its confidence and model, never as a fact", () => {
    render(
      <MemoryRouter>
        <FlatRefs items={[suggestion]} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Санал, 82%")).toBeInTheDocument();
    expect(screen.queryByText("Баримт")).not.toBeInTheDocument();
    expect(screen.getByText("Загвар: demo-llm")).toBeInTheDocument();
    expect(screen.getByText("Шалгах шаардлагатай")).toBeInTheDocument();
  });

  it("shows the empty state", () => {
    render(
      <MemoryRouter>
        <FlatRefs items={[]} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Мэдээлэл олдсонгүй.")).toBeInTheDocument();
  });
});
