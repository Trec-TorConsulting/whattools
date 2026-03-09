import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, setTokens, clearTokens, getAccessToken, setSessionExpiredHandler } from "./api-client";
import type { User } from "./schemas";

type AuthState = {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
};

type AuthContextType = AuthState & {
  login: (email: string, password: string) => Promise<void>;
  register: (data: { name: string; email: string; password: string; account_name: string }) => Promise<void>;
  logout: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  // Register session-expired handler
  useEffect(() => {
    setSessionExpiredHandler(() => {
      setState({ user: null, isLoading: false, isAuthenticated: false });
    });
  }, []);

  // Check for existing token on mount
  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setState({ user: null, isLoading: false, isAuthenticated: false });
      return;
    }

    api
      .get<User>("/api/v1/users/me")
      .then(({ data }) => {
        setState({ user: data, isLoading: false, isAuthenticated: true });
      })
      .catch(() => {
        clearTokens();
        setState({ user: null, isLoading: false, isAuthenticated: false });
      });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await api.post<{ access_token: string; refresh_token: string; user: User }>(
      "/api/v1/auth/login",
      { email, password }
    );
    setTokens(data.access_token, data.refresh_token);
    setState({ user: data.user, isLoading: false, isAuthenticated: true });
  }, []);

  const register = useCallback(
    async (data: { name: string; email: string; password: string; account_name: string }) => {
      await api.post("/api/v1/auth/register", data);
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/api/v1/auth/logout");
    } catch {
      // Proceed with client-side logout even if server call fails
    }
    clearTokens();
    setState({ user: null, isLoading: false, isAuthenticated: false });
  }, []);

  const value = useMemo(
    () => ({ ...state, login, register, logout }),
    [state, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
