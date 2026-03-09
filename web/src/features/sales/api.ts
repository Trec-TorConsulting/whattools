import { api } from "@/lib/api-client";
import type { Show, Order, CreateShow, CreateOrder } from "@/lib/schemas";

type ListParams = {
  cursor?: string;
  limit?: number;
  status?: string;
  search?: string;
};

export const salesApi = {
  // Shows
  listShows: (params?: ListParams) => {
    const query = new URLSearchParams();
    if (params?.cursor) query.set("cursor", params.cursor);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.status) query.set("status", params.status);
    if (params?.search) query.set("search", params.search);
    const qs = query.toString();
    return api.get<Show[]>(`/api/v1/shows${qs ? `?${qs}` : ""}`);
  },

  getShow: (id: string) => api.get<Show>(`/api/v1/shows/${id}`),

  createShow: (data: CreateShow) => api.post<Show>("/api/v1/shows", data),

  updateShow: (id: string, data: Partial<CreateShow>) => api.put<Show>(`/api/v1/shows/${id}`, data),

  deleteShow: (id: string) => api.delete(`/api/v1/shows/${id}`),

  startShow: (id: string) => api.post<Show>(`/api/v1/shows/${id}/start`),

  completeShow: (id: string) => api.post<Show>(`/api/v1/shows/${id}/complete`),

  cancelShow: (id: string) => api.post<Show>(`/api/v1/shows/${id}/cancel`),

  // Orders
  listOrders: (params?: ListParams & { show_id?: string }) => {
    const query = new URLSearchParams();
    if (params?.cursor) query.set("cursor", params.cursor);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.status) query.set("status", params.status);
    if (params?.show_id) query.set("show_id", params.show_id);
    if (params?.search) query.set("search", params.search);
    const qs = query.toString();
    return api.get<Order[]>(`/api/v1/orders${qs ? `?${qs}` : ""}`);
  },

  getOrder: (id: string) => api.get<Order>(`/api/v1/orders/${id}`),

  createOrder: (data: CreateOrder) => api.post<Order>("/api/v1/orders", data),

  updateOrder: (id: string, data: Partial<CreateOrder>) => api.put<Order>(`/api/v1/orders/${id}`, data),

  deleteOrder: (id: string) => api.delete(`/api/v1/orders/${id}`),

  shipOrder: (id: string) => api.post<Order>(`/api/v1/orders/${id}/ship`),

  deliverOrder: (id: string) => api.post<Order>(`/api/v1/orders/${id}/deliver`),

  cancelOrder: (id: string) => api.post<Order>(`/api/v1/orders/${id}/cancel`),
};
