import { useParams, Link } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Play, CheckCircle, XCircle, ExternalLink } from "lucide-react";
import { queryKeys } from "@/lib/query-keys";
import { salesApi } from "@/features/sales/api";
import { formatDateTime, formatCurrency } from "@/lib/utils";
import type { Order } from "@/lib/schemas";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { PageSkeleton } from "@/components/loading-skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/data-table";

export function ShowDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.shows.detail(id!),
    queryFn: () => salesApi.getShow(id!),
    enabled: !!id,
  });

  const { data: ordersData, isLoading: loadingOrders } = useQuery({
    queryKey: queryKeys.shows.orders(id!),
    queryFn: () => salesApi.listOrders({ show_id: id!, limit: 100 }),
    enabled: !!id,
  });

  const lifecycleMutation = useMutation({
    mutationFn: (action: "start" | "complete" | "cancel") => {
      if (action === "start") return salesApi.startShow(id!);
      if (action === "complete") return salesApi.completeShow(id!);
      return salesApi.cancelShow(id!);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.shows.detail(id!) });
      toast.success("Show updated");
    },
  });

  if (isLoading) return <PageSkeleton />;
  if (!data?.data) return <div>Show not found</div>;

  const show = data.data;
  const ordersPayload = ordersData?.data as Record<string, unknown> | undefined;
  const orders: Order[] = (ordersPayload?.items as Order[]) ?? [];
  const totalRevenue = orders.reduce((sum, o) => sum + Number(o.sale_price) * o.quantity, 0);
  const totalProfit = orders.reduce((sum, o) => sum + Number(o.profit), 0);

  const orderColumns: ColumnDef<Order, unknown>[] = [
    {
      accessorKey: "buyer_username",
      header: "Buyer",
      cell: ({ row }) => <span className="font-medium">@{row.original.buyer_username}</span>,
    },
    { accessorKey: "item_name", header: "Item" },
    { accessorKey: "quantity", header: "Qty" },
    {
      accessorKey: "sale_price",
      header: "Price",
      cell: ({ row }) => formatCurrency(Number(row.original.sale_price)),
    },
    {
      accessorKey: "profit",
      header: "Profit",
      cell: ({ row }) => (
        <span className={Number(row.original.profit) >= 0 ? "text-green-600" : "text-red-600"}>
          {formatCurrency(Number(row.original.profit))}
        </span>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/shows"><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <PageHeader
          title={show.title}
          description={show.scheduled_at ? `Scheduled: ${formatDateTime(show.scheduled_at)}` : undefined}
          actions={
            <div className="flex items-center gap-2">
              <StatusBadge status={show.status} />
              {show.status === "planned" && (
                <Button size="sm" onClick={() => lifecycleMutation.mutate("start")}>
                  <Play className="mr-1 h-4 w-4" /> Go Live
                </Button>
              )}
              {show.status === "live" && (
                <Button size="sm" onClick={() => lifecycleMutation.mutate("complete")}>
                  <CheckCircle className="mr-1 h-4 w-4" /> Complete
                </Button>
              )}
              {(show.status === "planned" || show.status === "live") && (
                <Button size="sm" variant="destructive" onClick={() => lifecycleMutation.mutate("cancel")}>
                  <XCircle className="mr-1 h-4 w-4" /> Cancel
                </Button>
              )}
            </div>
          }
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Show info */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Show Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-xs text-muted-foreground">Created</p>
              <p className="text-sm">{formatDateTime(show.created_at)}</p>
            </div>
            {show.started_at && (
              <div>
                <p className="text-xs text-muted-foreground">Started</p>
                <p className="text-sm">{formatDateTime(show.started_at)}</p>
              </div>
            )}
            {show.completed_at && (
              <div>
                <p className="text-xs text-muted-foreground">Completed</p>
                <p className="text-sm">{formatDateTime(show.completed_at)}</p>
              </div>
            )}
            {show.platform_url && (
              <div>
                <p className="text-xs text-muted-foreground">Platform</p>
                <a
                  href={show.platform_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center text-sm text-primary hover:underline"
                >
                  Open on Whatnot <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              </div>
            )}
            {show.notes && (
              <div>
                <p className="text-xs text-muted-foreground">Notes</p>
                <p className="text-sm">{show.notes}</p>
              </div>
            )}
            <Separator />
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Orders</p>
                <p className="text-lg font-bold">{orders.length}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Revenue</p>
                <p className="text-lg font-bold">{formatCurrency(totalRevenue)}</p>
              </div>
              <div className="col-span-2">
                <p className="text-xs text-muted-foreground">Profit</p>
                <p className={`text-lg font-bold ${totalProfit >= 0 ? "text-green-600" : "text-red-600"}`}>
                  {formatCurrency(totalProfit)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Orders */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Orders ({orders.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={orderColumns}
              data={orders}
              isLoading={loadingOrders}
              emptyTitle="No orders"
              emptyDescription="No orders have been placed for this show yet."
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
