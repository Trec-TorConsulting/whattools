import type { ReactNode } from "react";
import { useAuth } from "@/hooks/use-auth";
import { isAtLeast, type Role } from "@/lib/role-utils";

type RoleGuardProps = {
  roles: Role[];
  children: ReactNode;
  fallback?: ReactNode;
};

export function RoleGuard({ roles, children, fallback = null }: RoleGuardProps) {
  const { user } = useAuth();
  if (!user) return null;

  const hasAccess = roles.some((role) => isAtLeast(user.role, role));
  return hasAccess ? <>{children}</> : <>{fallback}</>;
}
