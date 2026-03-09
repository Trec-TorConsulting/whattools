import { api } from "@/lib/api-client";
import type { Item, Category, CreateItem } from "@/lib/schemas";

type ListParams = {
  cursor?: string;
  limit?: number;
  status?: string;
  category_id?: string;
  search?: string;
};

export const inventoryApi = {
  // Items
  listItems: (params?: ListParams) => {
    const query = new URLSearchParams();
    if (params?.cursor) query.set("cursor", params.cursor);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.status) query.set("status", params.status);
    if (params?.category_id) query.set("category_id", params.category_id);
    if (params?.search) query.set("search", params.search);
    const qs = query.toString();
    return api.get<Item[]>(`/api/v1/items${qs ? `?${qs}` : ""}`);
  },

  getItem: (id: string) => api.get<Item>(`/api/v1/items/${id}`),

  createItem: (data: CreateItem) => api.post<Item>("/api/v1/items", data),

  updateItem: (id: string, data: Partial<CreateItem>) => api.put<Item>(`/api/v1/items/${id}`, data),

  deleteItem: (id: string) => api.delete(`/api/v1/items/${id}`),

  restoreItem: (id: string) => api.post<Item>(`/api/v1/items/${id}/restore`),

  listDeletedItems: () => api.get<Item[]>("/api/v1/items/deleted"),

  // Categories
  listCategories: () => api.get<Category[]>("/api/v1/categories"),

  createCategory: (data: { name: string }) => api.post<Category>("/api/v1/categories", data),

  updateCategory: (id: string, data: { name: string }) => api.put<Category>(`/api/v1/categories/${id}`, data),

  deleteCategory: (id: string) => api.delete(`/api/v1/categories/${id}`),

  // CSV Import
  importCsv: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.upload<{ job_id: string; status: string }>("/api/v1/items/import", formData);
  },

  getImportStatus: (jobId: string) =>
    api.get<{ job_id: string; status: string; processed: number; errors: string[] }>(
      `/api/v1/items/import/${jobId}`
    ),
};
