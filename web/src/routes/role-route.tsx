import { Navigate, Outlet } from "react-router";
import { useAuth } from "@/hooks/use-auth";
import { isAtLeast, type Role } from "@/lib/role-utils";

export function RoleRoute({ roles }: { roles: Role[] }) {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;

  const hasAccess = roles.some((role) => isAtLeast(user.role, role));
  if (!hasAccess) return <Navigate to="/dashboard" replace />;

  return <Outlet />;
}
