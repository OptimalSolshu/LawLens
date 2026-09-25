import { describe, expect, it } from "vitest";
import { exportUrl } from "../src/lib/api";
import { articleRoute, ordinalSuffix, provisionLabel, typeLabel } from "../src/lib/format";

describe("labels", () => {
  it("formats facts and suggestions", () => {
    expect(typeLabel("fact", 1)).toBe("Баримт");
    expect(typeLabel("suggestion", 0.82)).toBe("Санал, 82%");
  });

  it("uses the right ordinal suffix", () => {
    expect(provisionLabel("80")).toBe("80 дугаар зүйл");
    expect(provisionLabel("104")).toBe("104 дүгээр зүйл");
    expect(provisionLabel("91")).toBe("91 дүгээр зүйл");
    expect(provisionLabel("40")).toBe("40 дүгээр зүйл");
    expect(provisionLabel("120")).toBe("120 дугаар зүйл");
    expect(ordinalSuffix(6)).toBe("дугаар");
    expect(provisionLabel("80.1")).toBe("80.1");
    expect(provisionLabel(null)).toBe("Хууль бүхэлдээ");
  });

  it("builds routes and export urls", () => {
    expect(articleRoute("khodolmoriin-tukhai-khuuli:80.1")).toBe("/laws/khodolmoriin-tukhai-khuuli/80.1");
    expect(exportUrl({ kind: "connections", article_id: "a:1", list: undefined, q: "" })).toBe(
      "/api/export?kind=connections&article_id=a%3A1",
    );
  });
});
