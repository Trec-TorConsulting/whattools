import { api } from "@/lib/api-client";
import type { AnalyticsSummary, Item, Show, Order, Shipment } from "@/lib/schemas";

export const dashboardApi = {
  getSummary: () => api.get<AnalyticsSummary>("/api/v1/analytics/summary?period=30d"),

  getRecentItems: () => api.get<Item[]>("/api/v1/items?limit=5"),

  getUpcomingShows: () => api.get<Show[]>("/api/v1/shows?status=planned&limit=5"),

  getRecentOrders: () => api.get<Order[]>("/api/v1/orders?limit=5"),

  getPendingShipments: () => api.get<Shipment[]>("/api/v1/shipments?status=pending&limit=5"),
};
