import { test, expect } from "./fixtures";

test.describe("Sales & Orders", () => {
  test.describe("Shows", () => {
    test("shows page requires admin role", async ({ memberPage: page }) => {
      await page.goto("/shows");
      // Member should be redirected away or see access denied
      await expect(page).not.toHaveURL(/shows/);
    });

    test("owner can access shows page", async ({ ownerPage: page }) => {
      await page.getByRole("link", { name: "Shows", exact: true }).click();
      await expect(page).toHaveURL(/shows/);
      await expect(page.getByText("Manage your live selling shows")).toBeVisible();
      await expect(page.getByRole("button", { name: "Create Show" })).toBeVisible();
    });

    test("shows table has correct columns", async ({ ownerPage: page }) => {
      await page.goto("/shows");
      await expect(page.getByRole("columnheader", { name: "Title" })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: "Status" })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: "Scheduled" })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: "Created" })).toBeVisible();
    });

    test("can create a new show", async ({ ownerPage: page }) => {
      const showTitle = `E2E Show ${Date.now().toString(36)}`;
      await page.goto("/shows");
      await page.getByRole("button", { name: "Create Show" }).click();

      await expect(page.getByRole("heading", { name: "Create Show" })).toBeVisible();
      await expect(page.getByText("Schedule a new live show")).toBeVisible();

      await page.getByLabel("Title *").fill(showTitle);
      await page.getByRole("button", { name: "Create" }).click();

      await expect(page.getByRole("heading", { name: "Create Show" })).not.toBeVisible({ timeout: 10_000 });
      await expect(page.getByText(showTitle)).toBeVisible({ timeout: 10_000 });
    });

    test("can view show details", async ({ ownerPage: page }) => {
      // First create a show
      const showTitle = `Detail Show ${Date.now().toString(36)}`;
      await page.goto("/shows");
      await page.getByRole("button", { name: "Create Show" }).click();
      await page.getByLabel("Title *").fill(showTitle);
      await page.getByRole("button", { name: "Create" }).click();
      await expect(page.getByRole("heading", { name: "Create Show" })).not.toBeVisible({ timeout: 10_000 });

      // Click the show title link to navigate to detail
      await page.getByText(showTitle).click();
      await expect(page).toHaveURL(/shows\/.+/);
      await expect(page.getByText("Show Details")).toBeVisible();
      await expect(page.getByText(showTitle)).toBeVisible();
    });

    test("can filter shows by status", async ({ ownerPage: page }) => {
      await page.goto("/shows");
      await page.getByText("All statuses").first().click();
      await expect(page.getByText("Planned", { exact: true })).toBeVisible();
      await expect(page.getByText("Live", { exact: true })).toBeVisible();
      await expect(page.getByText("Completed", { exact: true })).toBeVisible();
      await expect(page.getByText("Cancelled", { exact: true })).toBeVisible();
    });

    test("can search shows", async ({ ownerPage: page }) => {
      await page.goto("/shows");
      await expect(page.getByPlaceholder("Search shows…")).toBeVisible();
    });
  });

  test.describe("Orders", () => {
    test("orders page requires admin role", async ({ memberPage: page }) => {
      await page.goto("/orders");
      await expect(page).not.toHaveURL(/orders/);
    });

    test("owner can access orders page", async ({ ownerPage: page }) => {
      await page.getByRole("link", { name: "Orders", exact: true }).click();
      await expect(page).toHaveURL(/orders/);
      await expect(page.getByText("Track and manage your sales")).toBeVisible();
    });

    test("orders table has correct columns", async ({ ownerPage: page }) => {
      await page.goto("/orders");
      await expect(page.getByRole("columnheader", { name: "Buyer" })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: "Item" })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: "Qty" })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: "Price" })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: "Profit" })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: "Status" })).toBeVisible();
    });

    test("can filter orders by status", async ({ ownerPage: page }) => {
      await page.goto("/orders");
      await page.getByText("All statuses").first().click();
      await expect(page.getByText("Pending", { exact: true })).toBeVisible();
      await expect(page.getByText("Shipped", { exact: true })).toBeVisible();
      await expect(page.getByText("Delivered", { exact: true })).toBeVisible();
      await expect(page.getByText("Cancelled", { exact: true })).toBeVisible();
    });

    test("can open create order dialog", async ({ ownerPage: page }) => {
      await page.goto("/orders");
      await page.getByRole("button", { name: "Create Order" }).click();
      await expect(page.getByRole("heading", { name: "Create Order" })).toBeVisible();
      await expect(page.getByText("Record a new sale")).toBeVisible();
      await expect(page.getByLabel("Buyer Username *")).toBeVisible();
      await expect(page.getByLabel("Sale Price *")).toBeVisible();
    });
  });
});
