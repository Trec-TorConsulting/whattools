import { Navigate, useLocation, Outlet } from "react-router";
import { useAuth } from "@/hooks/use-auth";
import { PageSkeleton } from "@/components/loading-skeleton";

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <PageSkeleton />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return <Outlet />;
}
