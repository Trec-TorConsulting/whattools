import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AuthProvider } from "@/lib/auth";
import { AppShell } from "@/components/app-shell";
import { ProtectedRoute } from "@/routes/protected-route";
import { RoleRoute } from "@/routes/role-route";
import "@/globals.css";

// Lazy load pages
import { LoginPage } from "@/features/auth/pages/login";
import { RegisterPage } from "@/features/auth/pages/register";
import { ForgotPasswordPage } from "@/features/auth/pages/forgot-password";
import { VerifyEmailPage } from "@/features/auth/pages/verify-email";
import { DashboardPage } from "@/features/dashboard/pages/dashboard";
import { ItemsListPage } from "@/features/inventory/pages/items-list";
import { CategoriesPage } from "@/features/inventory/pages/categories";
import { ShowsListPage } from "@/features/sales/pages/shows-list";
import { ShowDetailPage } from "@/features/sales/pages/show-detail";
import { OrdersListPage } from "@/features/sales/pages/orders-list";
import { ShipmentsListPage } from "@/features/shipping/pages/shipments-list";
import { ShipmentDetailPage } from "@/features/shipping/pages/shipment-detail";
import { AnalyticsDashboardPage } from "@/features/analytics/pages/analytics-dashboard";
import { ExportsPage } from "@/features/analytics/pages/exports";
import { SettingsLayout } from "@/features/settings/pages/settings-layout";
import { ProfileSettingsPage } from "@/features/settings/pages/profile-settings";
import { TeamSettingsPage } from "@/features/settings/pages/team-settings";
import { AccountSettingsPage } from "@/features/settings/pages/account-settings";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />

            {/* Protected routes */}
            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route path="/dashboard" element={<DashboardPage />} />

                {/* Inventory — all roles */}
                <Route path="/inventory" element={<ItemsListPage />} />
                <Route path="/inventory/categories" element={<CategoriesPage />} />

                {/* Sales — admin+ */}
                <Route element={<RoleRoute roles={["admin", "owner"]} />}>
                  <Route path="/shows" element={<ShowsListPage />} />
                  <Route path="/shows/:id" element={<ShowDetailPage />} />
                  <Route path="/orders" element={<OrdersListPage />} />
                </Route>

                {/* Shipping — admin+ */}
                <Route element={<RoleRoute roles={["admin", "owner"]} />}>
                  <Route path="/shipments" element={<ShipmentsListPage />} />
                  <Route path="/shipments/:id" element={<ShipmentDetailPage />} />
                </Route>

                {/* Analytics — admin+ */}
                <Route element={<RoleRoute roles={["admin", "owner"]} />}>
                  <Route path="/analytics" element={<AnalyticsDashboardPage />} />
                  <Route path="/analytics/exports" element={<ExportsPage />} />
                </Route>

                {/* Settings */}
                <Route path="/settings" element={<SettingsLayout />}>
                  <Route index element={<ProfileSettingsPage />} />
                  <Route path="team" element={<TeamSettingsPage />} />
                  <Route path="account" element={<AccountSettingsPage />} />
                </Route>
              </Route>
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" richColors closeButton />
      </AuthProvider>
    </QueryClientProvider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
