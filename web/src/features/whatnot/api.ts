import { api } from "@/lib/api-client";
import type {
  WhatnotStatus,
  WhatnotConnect,
  ProductPullResult,
  SyncStatus,
  WhatnotListing,
  OrderTracking,
} from "@/lib/schemas";

type ListParams = {
  cursor?: string;
  limit?: number;
};

export const whatnotApi = {
  // OAuth
  connect: () => api.get<WhatnotConnect>("/api/v1/whatnot/connect"),

  disconnect: () => api.post("/api/v1/whatnot/disconnect"),

  status: () => api.get<WhatnotStatus>("/api/v1/whatnot/status"),

  // Products
  pullProducts: () => api.post<ProductPullResult>("/api/v1/whatnot/products/pull"),

  pushProduct: (inventoryItemId: string) =>
    api.post("/api/v1/whatnot/products/push", { inventory_item_id: inventoryItemId }),

  syncProduct: (itemId: string) => api.post(`/api/v1/whatnot/products/${itemId}/sync`),

  unlinkProduct: (itemId: string) => api.post(`/api/v1/whatnot/products/${itemId}/unlink`),

  // Listings
  listListings: (params?: ListParams) => {
    const query = new URLSearchParams();
    if (params?.cursor) query.set("cursor", params.cursor);
    if (params?.limit) query.set("limit", String(params.limit));
    const qs = query.toString();
    return api.get<WhatnotListing[]>(`/api/v1/whatnot/listings${qs ? `?${qs}` : ""}`);
  },

  getListing: (id: string) => api.get<WhatnotListing>(`/api/v1/whatnot/listings/${id}`),

  updateListing: (id: string, data: Partial<WhatnotListing>) =>
    api.put(`/api/v1/whatnot/listings/${id}`, data),

  deleteListing: (id: string) => api.delete(`/api/v1/whatnot/listings/${id}`),

  publishListing: (id: string) => api.post(`/api/v1/whatnot/listings/${id}/publish`),

  unpublishListing: (id: string) => api.post(`/api/v1/whatnot/listings/${id}/unpublish`),

  // Orders
  syncOrders: () => api.post("/api/v1/whatnot/orders/sync"),

  pushTracking: (orderId: string, data: OrderTracking) =>
    api.post(`/api/v1/whatnot/orders/${orderId}/tracking`, data),

  cancelOrder: (orderId: string) => api.post(`/api/v1/whatnot/orders/${orderId}/cancel`),

  // Livestreams
  syncLivestreams: () => api.post("/api/v1/whatnot/livestreams/sync"),

  // Sync
  fullSync: () => api.post("/api/v1/whatnot/sync/now"),

  syncStatus: () => api.get<SyncStatus>("/api/v1/whatnot/sync/status"),

  // Taxonomy
  getTaxonomy: () => api.get("/api/v1/whatnot/taxonomy"),

  getTaxonomyNode: (id: string) => api.get(`/api/v1/whatnot/taxonomy/${id}`),
};
