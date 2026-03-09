/**
 * Global setup: verify the backend is healthy and seeds are loaded.
 * Runs once before all test projects.
 */
import { test, expect } from "@playwright/test";

test("backend services are healthy", async ({ request }) => {
  const res = await request.get("/api/v1/health");
  expect(res.ok()).toBeTruthy();
});

test("seed data is loaded", async ({ request }) => {
  // Verify we can login as the seeded owner
  const res = await request.post("/api/v1/auth/login", {
    data: { email: "demo@whattools.dev", password: "Password123!" },
  });
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  expect(body.data.user.email).toBe("demo@whattools.dev");
  expect(body.data.user.role).toBe("owner");
});
