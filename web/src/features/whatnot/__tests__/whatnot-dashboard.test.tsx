import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WhatnotDashboardPage } from "@/features/whatnot/pages/whatnot-dashboard";
import { renderWithProviders } from "@/test/test-utils";

const mockStatus = vi.fn();
const mockSyncStatus = vi.fn();
const mockConnect = vi.fn();
const mockDisconnect = vi.fn();
const mockFullSync = vi.fn();
const mockPullProducts = vi.fn();
const mockSyncOrders = vi.fn();
const mockSyncLivestreams = vi.fn();

vi.mock("@/features/whatnot/api", () => ({
  whatnotApi: {
    status: () => mockStatus(),
    syncStatus: () => mockSyncStatus(),
    connect: () => mockConnect(),
    disconnect: () => mockDisconnect(),
    fullSync: () => mockFullSync(),
    pullProducts: () => mockPullProducts(),
    syncOrders: () => mockSyncOrders(),
    syncLivestreams: () => mockSyncLivestreams(),
  },
}));

describe("WhatnotDashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSyncStatus.mockResolvedValue({ data: { recent: [] } });
  });

  it("renders not-connected state", async () => {
    mockStatus.mockResolvedValue({ data: { connected: false } });

    renderWithProviders(<WhatnotDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Connection Status")).toBeInTheDocument();
    });
    expect(screen.getByText(/connect your whatnot seller account/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /connect whatnot account/i })).toBeInTheDocument();
  });

  it("renders connected state with username", async () => {
    mockStatus.mockResolvedValue({
      data: { connected: true, whatnot_username: "seller123", scopes: "full_access" },
    });

    renderWithProviders(<WhatnotDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/connected as @seller123/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /disconnect/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /full sync/i })).toBeInTheDocument();
  });

  it("shows sync action cards when connected", async () => {
    mockStatus.mockResolvedValue({
      data: { connected: true, whatnot_username: "seller123" },
    });

    renderWithProviders(<WhatnotDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Products")).toBeInTheDocument();
    });
    expect(screen.getByText("Orders")).toBeInTheDocument();
    expect(screen.getByText("Livestreams")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sync products/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sync orders/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sync livestreams/i })).toBeInTheDocument();
  });

  it("calls disconnect when button clicked", async () => {
    const user = userEvent.setup();
    mockStatus.mockResolvedValue({
      data: { connected: true, whatnot_username: "seller123" },
    });
    mockDisconnect.mockResolvedValue({});

    renderWithProviders(<WhatnotDashboardPage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /disconnect/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /disconnect/i }));

    await waitFor(() => {
      expect(mockDisconnect).toHaveBeenCalled();
    });
  });

  it("calls pullProducts when sync products clicked", async () => {
    const user = userEvent.setup();
    mockStatus.mockResolvedValue({
      data: { connected: true, whatnot_username: "seller123" },
    });
    mockPullProducts.mockResolvedValue({ data: { created: 5, updated: 2 } });

    renderWithProviders(<WhatnotDashboardPage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /sync products/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /sync products/i }));

    await waitFor(() => {
      expect(mockPullProducts).toHaveBeenCalled();
    });
  });

  it("renders page header", async () => {
    mockStatus.mockResolvedValue({ data: { connected: false } });

    renderWithProviders(<WhatnotDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Whatnot Integration")).toBeInTheDocument();
    });
    expect(screen.getByText(/connect and sync your whatnot seller account/i)).toBeInTheDocument();
  });

  it("shows sync history section when connected", async () => {
    mockStatus.mockResolvedValue({
      data: { connected: true, whatnot_username: "seller123" },
    });
    mockSyncStatus.mockResolvedValue({
      data: {
        recent: [
          { sync_type: "products", status: "completed", started_at: "2025-01-01T00:00:00Z" },
        ],
      },
    });

    renderWithProviders(<WhatnotDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Sync History")).toBeInTheDocument();
    });
  });
});
