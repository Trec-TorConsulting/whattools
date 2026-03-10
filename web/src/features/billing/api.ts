import { api } from "@/lib/api-client";
import type { SubscriptionStatus } from "@/lib/schemas";

export const billingApi = {
  getSubscription: () => api.get<SubscriptionStatus>("/api/v1/billing/subscription"),

  createCheckout: (successUrl: string, cancelUrl: string) =>
    api.post<{ url: string }>("/api/v1/billing/checkout", {
      success_url: successUrl,
      cancel_url: cancelUrl,
    }),

  createPortal: (returnUrl: string) =>
    api.post<{ url: string }>("/api/v1/billing/portal", { return_url: returnUrl }),
};
