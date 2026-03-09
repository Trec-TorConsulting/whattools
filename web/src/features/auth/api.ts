import { api } from "@/lib/api-client";
import type { User } from "@/lib/schemas";

export const authApi = {
  login: (data: { email: string; password: string }) =>
    api.post<{ access_token: string; refresh_token: string; user: User }>("/api/v1/auth/login", data),

  register: (data: { name: string; email: string; password: string; account_name: string }) =>
    api.post("/api/v1/auth/register", data),

  refresh: (refreshToken: string) =>
    api.post<{ access_token: string; refresh_token: string }>("/api/v1/auth/refresh", { refresh_token: refreshToken }),

  logout: () => api.post("/api/v1/auth/logout"),

  forgotPassword: (email: string) => api.post("/api/v1/auth/password-reset", { email }),

  resetPassword: (data: { token: string; password: string }) =>
    api.post("/api/v1/auth/password-reset/confirm", data),

  verifyEmail: (token: string) => api.post("/api/v1/auth/verify-email", { token }),

  getProfile: () => api.get<User>("/api/v1/users/me"),

  updateProfile: (data: { name?: string; email?: string }) => api.put<User>("/api/v1/users/me", data),
};
