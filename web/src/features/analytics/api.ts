import { api } from "@/lib/api-client";
import type {
  AnalyticsSummary,
  TrendPoint,
  CategoryAnalytics,
  TopItem,
  ExportJob,
  CreateExport,
} from "@/lib/schemas";

export const analyticsApi = {
  getSummary: (period = "30d") =>
    api.get<AnalyticsSummary>(`/api/v1/analytics/summary?period=${period}`),

  getCategories: (period = "30d") =>
    api.get<CategoryAnalytics[]>(`/api/v1/analytics/categories?period=${period}`),

  getShows: (period = "30d") =>
    api.get<Array<{ show_id: string; show_title: string; revenue: number; profit: number; orders: number; date: string }>>(
      `/api/v1/analytics/shows?period=${period}`
    ),

  getTrends: (period = "30d", granularity = "day") =>
    api.get<TrendPoint[]>(`/api/v1/analytics/trends?period=${period}&granularity=${granularity}`),

  getTopItems: (period = "30d", sortBy = "revenue") =>
    api.get<TopItem[]>(`/api/v1/analytics/top-items?period=${period}&sort_by=${sortBy}`),

  getShowTimeSuggestions: () =>
    api.get<{
      recommendations: Array<{ day: string; hour: number; score: number; avg_revenue: number; avg_profit: number; avg_orders: number; show_count: number }>;
      avoid_slots: Array<{ day: string; hour: number; score: number; avg_revenue: number; avg_profit: number; avg_orders: number; show_count: number }>;
      category_insights: Array<{ category: string; best_day: string; best_hour: number; avg_profit: number }>;
    }>("/api/v1/analytics/show-time-suggestions"),

  // Exports
  listExports: () => api.get<ExportJob[]>("/api/v1/exports"),

  createExport: (data: CreateExport) => api.post<ExportJob>("/api/v1/exports", data),

  getExport: (id: string) => api.get<ExportJob>(`/api/v1/exports/${id}`),

  downloadExport: (id: string) => api.download(`/api/v1/exports/${id}/download`),
};
