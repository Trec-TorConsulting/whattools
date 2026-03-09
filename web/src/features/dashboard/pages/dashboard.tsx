import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import {
  DollarSign,
  ShoppingCart,
  Tv,
  Truck,
  TrendingUp,
  ArrowRight,
  Calendar,
} from "lucide-react";
import { queryKeys } from "@/lib/query-keys";
import { useAuth } from "@/hooks/use-auth";
import { canAccessSales, canAccessAnalytics } from "@/lib/role-utils";
import { formatCurrency, formatRelative } from "@/lib/utils";
import { dashboardApi } from "@/features/dashboard/api";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import { PageSkeleton } from "@/components/loading-skeleton";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function DashboardPage() {
  const { user } = useAuth();
  const isAdmin = user ? canAccessSales(user.role) : false;
  const hasAnalytics = user ? canAccessAnalytics(user.role) : false;

  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: queryKeys.analytics.summary("30d"),
    queryFn: () => dashboardApi.getSummary(),
    enabled: hasAnalytics,
  });

  const { data: recentItems, isLoading: loadingItems } = useQuery({
    queryKey: [...queryKeys.items.all, "recent"],
    queryFn: () => dashboardApi.getRecentItems(),
  });

  const { data: upcomingShows, isLoading: loadingShows } = useQuery({
    queryKey: [...queryKeys.shows.all, "upcoming"],
    queryFn: () => dashboardApi.getUpcomingShows(),
    enabled: isAdmin,
  });

  const { data: recentOrders, isLoading: loadingOrders } = useQuery({
    queryKey: [...queryKeys.orders.all, "recent"],
    queryFn: () => dashboardApi.getRecentOrders(),
    enabled: isAdmin,
  });

  const { data: pendingShipments, isLoading: loadingShipments } = useQuery({
    queryKey: [...queryKeys.shipments.all, "pending"],
    queryFn: () => dashboardApi.getPendingShipments(),
    enabled: isAdmin,
  });

  if (loadingSummary && hasAnalytics) return <PageSkeleton />;

  const stats = summary?.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome back, ${user?.name?.split(" ")[0] ?? "there"}`}
        description="Here's what's happening with your business today"
      />

      {/* Stats Grid */}
      {hasAnalytics && stats && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Total Revenue"
            value={formatCurrency(stats.total_revenue)}
            icon={DollarSign}
            description="Last 30 days"
          />
          <StatCard
            title="Total Profit"
            value={formatCurrency(stats.total_profit)}
            icon={TrendingUp}
            trend={stats.profit_margin ? { value: stats.profit_margin, label: "profit margin" } : undefined}
          />
          <StatCard
            title="Total Orders"
            value={String(stats.total_orders)}
            icon={ShoppingCart}
            description="Last 30 days"
          />
          <StatCard
            title="Total Shows"
            value={String(stats.total_shows)}
            icon={Tv}
            description="Last 30 days"
          />
        </div>
      )}

      {/* Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Inventory */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base">Recent Inventory</CardTitle>
              <CardDescription>Latest items added</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/inventory">
                View all <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {loadingItems ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-10 animate-pulse rounded bg-muted" />
                ))}
              </div>
            ) : recentItems?.data && recentItems.data.length > 0 ? (
              <div className="space-y-3">
                {recentItems.data.map((item) => (
                  <div key={item.id} className="flex items-center justify-between rounded-lg border p-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{item.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {item.sku ? `SKU: ${item.sku} · ` : ""}
                        Qty: {item.quantity}
                      </p>
                    </div>
                    <div className="ml-3 flex items-center gap-2">
                      <span className="text-sm font-medium">{formatCurrency(Number(item.cogs))}</span>
                      <StatusBadge status={item.status} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">No items yet</p>
            )}
          </CardContent>
        </Card>

        {/* Upcoming Shows */}
        {isAdmin && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base">Upcoming Shows</CardTitle>
                <CardDescription>Planned live shows</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/shows">
                  View all <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </CardHeader>
            <CardContent>
              {loadingShows ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="h-10 animate-pulse rounded bg-muted" />
                  ))}
                </div>
              ) : upcomingShows?.data && upcomingShows.data.length > 0 ? (
                <div className="space-y-3">
                  {upcomingShows.data.map((show) => (
                    <Link
                      key={show.id}
                      to={`/shows/${show.id}`}
                      className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{show.title}</p>
                        {show.scheduled_at && (
                          <p className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Calendar className="h-3 w-3" />
                            {formatRelative(show.scheduled_at)}
                          </p>
                        )}
                      </div>
                      <StatusBadge status={show.status} />
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">No upcoming shows</p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Recent Orders */}
        {isAdmin && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base">Recent Orders</CardTitle>
                <CardDescription>Latest sales orders</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/orders">
                  View all <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </CardHeader>
            <CardContent>
              {loadingOrders ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="h-10 animate-pulse rounded bg-muted" />
                  ))}
                </div>
              ) : recentOrders?.data && recentOrders.data.length > 0 ? (
                <div className="space-y-3">
                  {recentOrders.data.map((order) => (
                    <Link
                      key={order.id}
                      to={`/orders/${order.id}`}
                      className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{order.item_name}</p>
                        <p className="text-xs text-muted-foreground">
                          @{order.buyer_username} · {formatRelative(order.created_at)}
                        </p>
                      </div>
                      <div className="ml-3 flex items-center gap-2">
                        <span className="text-sm font-medium">{formatCurrency(Number(order.sale_price))}</span>
                        <StatusBadge status={order.status} />
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">No orders yet</p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Pending Shipments */}
        {isAdmin && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base">Pending Shipments</CardTitle>
                <CardDescription>Orders awaiting fulfillment</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/shipments">
                  View all <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </CardHeader>
            <CardContent>
              {loadingShipments ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="h-10 animate-pulse rounded bg-muted" />
                  ))}
                </div>
              ) : pendingShipments?.data && pendingShipments.data.length > 0 ? (
                <div className="space-y-3">
                  {pendingShipments.data.map((shipment) => (
                    <Link
                      key={shipment.id}
                      to={`/shipments/${shipment.id}`}
                      className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">@{shipment.buyer_username}</p>
                        <p className="text-xs text-muted-foreground">
                          {shipment.carrier ?? "No carrier"} · {shipment.city ?? ""}
                        </p>
                      </div>
                      <div className="ml-3 flex items-center gap-2">
                        {shipment.ship_by_date && (
                          <Badge variant="outline" className="text-xs">
                            <Truck className="mr-1 h-3 w-3" />
                            Ship by {new Date(shipment.ship_by_date).toLocaleDateString()}
                          </Badge>
                        )}
                        <StatusBadge status={shipment.status} />
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">No pending shipments</p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
