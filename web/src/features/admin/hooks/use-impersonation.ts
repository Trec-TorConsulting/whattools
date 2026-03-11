import { useCallback } from "react";
import { useNavigate } from "react-router";
import { setTokens, getAccessToken, clearTokens } from "@/lib/api-client";
import type { AdminUser } from "./use-admin-api";

const IMPERSONATION_KEY = "whattools_impersonation";
const ADMIN_TOKEN_KEY = "whattools_admin_token";

export type ImpersonationState = {
  isImpersonating: boolean;
  impersonatedUser: AdminUser | null;
};

export function getImpersonationState(): ImpersonationState {
  const stored = localStorage.getItem(IMPERSONATION_KEY);
  if (!stored) return { isImpersonating: false, impersonatedUser: null };
  try {
    return JSON.parse(stored);
  } catch {
    return { isImpersonating: false, impersonatedUser: null };
  }
}

export function useImpersonation() {
  const navigate = useNavigate();

  const startImpersonation = useCallback(
    (accessToken: string, user: AdminUser) => {
      // Save admin's current token so we can restore it
      const adminToken = getAccessToken();
      if (adminToken) {
        localStorage.setItem(ADMIN_TOKEN_KEY, adminToken);
      }

      // Set the impersonation token as the active token
      // We only set the access token (no refresh) since impersonation sessions are time-limited
      localStorage.setItem("whattools_access_token", accessToken);

      // Store impersonation state
      localStorage.setItem(
        IMPERSONATION_KEY,
        JSON.stringify({ isImpersonating: true, impersonatedUser: user })
      );

      // Navigate to the main app (user's view)
      window.location.href = "/dashboard";
    },
    []
  );

  const stopImpersonation = useCallback(() => {
    // Restore admin token
    const adminToken = localStorage.getItem(ADMIN_TOKEN_KEY);
    if (adminToken) {
      localStorage.setItem("whattools_access_token", adminToken);
      localStorage.removeItem(ADMIN_TOKEN_KEY);
    }

    // Clear impersonation state
    localStorage.removeItem(IMPERSONATION_KEY);

    // Navigate back to admin portal
    window.location.href = "/admin";
  }, []);

  return {
    ...getImpersonationState(),
    startImpersonation,
    stopImpersonation,
  };
}
