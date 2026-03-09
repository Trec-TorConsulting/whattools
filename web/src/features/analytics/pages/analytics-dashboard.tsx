import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { DollarSign, TrendingUp, ShoppingCart, Tv } from "lucide-react";
import { queryKeys } from "@/lib/query-keys";
import { analyticsApi } from "@/features/analytics/api";
import { formatCurrency } from "@/lib/utils";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { PageSkeleton } from "@/components/loading-skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const CHART_COLORS = [
  "hsl(222, 80%, 55%)",
  "hsl(160, 60%, 45%)",
  "hsl(38, 92%, 50%)",
  "hsl(0, 72%, 51%)",
  "hsl(280, 65%, 60%)",
  "hsl(190, 80%, 42%)",
];

export function AnalyticsDashboardPage() {
  const [period, setPeriod] = useState("30d");

  const { data: summaryData, isLoading: loadingSummary } = useQuery({
    queryKey: queryKeys.analytics.summary(period),
    queryFn: () => analyticsApi.getSummary(period),
  });

  const { data: trendsData } = useQuery({
    queryKey: queryKeys.analytics.trends(period),
    queryFn: () => analyticsApi.getTrends(period),
  });

  const { data: categoriesData } = useQuery({
    queryKey: queryKeys.analytics.categories(period),
    queryFn: () => analyticsApi.getCategories(period),
  });

  const { data: topItemsData } = useQuery({
    queryKey: queryKeys.analytics.topItems(period, "revenue"),
    queryFn: () => analyticsApi.getTopItems(period, "revenue"),
  });

  if (loadingSummary) return <PageSkeleton />;

  const stats = summaryData?.data;
  const trends = trendsData?.data ?? [];
  const categories = categoriesData?.data ?? [];
  const topItems = topItemsData?.data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics"
        description="Business performance insights"
        actions={
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
              <SelectItem value="365d">Last year</SelectItem>
            </SelectContent>
          </Select>
        }
      />

      {/* KPI Cards */}
      {stats && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard title="Revenue" value={formatCurrency(stats.total_revenue)} icon={DollarSign} />
          <StatCard
            title="Profit"
            value={formatCurrency(stats.total_profit)}
            icon={TrendingUp}
            trend={{ value: Math.round(stats.profit_margin), label: "margin" }}
          />
          <StatCard title="Orders" value={String(stats.total_orders)} icon={ShoppingCart} />
          <StatCard title="Shows" value={String(stats.total_shows)} icon={Tv} />
        </div>
      )}

      {/* Charts */}
      <Tabs defaultValue="revenue">
        <TabsList>
          <TabsTrigger value="revenue">Revenue &amp; Profit</TabsTrigger>
          <TabsTrigger value="categories">Categories</TabsTrigger>
          <TabsTrigger value="top-items">Top Items</TabsTrigger>
        </TabsList>

        {/* Revenue Trends */}
        <TabsContent value="revenue">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Revenue &amp; Profit Trends</CardTitle>
            </CardHeader>
            <CardContent>
              {trends.length > 0 ? (
                <ResponsiveContainer width="100%" height={350}>
                  <LineChart data={trends}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="date"
                      className="text-xs"
                      tick={{ fontSize: 12 }}
                      tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                    />
                    <YAxis className="text-xs" tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                    <Tooltip
                      formatter={(value: number, name: string) => [formatCurrency(value), name]}
                      labelFormatter={(v) => new Date(v).toLocaleDateString()}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="revenue"
                      name="Revenue"
                      stroke={CHART_COLORS[0]}
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="profit"
                      name="Profit"
                      stroke={CHART_COLORS[1]}
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-16 text-center text-sm text-muted-foreground">
                  Not enough data to display trends
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Categories */}
        <TabsContent value="categories">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Revenue by Category</CardTitle>
              </CardHeader>
              <CardContent>
                {categories.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={categories}
                        dataKey="revenue"
                        nameKey="category_name"
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                      >
                        {categories.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="py-16 text-center text-sm text-muted-foreground">No category data</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Category Performance</CardTitle>
              </CardHeader>
              <CardContent>
                {categories.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={categories} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis type="number" tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                      <YAxis
                        type="category"
                        dataKey="category_name"
                        width={100}
                        tick={{ fontSize: 12 }}
                      />
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      <Bar dataKey="revenue" name="Revenue" fill={CHART_COLORS[0]} radius={[0, 4, 4, 0]} />
                      <Bar dataKey="profit" name="Profit" fill={CHART_COLORS[1]} radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="py-16 text-center text-sm text-muted-foreground">No category data</p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Top Items */}
        <TabsContent value="top-items">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Top Selling Items</CardTitle>
            </CardHeader>
            <CardContent>
              {topItems.length > 0 ? (
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={topItems.slice(0, 10)}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="item_name"
                      tick={{ fontSize: 11 }}
                      interval={0}
                      angle={-20}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
                    <Legend />
                    <Bar dataKey="revenue" name="Revenue" fill={CHART_COLORS[0]} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="profit" name="Profit" fill={CHART_COLORS[1]} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-16 text-center text-sm text-muted-foreground">No sales data yet</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
