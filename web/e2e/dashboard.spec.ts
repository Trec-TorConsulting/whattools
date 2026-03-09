import { test, expect, OWNER_USER, MEMBER_USER } from "./fixtures";

test.describe("Dashboard", () => {
  test("owner sees full dashboard with KPI cards", async ({ ownerPage: page }) => {
    await expect(page.getByText("Welcome back")).toBeVisible();
    await expect(page.getByText("Here's what's happening with your business today")).toBeVisible();

    // KPI cards visible for owner
    await expect(page.getByText("Total Revenue")).toBeVisible();
    await expect(page.getByText("Total Profit")).toBeVisible();
    await expect(page.getByText("Total Orders")).toBeVisible();
    await expect(page.getByText("Total Shows")).toBeVisible();
  });

  test("owner sees all dashboard sections", async ({ ownerPage: page }) => {
    await expect(page.getByText("Recent Inventory")).toBeVisible();
    await expect(page.getByText("Upcoming Shows")).toBeVisible();
    await expect(page.getByText("Recent Orders")).toBeVisible();
    await expect(page.getByText("Pending Shipments")).toBeVisible();
  });

  test("member sees limited dashboard without sales cards", async ({ memberPage: page }) => {
    await expect(page.getByText("Welcome back")).toBeVisible();
    await expect(page.getByText("Recent Inventory")).toBeVisible();

    // Member should NOT see admin-only KPI cards
    await expect(page.getByText("Total Revenue")).not.toBeVisible();
    await expect(page.getByText("Upcoming Shows")).not.toBeVisible();
  });

  test("dashboard 'View all' links navigate correctly", async ({ ownerPage: page }) => {
    const viewAllLinks = page.getByText("View all");
    const count = await viewAllLinks.count();
    expect(count).toBeGreaterThanOrEqual(1);

    // Click the first "View all" link (Recent Inventory → /inventory)
    await viewAllLinks.first().click();
    await expect(page).toHaveURL(/inventory/);
  });
});
