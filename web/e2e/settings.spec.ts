import { test, expect, OWNER_USER, MEMBER_USER } from "./fixtures";
import { loginAs } from "./fixtures";

test.describe("Settings", () => {
  test.describe("Navigation", () => {
    test("owner sees all settings tabs", async ({ ownerPage: page }) => {
      await page.getByRole("link", { name: "Settings", exact: true }).click();
      await expect(page).toHaveURL(/settings/);
      await expect(page.getByText("Manage your account and preferences")).toBeVisible();
      await expect(page.getByText("Profile")).toBeVisible();
      await expect(page.getByText("Team")).toBeVisible();
      await expect(page.getByText("Account")).toBeVisible();
    });

    test("member sees only Profile tab", async ({ memberPage: page }) => {
      await page.getByRole("link", { name: "Settings", exact: true }).click();
      await expect(page).toHaveURL(/settings/);
      await expect(page.getByText("Profile")).toBeVisible();
      // Member should not see Team or Account tabs
      await expect(page.getByRole("link", { name: "Team" })).not.toBeVisible();
      await expect(page.getByRole("link", { name: "Account" })).not.toBeVisible();
    });
  });

  test.describe("Profile", () => {
    test("shows profile form with current user data", async ({ ownerPage: page }) => {
      await page.goto("/settings");
      await expect(page.getByText("Update your personal information")).toBeVisible();
      await expect(page.getByLabel("Name")).toBeVisible();
      await expect(page.getByLabel("Email")).toBeVisible();
      await expect(page.getByRole("button", { name: "Save Changes" })).toBeVisible();
    });

    test("shows change password form", async ({ ownerPage: page }) => {
      await page.goto("/settings");
      await expect(page.getByText("Change Password")).toBeVisible();
      await expect(page.getByLabel("Current Password")).toBeVisible();
      await expect(page.getByLabel("New Password")).toBeVisible();
      await expect(page.getByLabel("Confirm New Password")).toBeVisible();
      await expect(page.getByRole("button", { name: "Change Password" })).toBeVisible();
    });

    test("can update profile name", async ({ ownerPage: page }) => {
      await page.goto("/settings");
      const nameInput = page.getByLabel("Name");
      const originalName = await nameInput.inputValue();

      await nameInput.fill("Updated E2E Name");
      await page.getByRole("button", { name: "Save Changes" }).click();

      // Wait for success feedback (toast or form reset)
      await page.waitForTimeout(2_000);

      // Restore original name
      await nameInput.fill(originalName);
      await page.getByRole("button", { name: "Save Changes" }).click();
      await page.waitForTimeout(1_000);
    });
  });

  test.describe("Team", () => {
    test("owner can access team settings", async ({ ownerPage: page }) => {
      await page.goto("/settings/team");
      await expect(page.getByText("Manage your team members and roles")).toBeVisible();
      await expect(page.getByRole("button", { name: "Invite Member" })).toBeVisible();
    });

    test("shows existing team members", async ({ ownerPage: page }) => {
      await page.goto("/settings/team");
      // Seed data has at least the owner and member users
      await expect(page.getByText(OWNER_USER.email)).toBeVisible({ timeout: 10_000 });
    });

    test("can open invite member dialog", async ({ ownerPage: page }) => {
      await page.goto("/settings/team");
      await page.getByRole("button", { name: "Invite Member" }).click();

      await expect(page.getByRole("heading", { name: "Invite Team Member" })).toBeVisible();
      await expect(page.getByText("Send an invitation to join your team")).toBeVisible();
      await expect(page.getByLabel("Email")).toBeVisible();
      await expect(page.getByText("Role")).toBeVisible();
      await expect(page.getByRole("button", { name: "Send Invitation" })).toBeVisible();
    });

    test("shows role badges for team members", async ({ ownerPage: page }) => {
      await page.goto("/settings/team");
      await expect(page.getByText("owner")).toBeVisible({ timeout: 10_000 });
    });
  });

  test.describe("Account", () => {
    test("owner can access account settings", async ({ ownerPage: page }) => {
      await page.goto("/settings/account");
      await expect(page.getByText("Account Details")).toBeVisible();
      await expect(page.getByText("Manage your business account settings")).toBeVisible();
      await expect(page.getByLabel("Business Name")).toBeVisible();
    });

    test("shows current plan tier", async ({ ownerPage: page }) => {
      await page.goto("/settings/account");
      await expect(page.getByText("Plan")).toBeVisible();
      await expect(page.getByText("Current subscription tier")).toBeVisible();
      // Seed data uses FREE tier
      await expect(page.getByText("FREE")).toBeVisible({ timeout: 10_000 });
    });

    test("member cannot access account settings", async ({ memberPage: page }) => {
      await page.goto("/settings/account");
      // Should redirect away or show unauthorized
      await expect(page.getByText("Account Details")).not.toBeVisible();
    });
  });
});

test.describe("Role-Based Access Control", () => {
  test("sidebar shows limited nav for member", async ({ memberPage: page }) => {
    // Member should only see: Dashboard, Inventory, Settings
    await expect(page.getByRole("link", { name: "Dashboard", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Inventory", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Settings", exact: true })).toBeVisible();

    // Member should NOT see admin-only nav items
    await expect(page.getByRole("link", { name: "Shows", exact: true })).not.toBeVisible();
    await expect(page.getByRole("link", { name: "Orders", exact: true })).not.toBeVisible();
    await expect(page.getByRole("link", { name: "Shipments", exact: true })).not.toBeVisible();
    await expect(page.getByRole("link", { name: "Analytics", exact: true })).not.toBeVisible();
  });

  test("sidebar shows full nav for owner", async ({ ownerPage: page }) => {
    await expect(page.getByRole("link", { name: "Dashboard", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Inventory", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Shows", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Orders", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Shipments", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Analytics", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Settings", exact: true })).toBeVisible();
  });

  test("member is redirected from admin routes", async ({ memberPage: page }) => {
    // Try each admin-only route
    for (const route of ["/shows", "/orders", "/shipments", "/analytics"]) {
      await page.goto(route);
      await expect(page).not.toHaveURL(new RegExp(route.replace("/", "\\/")));
    }
  });

  test("theme toggle works", async ({ ownerPage: page }) => {
    // Find and click theme toggle
    await page.getByRole("button", { name: "Toggle theme" }).click();
    await expect(page.getByText("Light")).toBeVisible();
    await expect(page.getByText("Dark")).toBeVisible();
    await expect(page.getByText("System")).toBeVisible();

    // Switch to dark mode
    await page.getByText("Dark").click();
    // Check that the dark class is applied
    const hasDark = await page.locator("html.dark").count();
    expect(hasDark).toBe(1);

    // Switch back to light
    await page.getByRole("button", { name: "Toggle theme" }).click();
    await page.getByText("Light").click();
    const hasLight = await page.locator("html.dark").count();
    expect(hasLight).toBe(0);
  });
});
