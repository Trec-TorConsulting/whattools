import { api } from "@/lib/api-client";
import type { Shipment, CreateShipment } from "@/lib/schemas";

type ListParams = {
  cursor?: string;
  limit?: number;
  status?: string;
  search?: string;
};

export const shippingApi = {
  listShipments: (params?: ListParams) => {
    const query = new URLSearchParams();
    if (params?.cursor) query.set("cursor", params.cursor);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.status) query.set("status", params.status);
    if (params?.search) query.set("search", params.search);
    const qs = query.toString();
    return api.get<Shipment[]>(`/api/v1/shipments${qs ? `?${qs}` : ""}`);
  },

  getShipment: (id: string) => api.get<Shipment>(`/api/v1/shipments/${id}`),

  createShipment: (data: CreateShipment) => api.post<Shipment>("/api/v1/shipments", data),

  updateShipment: (id: string, data: Partial<CreateShipment>) =>
    api.put<Shipment>(`/api/v1/shipments/${id}`, data),

  deleteShipment: (id: string) => api.delete(`/api/v1/shipments/${id}`),

  createLabel: (id: string) => api.post<Shipment>(`/api/v1/shipments/${id}/label`),

  markShipped: (id: string, data?: { tracking_number?: string }) =>
    api.post<Shipment>(`/api/v1/shipments/${id}/ship`, data),

  markDelivered: (id: string) => api.post<Shipment>(`/api/v1/shipments/${id}/deliver`),

  cancelShipment: (id: string) => api.post<Shipment>(`/api/v1/shipments/${id}/cancel`),

  bulkCreate: (orderIds: string[]) =>
    api.post<Shipment[]>("/api/v1/shipments/bulk", { order_ids: orderIds }),

  listOverdue: () => api.get<Shipment[]>("/api/v1/shipments/overdue"),

  getPackingList: (showId: string) =>
    api.get<{ show: { id: string; title: string }; items: Array<{ order_id: string; buyer_username: string; item_name: string; quantity: number; status: string }> }>(
      `/api/v1/shipments/packing-list/${showId}`
    ),
};
