import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { WhatnotCallbackPage } from "@/features/whatnot/pages/whatnot-callback";
import { renderWithProviders } from "@/test/test-utils";

const mockNavigate = vi.fn();

vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockGet = vi.fn();

vi.mock("@/lib/api-client", async () => {
  const actual = await vi.importActual("@/lib/api-client");
  return {
    ...actual,
    api: {
      ...(actual as Record<string, unknown>).api,
      get: (...args: unknown[]) => mockGet(...args),
    },
  };
});

describe("WhatnotCallbackPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially with valid params", () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    window.history.pushState({}, "", "?code=abc123&state=xyz");
    renderWithProviders(<WhatnotCallbackPage />);

    expect(screen.getByText("Connecting Whatnot...")).toBeInTheDocument();
    expect(screen.getByText(/please wait/i)).toBeInTheDocument();
  });

  it("shows error when access_denied", async () => {
    window.history.pushState({}, "", "?error=access_denied");
    renderWithProviders(<WhatnotCallbackPage />);

    await waitFor(() => {
      expect(screen.getByText("Connection Failed")).toBeInTheDocument();
    });
    expect(screen.getByText(/denied access/i)).toBeInTheDocument();
  });

  it("shows error when code is missing", async () => {
    window.history.pushState({}, "", "?state=xyz");
    renderWithProviders(<WhatnotCallbackPage />);

    await waitFor(() => {
      expect(screen.getByText("Connection Failed")).toBeInTheDocument();
    });
    expect(screen.getByText(/missing authorization code/i)).toBeInTheDocument();
  });

  it("shows success after successful callback", async () => {
    mockGet.mockResolvedValue({ data: {} });
    window.history.pushState({}, "", "?code=abc123&state=xyz");
    renderWithProviders(<WhatnotCallbackPage />);

    await waitFor(() => {
      expect(screen.getByText("Connected!")).toBeInTheDocument();
    });
    expect(screen.getByText(/connected successfully/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /go to whatnot dashboard/i })).toBeInTheDocument();
  });

  it("shows error when API call fails", async () => {
    mockGet.mockRejectedValue(new Error("Server error"));
    window.history.pushState({}, "", "?code=abc123&state=xyz");
    renderWithProviders(<WhatnotCallbackPage />);

    await waitFor(() => {
      expect(screen.getByText("Connection Failed")).toBeInTheDocument();
    });
  });
});
