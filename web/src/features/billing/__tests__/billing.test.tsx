import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BillingPage } from "@/features/billing/pages/billing";
import { renderWithProviders } from "@/test/test-utils";

const mockGetSubscription = vi.fn();
const mockCreateCheckout = vi.fn();
const mockCreatePortal = vi.fn();

vi.mock("@/features/billing/api", () => ({
  billingApi: {
    getSubscription: () => mockGetSubscription(),
    createCheckout: (successUrl: string, cancelUrl: string) =>
      mockCreateCheckout(successUrl, cancelUrl),
    createPortal: (returnUrl: string) => mockCreatePortal(returnUrl),
  },
}));

describe("BillingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders page header", async () => {
    mockGetSubscription.mockResolvedValue({
      data: { plan_tier: "free", inventory_item_limit: 50, team_member_limit: 2 },
    });

    renderWithProviders(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText("Billing & Subscription")).toBeInTheDocument();
    });
    expect(screen.getByText(/manage your plan and billing/i)).toBeInTheDocument();
  });

  it("renders free plan state", async () => {
    mockGetSubscription.mockResolvedValue({
      data: { plan_tier: "free", inventory_item_limit: 50, team_member_limit: 2 },
    });

    renderWithProviders(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText("Free Plan")).toBeInTheDocument();
    });
    expect(screen.getByText(/upgrade to unlock all features/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /upgrade to paid/i })).toBeInTheDocument();
  });

  it("renders paid plan state", async () => {
    mockGetSubscription.mockResolvedValue({
      data: {
        plan_tier: "paid",
        subscription_status: "active",
        inventory_item_limit: -1,
        team_member_limit: 100,
      },
    });

    renderWithProviders(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText("Paid Plan")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /manage billing/i })).toBeInTheDocument();
  });

  it("shows free plan features", async () => {
    mockGetSubscription.mockResolvedValue({
      data: { plan_tier: "free", inventory_item_limit: 50, team_member_limit: 2 },
    });

    renderWithProviders(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText("Up to 50 inventory items")).toBeInTheDocument();
    });
    expect(screen.getByText("2 team members")).toBeInTheDocument();
    expect(screen.getByText("Basic analytics")).toBeInTheDocument();
    expect(screen.getByText("CSV import")).toBeInTheDocument();
  });

  it("shows paid plan features", async () => {
    mockGetSubscription.mockResolvedValue({
      data: { plan_tier: "free", inventory_item_limit: 50, team_member_limit: 2 },
    });

    renderWithProviders(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText("Unlimited inventory items")).toBeInTheDocument();
    });
    expect(screen.getByText("Whatnot API integration")).toBeInTheDocument();
    expect(screen.getByText("Automated sync & webhooks")).toBeInTheDocument();
    expect(screen.getByText("Priority support")).toBeInTheDocument();
  });

  it("shows plan limits on free tier", async () => {
    mockGetSubscription.mockResolvedValue({
      data: { plan_tier: "free", inventory_item_limit: 50, team_member_limit: 2 },
    });

    renderWithProviders(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText("50")).toBeInTheDocument();
    });
  });

  it("shows unlimited label for paid tier", async () => {
    mockGetSubscription.mockResolvedValue({
      data: {
        plan_tier: "paid",
        subscription_status: "active",
        inventory_item_limit: -1,
        team_member_limit: 100,
      },
    });

    renderWithProviders(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText("Unlimited")).toBeInTheDocument();
    });
  });

  it("shows pricing info", async () => {
    mockGetSubscription.mockResolvedValue({
      data: { plan_tier: "free", inventory_item_limit: 50, team_member_limit: 2 },
    });

    renderWithProviders(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText("$0")).toBeInTheDocument();
    });
    expect(screen.getByText("$29")).toBeInTheDocument();
  });

  it("clicks upgrade button", async () => {
    const user = userEvent.setup();
    mockGetSubscription.mockResolvedValue({
      data: { plan_tier: "free", inventory_item_limit: 50, team_member_limit: 2 },
    });
    mockCreateCheckout.mockResolvedValue({ data: { url: "https://checkout.stripe.com/xxx" } });

    renderWithProviders(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /upgrade to paid/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /upgrade to paid/i }));

    await waitFor(() => {
      expect(mockCreateCheckout).toHaveBeenCalled();
    });
  });

  it("shows current plan badge on free plan card", async () => {
    mockGetSubscription.mockResolvedValue({
      data: { plan_tier: "free", inventory_item_limit: 50, team_member_limit: 2 },
    });

    renderWithProviders(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText("Current Plan")).toBeInTheDocument();
    });
  });
});
