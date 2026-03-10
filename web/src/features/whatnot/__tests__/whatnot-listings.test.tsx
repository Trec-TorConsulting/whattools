import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WhatnotListingsPage } from "@/features/whatnot/pages/whatnot-listings";
import { renderWithProviders } from "@/test/test-utils";

const mockListListings = vi.fn();
const mockPublishListing = vi.fn();
const mockUnpublishListing = vi.fn();
const mockDeleteListing = vi.fn();

vi.mock("@/features/whatnot/api", () => ({
  whatnotApi: {
    listListings: (...args: unknown[]) => mockListListings(...args),
    publishListing: (id: string) => mockPublishListing(id),
    unpublishListing: (id: string) => mockUnpublishListing(id),
    deleteListing: (id: string) => mockDeleteListing(id),
  },
}));

const sampleListings = [
  { id: "lst-1", title: "Vintage Watch", status: "published", price: 4999 },
  { id: "lst-2", title: "Limited Sneakers", status: "draft", price: 12000 },
  { id: "lst-3", title: "Rare Card", status: "unpublished", price: null },
];

describe("WhatnotListingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders page header", async () => {
    mockListListings.mockResolvedValue({ data: [], meta: {} });

    renderWithProviders(<WhatnotListingsPage />);

    await waitFor(() => {
      expect(screen.getByText("Whatnot Listings")).toBeInTheDocument();
    });
    expect(screen.getByText(/manage your listings on whatnot/i)).toBeInTheDocument();
  });

  it("renders listings in table", async () => {
    mockListListings.mockResolvedValue({
      data: sampleListings,
      meta: { has_more: false },
    });

    renderWithProviders(<WhatnotListingsPage />);

    await waitFor(() => {
      expect(screen.getByText("Vintage Watch")).toBeInTheDocument();
    });
    expect(screen.getByText("Limited Sneakers")).toBeInTheDocument();
    expect(screen.getByText("Rare Card")).toBeInTheDocument();
  });

  it("displays prices formatted as dollars", async () => {
    mockListListings.mockResolvedValue({
      data: sampleListings,
      meta: { has_more: false },
    });

    renderWithProviders(<WhatnotListingsPage />);

    await waitFor(() => {
      expect(screen.getByText("$49.99")).toBeInTheDocument();
    });
    expect(screen.getByText("$120.00")).toBeInTheDocument();
  });

  it("shows status badges", async () => {
    mockListListings.mockResolvedValue({
      data: sampleListings,
      meta: { has_more: false },
    });

    renderWithProviders(<WhatnotListingsPage />);

    await waitFor(() => {
      expect(screen.getByText("published")).toBeInTheDocument();
    });
    expect(screen.getByText("draft")).toBeInTheDocument();
    expect(screen.getByText("unpublished")).toBeInTheDocument();
  });

  it("opens actions dropdown menu", async () => {
    const user = userEvent.setup();
    mockListListings.mockResolvedValue({
      data: [sampleListings[0]],
      meta: { has_more: false },
    });

    renderWithProviders(<WhatnotListingsPage />);

    await waitFor(() => {
      expect(screen.getByText("Vintage Watch")).toBeInTheDocument();
    });

    const menuButton = screen.getByRole("button", { name: "" });
    await user.click(menuButton);

    await waitFor(() => {
      expect(screen.getByText("Publish")).toBeInTheDocument();
      expect(screen.getByText("Unpublish")).toBeInTheDocument();
      expect(screen.getByText("Delete")).toBeInTheDocument();
    });
  });

  it("renders empty table when no listings", async () => {
    mockListListings.mockResolvedValue({ data: [], meta: {} });

    renderWithProviders(<WhatnotListingsPage />);

    await waitFor(() => {
      expect(screen.getByText("Whatnot Listings")).toBeInTheDocument();
    });
  });
});
