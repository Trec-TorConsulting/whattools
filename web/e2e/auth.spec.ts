import { test, expect } from "@playwright/test";
import { loginAs, OWNER_USER, MEMBER_USER } from "./fixtures";

test.describe("Authentication", () => {
  test("shows login page with correct branding", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByText("Welcome back")).toBeVisible();
    await expect(page.getByText("Sign in to your WhatTools account")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sign In" })).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign In" })).toBeVisible();
  });

  test("validates empty login form", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "Sign In" }).click();
    // Zod validation errors should appear
    await expect(page.getByText(/email/i)).toBeVisible();
  });

  test("shows error for invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill("wrong@example.com");
    await page.getByLabel("Password").fill("wrongpassword");
    await page.getByRole("button", { name: "Sign In" }).click();
    // Should show an error message (not redirect)
    await expect(page).toHaveURL(/login/);
  });

  test("owner can login and reach dashboard", async ({ page }) => {
    await loginAs(page, OWNER_USER.email, OWNER_USER.password);
    await expect(page).toHaveURL(/dashboard/);
    await expect(page.getByText("Welcome back")).toBeVisible();
  });

  test("member can login and reach dashboard", async ({ page }) => {
    await loginAs(page, MEMBER_USER.email, MEMBER_USER.password);
    await expect(page).toHaveURL(/dashboard/);
    await expect(page.getByText("Welcome back")).toBeVisible();
  });

  test("redirects unauthenticated users to login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/login/);
  });

  test("redirects unauthenticated users from protected routes", async ({ page }) => {
    await page.goto("/inventory");
    await expect(page).toHaveURL(/login/);
  });

  test("user can logout", async ({ page }) => {
    await loginAs(page, OWNER_USER.email, OWNER_USER.password);
    await expect(page).toHaveURL(/dashboard/);

    // Open user dropdown and click logout
    await page.getByRole("button", { name: "Toggle theme" }).locator("..").locator("button").last().click();
    await page.getByText("Log out").click();
    await expect(page).toHaveURL(/login/);
  });

  test("login page links to register", async ({ page }) => {
    await page.goto("/login");
    await page.getByText("Create one").click();
    await expect(page).toHaveURL(/register/);
  });

  test("register page shows correct form", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByText("Create your account")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sign Up" })).toBeVisible();
    await expect(page.getByLabel("Full Name")).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Business Name")).toBeVisible();
    await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Confirm")).toBeVisible();
    await expect(page.getByRole("button", { name: "Create Account" })).toBeVisible();
  });

  test("can register a new account", async ({ page }) => {
    const unique = Date.now().toString(36);
    await page.goto("/register");
    await page.getByLabel("Full Name").fill(`E2E User ${unique}`);
    await page.getByLabel("Email").fill(`e2e-${unique}@whattools.dev`);
    await page.getByLabel("Business Name").fill(`E2E Store ${unique}`);
    await page.getByLabel("Password", { exact: true }).fill("SecurePass123!");
    await page.getByLabel("Confirm").fill("SecurePass123!");
    await page.getByRole("button", { name: "Create Account" }).click();

    // Should show email verification prompt
    await expect(page.getByText("Check your email")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Go to Sign In")).toBeVisible();
  });

  test("register links back to login", async ({ page }) => {
    await page.goto("/register");
    await page.getByText("Sign in").click();
    await expect(page).toHaveURL(/login/);
  });

  test("forgot password page is accessible", async ({ page }) => {
    await page.goto("/login");
    await page.getByText("Forgot password?").click();
    await expect(page).toHaveURL(/forgot-password/);
  });
});
