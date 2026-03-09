import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@/lib/auth";
import { ProtectedRoute } from "@/routes/protected-route";
import { RoleRoute } from "@/routes/role-route";
import type { ReactNode } from "react";

function createWrapper(authState: { user: unknown; isLoading: boolean; isAuthenticated: boolean }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <AuthContext.Provider
          value={{
            ...authState,
            user: authState.user as ReturnType<typeof Object>,
            login: vi.fn(),
            register: vi.fn(),
            logout: vi.fn(),
          }}
        >
          {children}
        </AuthContext.Provider>
      </QueryClientProvider>
    );
  };
}

describe("ProtectedRoute", () => {

  it("redirects to /login when not authenticated", () => {
    const Wrapper = createWrapper({ user: null, isLoading: false, isAuthenticated: false });

    render(
      <Wrapper>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <Routes>
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<div>Dashboard</div>} />
            </Route>
            <Route path="/login" element={<div>Login Page</div>} />
          </Routes>
        </MemoryRouter>
      </Wrapper>
    );

    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });

  it("renders children when authenticated", () => {
    const Wrapper = createWrapper({
      user: { id: "1", name: "Test", email: "t@t.com", role: "owner" },
      isLoading: false,
      isAuthenticated: true,
    });

    render(
      <Wrapper>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <Routes>
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<div>Dashboard</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </Wrapper>
    );

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });
});

describe("RoleRoute", () => {
  it("redirects member away from admin routes", () => {
    const Wrapper = createWrapper({
      user: { id: "1", name: "Test", email: "t@t.com", role: "member" },
      isLoading: false,
      isAuthenticated: true,
    });

    render(
      <Wrapper>
        <MemoryRouter initialEntries={["/analytics"]}>
          <Routes>
            <Route element={<RoleRoute roles={["admin", "owner"]} />}>
              <Route path="/analytics" element={<div>Analytics</div>} />
            </Route>
            <Route path="/dashboard" element={<div>Dashboard Redirect</div>} />
          </Routes>
        </MemoryRouter>
      </Wrapper>
    );

    expect(screen.getByText("Dashboard Redirect")).toBeInTheDocument();
  });

  it("allows admin access to admin routes", () => {
    const Wrapper = createWrapper({
      user: { id: "1", name: "Test", email: "t@t.com", role: "admin" },
      isLoading: false,
      isAuthenticated: true,
    });

    render(
      <Wrapper>
        <MemoryRouter initialEntries={["/analytics"]}>
          <Routes>
            <Route element={<RoleRoute roles={["admin", "owner"]} />}>
              <Route path="/analytics" element={<div>Analytics</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </Wrapper>
    );

    expect(screen.getByText("Analytics")).toBeInTheDocument();
  });

  it("allows owner access to all routes", () => {
    const Wrapper = createWrapper({
      user: { id: "1", name: "Test", email: "t@t.com", role: "owner" },
      isLoading: false,
      isAuthenticated: true,
    });

    render(
      <Wrapper>
        <MemoryRouter initialEntries={["/analytics"]}>
          <Routes>
            <Route element={<RoleRoute roles={["admin", "owner"]} />}>
              <Route path="/analytics" element={<div>Analytics</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </Wrapper>
    );

    expect(screen.getByText("Analytics")).toBeInTheDocument();
  });
});
