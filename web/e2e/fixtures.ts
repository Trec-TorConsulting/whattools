import { test as base, expect, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";

// Seed data credentials (from scripts/seed.py)
export const OWNER_USER = {
  email: "demo@whattools.dev",
  password: "Password123!",
  name: "Demo User",
  role: "owner",
};

export const MEMBER_USER = {
  email: "member@whattools.dev",
  password: "Member123!",
  name: "Member User",
  role: "member",
};

/** Create a fresh user via the API and return credentials */
export async function createTestUser(
  request: Page["request"],
  overrides: Partial<{
    name: string;
    email: string;
    password: string;
    account_name: string;
  }> = {},
) {
  const unique = `${Date.now().toString(36)}-${randomUUID().slice(0, 8)}`;
  const user = {
    name: overrides.name ?? `Test User ${unique}`,
    email: overrides.email ?? `test-${unique}@whattools.dev`,
    password: overrides.password ?? "Test1234!",
    confirm_password: overrides.password ?? "Test1234!",
    account_name: overrides.account_name ?? `Test Account ${unique}`,
  };
  return user;
}

/** Login via the UI and wait for dashboard */
export async function loginAs(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign In" }).click();
  await page.waitForURL("**/dashboard");
}

/** Login via API and set tokens in localStorage (faster) */
export async function loginViaApi(page: Page, email: string, password: string) {
  const response = await page.request.post("/api/v1/auth/login", {
    data: { email, password },
  });
  const body = await response.json();
  const { access_token, refresh_token } = body.data;

  await page.goto("/login"); // need a page context to set localStorage
  await page.evaluate(
    ([at, rt]) => {
      localStorage.setItem("whattools_access_token", at);
      localStorage.setItem("whattools_refresh_token", rt);
    },
    [access_token, refresh_token],
  );
}

/** Navigate using the sidebar */
export async function navigateTo(page: Page, label: string) {
  await page.getByRole("link", { name: label, exact: true }).click();
}

/** Extended test fixture with pre-authenticated pages */
type Fixtures = {
  ownerPage: Page;
  memberPage: Page;
};

export const test = base.extend<Fixtures>({
  ownerPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await loginViaApi(page, OWNER_USER.email, OWNER_USER.password);
    await page.goto("/dashboard");
    await page.waitForURL("**/dashboard");
    await use(page);
    await context.close();
  },
  memberPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await loginViaApi(page, MEMBER_USER.email, MEMBER_USER.password);
    await page.goto("/dashboard");
    await page.waitForURL("**/dashboard");
    await use(page);
    await context.close();
  },
});

export { expect };
