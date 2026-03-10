import { useQuery, useMutation } from "@tanstack/react-query";
import { CreditCard, Crown, Check, ArrowUpRight } from "lucide-react";
import { toast } from "sonner";

import { queryKeys } from "@/lib/query-keys";
import { billingApi } from "@/features/billing/api";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageSkeleton } from "@/components/loading-skeleton";

const FREE_FEATURES = [
  "Up to 50 inventory items",
  "2 team members",
  "Basic analytics",
  "CSV import",
];

const PAID_FEATURES = [
  "Unlimited inventory items",
  "Up to 100 team members",
  "Advanced analytics & exports",
  "Whatnot API integration",
  "Automated sync & webhooks",
  "Priority support",
];

export function BillingPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.billing.subscription,
    queryFn: () => billingApi.getSubscription(),
  });

  const checkoutMutation = useMutation({
    mutationFn: () =>
      billingApi.createCheckout(
        `${window.location.origin}/settings/account?billing=success`,
        `${window.location.origin}/settings/account?billing=cancelled`
      ),
    onSuccess: ({ data }) => {
      window.location.href = data.url;
    },
    onError: () => toast.error("Failed to start checkout"),
  });

  const portalMutation = useMutation({
    mutationFn: () => billingApi.createPortal(`${window.location.origin}/settings/account`),
    onSuccess: ({ data }) => {
      window.location.href = data.url;
    },
    onError: () => toast.error("Failed to open billing portal"),
  });

  if (isLoading) return <PageSkeleton />;

  const subscription = data?.data;
  const isPaid = subscription?.plan_tier === "paid";

  return (
    <div className="space-y-6">
      <PageHeader title="Billing & Subscription" description="Manage your plan and billing" />

      {/* Current plan */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                {isPaid && <Crown className="h-5 w-5 text-yellow-500" />}
                {isPaid ? "Paid Plan" : "Free Plan"}
              </CardTitle>
              <CardDescription>
                {isPaid
                  ? `Status: ${subscription?.subscription_status || "active"}`
                  : "Upgrade to unlock all features"}
              </CardDescription>
            </div>
            {isPaid && (
              <Badge variant="success">Active</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 text-sm">
            <p>
              <span className="text-muted-foreground">Inventory limit:</span>{" "}
              {subscription?.inventory_item_limit === -1 ? "Unlimited" : subscription?.inventory_item_limit}
            </p>
            <p>
              <span className="text-muted-foreground">Team members:</span> {subscription?.team_member_limit}
            </p>
          </div>
        </CardContent>
        {isPaid && (
          <CardFooter>
            <Button variant="outline" onClick={() => portalMutation.mutate()} disabled={portalMutation.isPending}>
              <CreditCard className="mr-2 h-4 w-4" />
              Manage Billing
              <ArrowUpRight className="ml-2 h-4 w-4" />
            </Button>
          </CardFooter>
        )}
      </Card>

      {/* Plan comparison */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card className={!isPaid ? "border-primary" : undefined}>
          <CardHeader>
            <CardTitle>Free</CardTitle>
            <CardDescription>For individuals getting started</CardDescription>
            <p className="text-3xl font-bold">$0<span className="text-base font-normal text-muted-foreground">/mo</span></p>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {FREE_FEATURES.map((feature) => (
                <li key={feature} className="flex items-center gap-2 text-sm">
                  <Check className="h-4 w-4 text-green-500" />
                  {feature}
                </li>
              ))}
            </ul>
          </CardContent>
          <CardFooter>
            {!isPaid ? (
              <Badge variant="secondary">Current Plan</Badge>
            ) : (
              <span className="text-sm text-muted-foreground">Downgrade via billing portal</span>
            )}
          </CardFooter>
        </Card>

        <Card className={isPaid ? "border-primary" : undefined}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Crown className="h-5 w-5 text-yellow-500" />
              Paid
            </CardTitle>
            <CardDescription>For professional sellers</CardDescription>
            <p className="text-3xl font-bold">$29<span className="text-base font-normal text-muted-foreground">/mo</span></p>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {PAID_FEATURES.map((feature) => (
                <li key={feature} className="flex items-center gap-2 text-sm">
                  <Check className="h-4 w-4 text-green-500" />
                  {feature}
                </li>
              ))}
            </ul>
          </CardContent>
          <CardFooter>
            {isPaid ? (
              <Badge variant="success">Current Plan</Badge>
            ) : (
              <Button onClick={() => checkoutMutation.mutate()} disabled={checkoutMutation.isPending}>
                Upgrade to Paid
              </Button>
            )}
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
