import { api } from "@/lib/api-client";
import type { Account, TeamMember, User } from "@/lib/schemas";

export const settingsApi = {
  // Account
  getAccount: () => api.get<Account>("/api/v1/account"),

  updateAccount: (data: { name: string }) => api.put<Account>("/api/v1/account", data),

  // Team members
  listMembers: () => api.get<TeamMember[]>("/api/v1/account/members"),

  inviteMember: (data: { email: string; role: "admin" | "member" }) =>
    api.post<TeamMember>("/api/v1/account/members/invite", data),

  updateMemberRole: (memberId: string, role: "admin" | "member") =>
    api.put<TeamMember>(`/api/v1/account/members/${memberId}`, { role }),

  removeMember: (memberId: string) => api.delete(`/api/v1/account/members/${memberId}`),

  // Profile
  updateProfile: (data: { name?: string; email?: string }) =>
    api.put<User>("/api/v1/users/me", data),

  changePassword: (data: { current_password: string; new_password: string }) =>
    api.post("/api/v1/users/me/password", data),
};
