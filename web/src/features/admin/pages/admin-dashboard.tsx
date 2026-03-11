import { Building2, Users, DollarSign, TrendingUp, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAdminMetrics } from "../hooks/use-admin-api";
import { Skeleton } from "@/components/ui/skeleton";

export function AdminDashboardPage() {
  const { data: metrics, isLoading } = useAdminMetrics();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Platform Dashboard</h1>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!metrics) return null;

  const stats = [
    {
      title: "Total Accounts",
      value: metrics.total_accounts,
      icon: Building2,
      color: "text-blue-500",
    },
    {
      title: "Active Accounts",
      value: metrics.active_accounts,
      icon: Building2,
      color: "text-green-500",
    },
    {
      title: "Suspended",
      value: metrics.suspended_accounts,
      icon: AlertTriangle,
      color: "text-red-500",
    },
    {
      title: "Total Users",
      value: metrics.total_users,
      icon: Users,
      color: "text-purple-500",
    },
    {
      title: "Active Users",
      value: metrics.active_users,
      icon: Users,
      color: "text-green-500",
    },
    {
      title: "Free Accounts",
      value: metrics.free_accounts,
      icon: Building2,
      color: "text-gray-500",
    },
    {
      title: "Paid Accounts",
      value: metrics.paid_accounts,
      icon: DollarSign,
      color: "text-emerald-500",
    },
    {
      title: "MRR",
      value: `$${metrics.mrr.toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
      icon: TrendingUp,
      color: "text-emerald-500",
    },
    {
      title: "Signups (30d)",
      value: metrics.recent_signups,
      icon: TrendingUp,
      color: "text-blue-500",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Platform Dashboard</h1>
        <p className="text-muted-foreground">Overview of your WhatTools platform</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{stat.title}</CardTitle>
              <stat.icon className={cn("h-4 w-4", stat.color)} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Pricing</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border p-4">
              <h3 className="font-semibold">Free Plan</h3>
              <p className="text-2xl font-bold">$0<span className="text-sm font-normal text-muted-foreground">/mo</span></p>
              <p className="text-sm text-muted-foreground">2 team members, 50 items</p>
            </div>
            <div className="rounded-lg border border-emerald-500/50 bg-emerald-500/5 p-4">
              <h3 className="font-semibold">Paid Plan</h3>
              <p className="text-2xl font-bold">$29.99<span className="text-sm font-normal text-muted-foreground">/mo</span></p>
              <p className="text-sm text-muted-foreground">
                100 team members, unlimited items
                <br />
                Annual: $299.90/yr (2 months free)
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}
