import { expect, test } from "@playwright/test";

// The 3-minute demo flow on the [ЖИШЭЭ] sample dataset.
test("search → provision → connections → impact → draft gap → CSV", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Хуулийн уялдааны шинжилгээ").first()).toBeVisible();
  await expect(page.getByTestId("sample-banner")).toContainText("ЖИШЭЭ");

  // 1. search the Labor Law and open it
  await page.getByPlaceholder("Хууль, заалт хайх").fill("Хөдөлмөрийн тухай");
  await page.getByTestId("law-row").filter({ hasText: /^Хөдөлмөрийн тухай хууль\d/ }).click();
  await expect(page.getByTestId("law-overview")).toBeVisible();

  // 2. select article 80 and see the grouped connections
  await page.getByPlaceholder("Хууль, заалт хайх").fill("");
  await page.getByTestId("article-list").getByText("80 дугаар зүйл. Ажлын цаг").click();
  const view = page.getByTestId("article-view");
  await expect(view.getByRole("heading", { name: /80 дугаар зүйл/ })).toBeVisible();
  for (const title of ["1. Үүнийг иш татсан", "2. Үүнээс иш татсан", "3. Хуучин нэр / дугаар ашигласан",
    "4. Заалт олдсонгүй", "5. Ижил асуудлыг зохицуулсан", "7. Болзошгүй зөрчил", "8. Олон улсын эх сурвалж"]) {
    await expect(view.getByRole("heading", { name: title })).toBeVisible();
  }
  await expect(page.locator("#incoming").getByText("Зөрчлийн тухай хууль")).toBeVisible();
  await expect(page.locator("#old-name").getByText("Хуучин нэр", { exact: true }).first()).toBeVisible();
  await expect(page.locator("#missing").getByText("Заалт олдсонгүй", { exact: true }).first()).toBeVisible();
  await expect(page.locator("#conflicts").getByText("Санал, 82%")).toBeVisible();

  // side-by-side comparison with international sources and a resolution suggestion
  await page.locator("#conflicts").getByRole("button", { name: "Харьцуулах" }).first().click();
  const panel = page.getByTestId("relation-panel");
  await expect(panel.getByTestId("relation-side")).toHaveCount(2);
  await expect(panel.getByTestId("intl-row").first()).toContainText("Hours of Work (Industry) Convention, 1919 (No. 1)");
  await expect(panel.getByTestId("resolution")).toContainText("Шалгах шаардлагатай");

  // 3. impact analysis of a temporary change
  await page.getByRole("link", { name: "Нөлөөллийн шинжилгээ", exact: true }).click();
  await page.getByLabel("Зүйл, заалт").selectOption("80.1");
  await page.getByLabel("Түр өөрчлөлтийн текст").fill("[ЖИШЭЭ] Ажилтны долоо хоногийн ажлын хэвийн цаг 38 цагаас хэтрэхгүй байна.");
  await page.getByRole("button", { name: "Нөлөөллийг тооцоолох" }).click();
  const result = page.getByTestId("impact-result");
  await expect(result.getByText("Энэ нь түр тооцоолол бөгөөд хуульд өөрчлөлт оруулахгүй.")).toBeVisible();
  await expect(result.getByRole("heading", { name: /Шууд нөлөөлөл — Depth 1/ })).toBeVisible();
  await expect(result.getByRole("heading", { name: /Дам нөлөөлөл — Depth 2/ })).toBeVisible();
  await expect(page.getByTestId("impact-totals")).toContainText("6 заалт, 4 хууль");

  // 4. co-submitted bill gap
  await page.getByRole("link", { name: "Хуулийн төслүүд" }).click();
  await page.getByTestId("draft-row").first().click();
  await expect(page.getByTestId("gap-summary")).toContainText("Тусгагдсан: 1 · Орхигдсон: 2");
  await expect(page.getByTestId("gap-missing")).toHaveCount(2);
  await expect(page.getByTestId("gap-table").getByText("Орхигдсон").first()).toBeVisible();

  // 5. CSV export
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "CSV татах" }).first().click(),
  ]);
  const path = await download.path();
  const fs = await import("node:fs");
  const csv = fs.readFileSync(path!, "utf-8");
  expect(csv).toContain("law_name,provision_number,relationship,type");
  expect(csv).toContain("Орхигдсон");
});
