import type { ItemType } from "../types/api";

/** "Баримт" for facts, "Санал, 82%" for suggestions (CLAUDE.md §11). */
export function typeLabel(type: ItemType, confidence: number): string {
  return type === "fact" ? "Баримт" : `Санал, ${Math.round(confidence * 100)}%`;
}

/**
 * Ordinal suffix for an article number: "80 дугаар зүйл", "104 дүгээр зүйл".
 * Vowel harmony follows the last non-zero part of the spoken number:
 * нэг (1), дөрөв (4), ес (9), дөч (40), ер (90) take "дүгээр"; the rest "дугаар".
 */
export function ordinalSuffix(n: number): "дугаар" | "дүгээр" {
  const units = n % 10;
  const tens = Math.floor(n / 10) % 10;
  if (units) return [1, 4, 9].includes(units) ? "дүгээр" : "дугаар";
  if (tens) return [4, 9].includes(tens) ? "дүгээр" : "дугаар";
  return "дугаар";
}

/** "80" -> "80 дугаар зүйл"; "80.1" -> "80.1"; null -> "Хууль бүхэлдээ". */
export function provisionLabel(number: string | null | undefined): string {
  if (!number) return "Хууль бүхэлдээ";
  if (/^\d+$/.test(number)) return `${number} ${ordinalSuffix(Number(number))} зүйл`;
  return number;
}

export function isArticleLevel(number: string): boolean {
  return /^\d+$/.test(number);
}

export function articleIdOf(lawId: string, number: string): string {
  return `${lawId}:${number}`;
}

export function splitArticleId(articleId: string): { lawId: string; number: string } {
  const i = articleId.indexOf(":");
  return { lawId: articleId.slice(0, i), number: articleId.slice(i + 1) };
}

/** Route of a provision in the "Хууль хайх" page. */
export function articleRoute(articleId: string): string {
  const { lawId, number } = splitArticleId(articleId);
  return `/laws/${lawId}/${number}`;
}

export const OP_LABEL: Record<string, string> = {
  replace: "Өөрчлөх",
  insert: "Нэмэх",
  delete: "Хасах",
  repeal: "Хүчингүй болгох",
  add: "Шинэ заалт нэмэх",
  rename: "Хуулийн нэр өөрчлөх",
};
