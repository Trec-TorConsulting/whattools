import { test, expect } from "./fixtures";

test.describe("Shipping", () => {
  test("shipments page requires admin role", async ({ memberPage: page }) => {
    await page.goto("/shipments");
    await expect(page).not.toHaveURL(/shipments/);
  });

  test("owner can access shipments page", async ({ ownerPage: page }) => {
    await page.getByRole("link", { name: "Shipments", exact: true }).click();
    await expect(page).toHaveURL(/shipments/);
    await expect(page.getByText("Track and fulfill your orders")).toBeVisible();
  });

  test("shipments table has correct columns", async ({ ownerPage: page }) => {
    await page.goto("/shipments");
    await expect(page.getByRole("columnheader", { name: "Buyer" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Carrier" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Tracking" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Destination" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Ship By" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Status" })).toBeVisible();
  });

  test("can filter shipments by status", async ({ ownerPage: page }) => {
    await page.goto("/shipments");
    await page.getByText("All statuses").first().click();
    await expect(page.getByText("Pending", { exact: true })).toBeVisible();
    await expect(page.getByText("Label Created", { exact: true })).toBeVisible();
    await expect(page.getByText("Shipped", { exact: true })).toBeVisible();
    await expect(page.getByText("Delivered", { exact: true })).toBeVisible();
    await expect(page.getByText("Cancelled", { exact: true })).toBeVisible();
  });

  test("can search shipments", async ({ ownerPage: page }) => {
    await page.goto("/shipments");
    await expect(page.getByPlaceholder("Search shipments…")).toBeVisible();
  });

  test("shows empty state or shipment data", async ({ ownerPage: page }) => {
    await page.goto("/shipments");
    // Either we see shipment data or the empty state
    const hasData = await page.getByRole("table").isVisible().catch(() => false);
    if (!hasData) {
      await expect(page.getByText("No shipments")).toBeVisible();
      await expect(page.getByText("Shipments will appear here when orders are ready to ship.")).toBeVisible();
    }
  });
});
