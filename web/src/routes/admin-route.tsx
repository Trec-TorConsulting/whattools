import { Navigate, Outlet } from "react-router";
import { useAuth } from "@/hooks/use-auth";
import { isPlatformAdmin } from "@/lib/role-utils";

export function AdminRoute() {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;
  if (!isPlatformAdmin(user)) return <Navigate to="/dashboard" replace />;

  return <Outlet />;
}
