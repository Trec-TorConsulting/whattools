import { test, expect } from "./fixtures";

test.describe("Analytics", () => {
  test("analytics page requires admin role", async ({ memberPage: page }) => {
    await page.goto("/analytics");
    await expect(page).not.toHaveURL(/analytics/);
  });

  test("owner can access analytics dashboard", async ({ ownerPage: page }) => {
    await page.getByRole("link", { name: "Analytics", exact: true }).click();
    await expect(page).toHaveURL(/analytics/);
    await expect(page.getByText("Business performance insights")).toBeVisible();
  });

  test("shows KPI summary cards", async ({ ownerPage: page }) => {
    await page.goto("/analytics");
    await expect(page.getByText("Revenue")).toBeVisible();
    await expect(page.getByText("Profit")).toBeVisible();
    await expect(page.getByText("Orders")).toBeVisible();
    await expect(page.getByText("Shows")).toBeVisible();
  });

  test("has period selector", async ({ ownerPage: page }) => {
    await page.goto("/analytics");
    // Period select with options
    await page.getByText("Last 30 days").first().click();
    await expect(page.getByText("Last 7 days", { exact: true })).toBeVisible();
    await expect(page.getByText("Last 90 days", { exact: true })).toBeVisible();
    await expect(page.getByText("Last year", { exact: true })).toBeVisible();
  });

  test("has chart tabs", async ({ ownerPage: page }) => {
    await page.goto("/analytics");
    await expect(page.getByText("Revenue & Profit")).toBeVisible();
    await expect(page.getByText("Categories")).toBeVisible();
    await expect(page.getByText("Top Items")).toBeVisible();
  });

  test("can switch between chart tabs", async ({ ownerPage: page }) => {
    await page.goto("/analytics");

    // Click Categories tab
    await page.getByText("Categories").click();
    // Should show category-related chart or empty state
    const hasCategoryData = await page.getByText("Revenue by Category").isVisible().catch(() => false);
    if (!hasCategoryData) {
      await expect(page.getByText("No category data")).toBeVisible();
    }

    // Click Top Items tab
    await page.getByText("Top Items").click();
    const hasItemData = await page.getByText("Top Selling Items").isVisible().catch(() => false);
    if (!hasItemData) {
      await expect(page.getByText("No sales data yet")).toBeVisible();
    }
  });

  test("can change analytics period", async ({ ownerPage: page }) => {
    await page.goto("/analytics");
    await page.getByText("Last 30 days").first().click();
    await page.getByText("Last 7 days", { exact: true }).click();
    // Should refetch data (no error)
    await expect(page.getByText("Business performance insights")).toBeVisible();
  });
});

test.describe("Exports", () => {
  test("exports page requires admin role", async ({ memberPage: page }) => {
    await page.goto("/analytics/exports");
    await expect(page).not.toHaveURL(/exports/);
  });

  test("owner can access exports page", async ({ ownerPage: page }) => {
    await page.goto("/analytics/exports");
    await expect(page.getByText("Generate and download reports")).toBeVisible();
    await expect(page.getByRole("button", { name: "New Export" })).toBeVisible();
  });

  test("can open create export dialog", async ({ ownerPage: page }) => {
    await page.goto("/analytics/exports");
    await page.getByRole("button", { name: "New Export" }).click();

    await expect(page.getByRole("heading", { name: "Create Export" })).toBeVisible();
    await expect(page.getByText("Generate a report to download")).toBeVisible();
    await expect(page.getByText("Report Type")).toBeVisible();
    await expect(page.getByText("Format")).toBeVisible();
    await expect(page.getByText("Period")).toBeVisible();
  });

  test("can create an export", async ({ ownerPage: page }) => {
    await page.goto("/analytics/exports");
    await page.getByRole("button", { name: "New Export" }).click();

    // Select report type — click to open, then choose
    await page.getByRole("button", { name: "Create Export" }).click();

    // Dialog should close after submission
    await expect(page.getByRole("heading", { name: "Create Export" })).not.toBeVisible({ timeout: 15_000 });
  });
});
