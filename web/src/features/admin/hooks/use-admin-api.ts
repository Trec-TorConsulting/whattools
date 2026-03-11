import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

// Types
export type AdminAccount = {
  id: string;
  name: string;
  plan_tier: "free" | "paid";
  is_suspended: boolean;
  subscription_status: string | null;
  user_count: number;
  created_at: string;
  updated_at: string;
  stripe_customer_id?: string | null;
};

export type AdminUser = {
  id: string;
  email: string;
  name: string;
  role: "owner" | "admin" | "member";
  account_id: string;
  is_active: boolean;
  is_verified: boolean;
  is_platform_admin: boolean;
  created_at: string;
  updated_at: string;
};

export type PlatformMetrics = {
  total_accounts: number;
  active_accounts: number;
  suspended_accounts: number;
  total_users: number;
  active_users: number;
  free_accounts: number;
  paid_accounts: number;
  mrr: number;
  recent_signups: number;
};

export type AdminAuditLogEntry = {
  id: string;
  admin_id: string;
  action: string;
  target_type: string;
  target_id: string | null;
  changes: Record<string, unknown> | null;
  description: string | null;
  ip_address: string | null;
  timestamp: string;
};

export type Pagination = {
  page: number;
  per_page: number;
  total: number;
  pages: number;
};

// Hooks

export function useAdminMetrics() {
  return useQuery({
    queryKey: ["admin", "metrics"],
    queryFn: async () => {
      const { data } = await api.get<PlatformMetrics>("/api/v1/admin/metrics");
      return data;
    },
  });
}

export function useAdminAccounts(params: {
  page?: number;
  per_page?: number;
  search?: string;
  plan_tier?: string;
  is_suspended?: boolean;
} = {}) {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.per_page) searchParams.set("per_page", String(params.per_page));
  if (params.search) searchParams.set("search", params.search);
  if (params.plan_tier) searchParams.set("plan_tier", params.plan_tier);
  if (params.is_suspended !== undefined) searchParams.set("is_suspended", String(params.is_suspended));

  const qs = searchParams.toString();
  return useQuery({
    queryKey: ["admin", "accounts", params],
    queryFn: async () => {
      const result = await api.get<AdminAccount[]>(`/api/v1/admin/accounts${qs ? `?${qs}` : ""}`);
      return {
        accounts: result.data,
        pagination: result.meta.pagination as Pagination,
      };
    },
  });
}

export function useAdminAccount(accountId: string) {
  return useQuery({
    queryKey: ["admin", "accounts", accountId],
    queryFn: async () => {
      const { data } = await api.get<AdminAccount>(`/api/v1/admin/accounts/${accountId}`);
      return data;
    },
    enabled: !!accountId,
  });
}

export function useAdminUsers(params: {
  page?: number;
  per_page?: number;
  search?: string;
  account_id?: string;
  is_platform_admin?: boolean;
} = {}) {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.per_page) searchParams.set("per_page", String(params.per_page));
  if (params.search) searchParams.set("search", params.search);
  if (params.account_id) searchParams.set("account_id", params.account_id);
  if (params.is_platform_admin !== undefined) searchParams.set("is_platform_admin", String(params.is_platform_admin));

  const qs = searchParams.toString();
  return useQuery({
    queryKey: ["admin", "users", params],
    queryFn: async () => {
      const result = await api.get<AdminUser[]>(`/api/v1/admin/users${qs ? `?${qs}` : ""}`);
      return {
        users: result.data,
        pagination: result.meta.pagination as Pagination,
      };
    },
  });
}

export function useAdminAuditLogs(params: {
  page?: number;
  per_page?: number;
  admin_id?: string;
  action?: string;
} = {}) {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.per_page) searchParams.set("per_page", String(params.per_page));
  if (params.admin_id) searchParams.set("admin_id", params.admin_id);
  if (params.action) searchParams.set("action", params.action);

  const qs = searchParams.toString();
  return useQuery({
    queryKey: ["admin", "audit-logs", params],
    queryFn: async () => {
      const result = await api.get<AdminAuditLogEntry[]>(`/api/v1/admin/audit-logs${qs ? `?${qs}` : ""}`);
      return {
        logs: result.data,
        pagination: result.meta.pagination as Pagination,
      };
    },
  });
}

// Mutations

export function useSuspendAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (accountId: string) => {
      const { data } = await api.post<AdminAccount>(`/api/v1/admin/accounts/${accountId}/suspend`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "accounts"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "metrics"] });
    },
  });
}

export function useUnsuspendAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (accountId: string) => {
      const { data } = await api.post<AdminAccount>(`/api/v1/admin/accounts/${accountId}/unsuspend`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "accounts"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "metrics"] });
    },
  });
}

export function useUpdateAccountPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ accountId, planTier }: { accountId: string; planTier: string }) => {
      const { data } = await api.put<AdminAccount>(`/api/v1/admin/accounts/${accountId}/plan`, {
        plan_tier: planTier,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "accounts"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "metrics"] });
    },
  });
}

export function useResetUserPassword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      const { data } = await api.post<{ reset_token: string; expires_at: string; user_email: string }>(
        `/api/v1/admin/users/${userId}/reset-password`
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "audit-logs"] });
    },
  });
}

export function useTogglePlatformAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      const { data } = await api.post<AdminUser>(`/api/v1/admin/users/${userId}/toggle-admin`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit-logs"] });
    },
  });
}

export function useImpersonateUser() {
  return useMutation({
    mutationFn: async (userId: string) => {
      const { data } = await api.post<{ access_token: string; token_type: string; user: AdminUser }>(
        `/api/v1/admin/users/${userId}/impersonate`
      );
      return data;
    },
  });
}
