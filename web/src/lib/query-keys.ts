export const queryKeys = {
  // Auth
  user: {
    current: ["user", "me"] as const,
  },

  // Account
  account: {
    detail: ["account"] as const,
    members: ["account", "members"] as const,
  },

  // Inventory
  items: {
    all: ["items"] as const,
    list: (filters?: Record<string, unknown>) => ["items", "list", filters] as const,
    detail: (id: string) => ["items", "detail", id] as const,
    deleted: ["items", "deleted"] as const,
  },

  categories: {
    all: ["categories"] as const,
    list: () => ["categories", "list"] as const,
    detail: (id: string) => ["categories", "detail", id] as const,
  },

  csvImport: {
    job: (id: string) => ["csv", "job", id] as const,
  },

  // Sales
  shows: {
    all: ["shows"] as const,
    list: (filters?: Record<string, unknown>) => ["shows", "list", filters] as const,
    detail: (id: string) => ["shows", "detail", id] as const,
    orders: (showId: string) => ["shows", showId, "orders"] as const,
  },

  orders: {
    all: ["orders"] as const,
    list: (filters?: Record<string, unknown>) => ["orders", "list", filters] as const,
    detail: (id: string) => ["orders", "detail", id] as const,
    deleted: ["orders", "deleted"] as const,
  },

  // Shipping
  shipments: {
    all: ["shipments"] as const,
    list: (filters?: Record<string, unknown>) => ["shipments", "list", filters] as const,
    detail: (id: string) => ["shipments", "detail", id] as const,
    overdue: ["shipments", "overdue"] as const,
    deleted: ["shipments", "deleted"] as const,
  },

  packingList: {
    byShow: (showId: string) => ["packing-list", showId] as const,
  },

  // Analytics
  analytics: {
    summary: (period: string) => ["analytics", "summary", period] as const,
    categories: (period: string) => ["analytics", "categories", period] as const,
    shows: (period: string) => ["analytics", "shows", period] as const,
    trends: (period: string, granularity?: string) => ["analytics", "trends", period, granularity] as const,
    topItems: (period: string, sortBy?: string) => ["analytics", "top-items", period, sortBy] as const,
    showTimeSuggestions: ["analytics", "show-time-suggestions"] as const,
  },

  exports: {
    all: ["exports"] as const,
    list: () => ["exports", "list"] as const,
    detail: (id: string) => ["exports", "detail", id] as const,
  },

  // Whatnot
  whatnot: {
    status: ["whatnot", "status"] as const,
    syncStatus: ["whatnot", "sync-status"] as const,
    listings: (filters?: Record<string, unknown>) => ["whatnot", "listings", filters] as const,
    listing: (id: string) => ["whatnot", "listing", id] as const,
    taxonomy: ["whatnot", "taxonomy"] as const,
    taxonomyNode: (id: string) => ["whatnot", "taxonomy", id] as const,
  },

  // Billing
  billing: {
    subscription: ["billing", "subscription"] as const,
  },
} as const;
