const TOKEN_KEY = "whattools_access_token";
const REFRESH_KEY = "whattools_refresh_token";

type ApiError = {
  code: string;
  message: string;
  field?: string;
};

export class ApiClientError extends Error {
  constructor(
    public status: number,
    public errors: ApiError[],
    public requestId?: string
  ) {
    super(errors[0]?.message ?? `Request failed with status ${status}`);
    this.name = "ApiClientError";
  }
}

let refreshPromise: Promise<string> | null = null;
let onSessionExpired: (() => void) | null = null;

export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler;
}

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

async function refreshAccessToken(): Promise<string> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error("No refresh token");
  }

  const response = await fetch("/api/v1/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    clearTokens();
    onSessionExpired?.();
    throw new Error("Session expired");
  }

  const body = await response.json();
  const { access_token, refresh_token } = body.data;
  setTokens(access_token, refresh_token);
  return access_token;
}

async function refreshWithMutex(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = refreshAccessToken().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<{ data: T; meta: Record<string, unknown> }> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response = await fetch(path, { ...options, headers });

  // Attempt token refresh on 401
  if (response.status === 401 && token) {
    try {
      const newToken = await refreshWithMutex();
      headers["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(path, { ...options, headers });
    } catch {
      throw new ApiClientError(401, [{ code: "session_expired", message: "Your session has expired. Please log in again." }]);
    }
  }

  const body = await response.json();

  if (!response.ok) {
    throw new ApiClientError(
      response.status,
      body.errors ?? [{ code: "unknown", message: body.message ?? "An error occurred" }],
      body.meta?.request_id
    );
  }

  return { data: body.data, meta: body.meta ?? {} };
}

// Convenience methods
export const api = {
  get: <T = unknown>(path: string) => apiRequest<T>(path),

  post: <T = unknown>(path: string, data?: unknown) =>
    apiRequest<T>(path, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T = unknown>(path: string, data?: unknown) =>
    apiRequest<T>(path, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T = unknown>(path: string) =>
    apiRequest<T>(path, { method: "DELETE" }),

  upload: <T = unknown>(path: string, formData: FormData) => {
    const token = getAccessToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    // Don't set Content-Type — browser handles multipart boundary
    return apiRequest<T>(path, {
      method: "POST",
      headers,
      body: formData,
    });
  },

  download: async (path: string): Promise<Blob> => {
    const token = getAccessToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(path, { headers });
    if (!response.ok) {
      throw new ApiClientError(response.status, [
        { code: "download_failed", message: "Download failed" },
      ]);
    }
    return response.blob();
  },
};
