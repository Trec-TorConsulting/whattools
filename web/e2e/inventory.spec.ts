import { test, expect } from "./fixtures";

test.describe("Inventory Management", () => {
  test.describe("Items List", () => {
    test("shows inventory page with correct header", async ({ ownerPage: page }) => {
      await page.getByRole("link", { name: "Inventory", exact: true }).click();
      await expect(page).toHaveURL(/inventory/);
      await expect(page.getByText("Manage your items and stock levels")).toBeVisible();
      await expect(page.getByRole("button", { name: "Add Item" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Import CSV" })).toBeVisible();
    });

    test("shows search and filter controls", async ({ ownerPage: page }) => {
      await page.goto("/inventory");
      await expect(page.getByPlaceholder("Search items…")).toBeVisible();
    });

    test("can open Add Item dialog", async ({ ownerPage: page }) => {
      await page.goto("/inventory");
      await page.getByRole("button", { name: "Add Item" }).click();
      await expect(page.getByRole("heading", { name: "Add Item" })).toBeVisible();
      await expect(page.getByText("Add a new item to your inventory")).toBeVisible();

      // Verify form fields
      await expect(page.getByLabel("Item Name *")).toBeVisible();
      await expect(page.getByLabel("SKU")).toBeVisible();
      await expect(page.getByLabel("Quantity *")).toBeVisible();
      await expect(page.getByLabel("Cost (COGS) *")).toBeVisible();
      await expect(page.getByLabel("Sale Price")).toBeVisible();
    });

    test("can create a new item", async ({ ownerPage: page }) => {
      const itemName = `E2E Item ${Date.now().toString(36)}`;
      await page.goto("/inventory");
      await page.getByRole("button", { name: "Add Item" }).click();

      await page.getByLabel("Item Name *").fill(itemName);
      await page.getByLabel("Quantity *").fill("5");
      await page.getByLabel("Cost (COGS) *").fill("12.50");
      await page.getByLabel("Sale Price").fill("29.99");

      await page.getByRole("button", { name: "Create" }).click();

      // Dialog should close and item should appear in table
      await expect(page.getByRole("heading", { name: "Add Item" })).not.toBeVisible({ timeout: 10_000 });
      await expect(page.getByText(itemName)).toBeVisible({ timeout: 10_000 });
    });

    test("can search for items", async ({ ownerPage: page }) => {
      await page.goto("/inventory");
      const searchInput = page.getByPlaceholder("Search items…");
      await searchInput.fill("nonexistent-item-xyz-999");
      // Allow debounce/refetch
      await page.waitForTimeout(500);
    });

    test("can filter items by status", async ({ ownerPage: page }) => {
      await page.goto("/inventory");
      // Click the status filter select
      await page.getByText("All statuses").first().click();
      await expect(page.getByText("Available", { exact: true })).toBeVisible();
      await expect(page.getByText("Sold", { exact: true })).toBeVisible();
      await expect(page.getByText("Reserved", { exact: true })).toBeVisible();
      await expect(page.getByText("Listed", { exact: true })).toBeVisible();
    });

    test("member can access inventory", async ({ memberPage: page }) => {
      await page.getByRole("link", { name: "Inventory", exact: true }).click();
      await expect(page).toHaveURL(/inventory/);
      await expect(page.getByText("Manage your items and stock levels")).toBeVisible();
    });
  });

  test.describe("Categories", () => {
    test("shows categories page", async ({ ownerPage: page }) => {
      await page.goto("/inventory/categories");
      await expect(page.getByText("Organize your inventory with categories")).toBeVisible();
      await expect(page.getByRole("button", { name: "Add Category" })).toBeVisible();
    });

    test("seed categories are visible", async ({ ownerPage: page }) => {
      await page.goto("/inventory/categories");
      // Seed data includes: Trading Cards, Vintage Toys, Comics, Electronics, Clothing
      await expect(page.getByText("Trading Cards")).toBeVisible({ timeout: 10_000 });
      await expect(page.getByText("Vintage Toys")).toBeVisible();
    });

    test("can create a new category", async ({ ownerPage: page }) => {
      const catName = `E2E Cat ${Date.now().toString(36)}`;
      await page.goto("/inventory/categories");
      await page.getByRole("button", { name: "Add Category" }).click();

      await expect(page.getByRole("heading", { name: "New Category" })).toBeVisible();
      await page.getByLabel("Name").fill(catName);
      await page.getByRole("button", { name: "Create" }).click();

      await expect(page.getByRole("heading", { name: "New Category" })).not.toBeVisible({ timeout: 10_000 });
      await expect(page.getByText(catName)).toBeVisible({ timeout: 10_000 });
    });
  });
});
