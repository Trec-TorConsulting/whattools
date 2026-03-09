import { http, HttpResponse, delay } from "msw";

const testUser = {
  id: "user-1",
  name: "Test User",
  email: "test@example.com",
  role: "owner" as const,
  account_id: "acc-1",
  created_at: "2024-01-01T00:00:00Z",
};

const testCategories = [
  { id: "cat-1", name: "Electronics", description: "Electronic items", item_count: 5, created_at: "2024-01-01T00:00:00Z" },
  { id: "cat-2", name: "Clothing", description: "Clothing items", item_count: 3, created_at: "2024-01-01T00:00:00Z" },
];

const testItems = [
  {
    id: "item-1",
    name: "Test Item",
    sku: "TST-001",
    quantity: 10,
    cogs: "25.00",
    sale_price: "49.99",
    status: "available",
    category_id: "cat-1",
    category_name: "Electronics",
    notes: "",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
];

const testSummary = {
  total_revenue: 5000,
  total_profit: 2000,
  total_orders: 50,
  total_shows: 10,
  inventory_value: 15000,
  items_count: 100,
};

export const handlers = [
  // Auth
  http.post("/api/v1/auth/login", async () => {
    await delay(50);
    return HttpResponse.json({
      data: {
        user: testUser,
        access_token: "test-access-token",
        refresh_token: "test-refresh-token",
      },
    });
  }),

  http.post("/api/v1/auth/register", async () => {
    await delay(50);
    return HttpResponse.json({
      data: { message: "Registration successful. Please check your email." },
    });
  }),

  http.get("/api/v1/users/me", () => {
    return HttpResponse.json({ data: testUser });
  }),

  http.post("/api/v1/auth/logout", () => {
    return HttpResponse.json({ data: { message: "Logged out" } });
  }),

  // Dashboard
  http.get("/api/v1/dashboard/summary", () => {
    return HttpResponse.json({ data: testSummary });
  }),

  http.get("/api/v1/dashboard/recent-items", () => {
    return HttpResponse.json({ data: testItems });
  }),

  http.get("/api/v1/dashboard/upcoming-shows", () => {
    return HttpResponse.json({ data: [] });
  }),

  http.get("/api/v1/dashboard/recent-orders", () => {
    return HttpResponse.json({ data: [] });
  }),

  http.get("/api/v1/dashboard/pending-shipments", () => {
    return HttpResponse.json({ data: [] });
  }),

  // Inventory
  http.get("/api/v1/items", ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get("search") ?? "";
    const items = search
      ? testItems.filter((i) => i.name.toLowerCase().includes(search.toLowerCase()))
      : testItems;
    return HttpResponse.json({
      data: items,
      meta: { next_cursor: null },
    });
  }),

  http.post("/api/v1/items", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      data: { id: "item-new", ...body, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
    }, { status: 201 });
  }),

  http.get("/api/v1/categories", () => {
    return HttpResponse.json({ data: testCategories });
  }),

  // Analytics
  http.get("/api/v1/analytics/summary", () => {
    return HttpResponse.json({
      data: {
        total_revenue: 5000,
        total_profit: 2000,
        total_orders: 50,
        order_count: 50,
        avg_order_value: 100,
        profit_margin: 40,
      },
    });
  }),

  http.get("/api/v1/analytics/trends", () => {
    return HttpResponse.json({
      data: [
        { date: "2024-01-01", revenue: 500, profit: 200 },
        { date: "2024-01-02", revenue: 600, profit: 250 },
      ],
    });
  }),

  http.get("/api/v1/analytics/categories", () => {
    return HttpResponse.json({
      data: [
        { name: "Electronics", revenue: 3000, profit: 1200, item_count: 20, order_count: 30 },
      ],
    });
  }),

  http.get("/api/v1/analytics/top-items", () => {
    return HttpResponse.json({
      data: [
        { id: "item-1", name: "Test Item", revenue: 1000, quantity_sold: 20, profit: 500 },
      ],
    });
  }),

  // Settings
  http.get("/api/v1/account", () => {
    return HttpResponse.json({
      data: { id: "acc-1", name: "Test Account", plan: "pro", created_at: "2024-01-01T00:00:00Z" },
    });
  }),

  http.get("/api/v1/team/members", () => {
    return HttpResponse.json({
      data: [
        { id: "user-1", name: "Test User", email: "test@example.com", role: "owner", created_at: "2024-01-01T00:00:00Z" },
        { id: "user-2", name: "Team Member", email: "member@example.com", role: "member", created_at: "2024-01-02T00:00:00Z" },
      ],
    });
  }),
];
