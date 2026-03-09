export type Role = "owner" | "admin" | "member";

const ROLE_HIERARCHY: Record<Role, number> = {
  owner: 3,
  admin: 2,
  member: 1,
};

export function isAtLeast(userRole: Role, requiredRole: Role): boolean {
  return ROLE_HIERARCHY[userRole] >= ROLE_HIERARCHY[requiredRole];
}

export function canAccessSales(role: Role): boolean {
  return isAtLeast(role, "admin");
}

export function canAccessShipping(role: Role): boolean {
  return isAtLeast(role, "admin");
}

export function canAccessAnalytics(role: Role): boolean {
  return isAtLeast(role, "admin");
}

export function canManageTeam(role: Role): boolean {
  return isAtLeast(role, "admin");
}

export function canChangeRoles(role: Role): boolean {
  return role === "owner";
}

export function canManageAccount(role: Role): boolean {
  return role === "owner";
}
