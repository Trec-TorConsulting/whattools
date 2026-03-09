import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, MoreHorizontal, Truck, CheckCircle, XCircle } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import { queryKeys } from "@/lib/query-keys";
import { formatCurrency, formatDate } from "@/lib/utils";
import { salesApi } from "@/features/sales/api";
import { usePagination } from "@/hooks/use-pagination";
import type { Order } from "@/lib/schemas";
import { PageHeader } from "@/components/page-header";
import { DataTable } from "@/components/data-table";
import { StatusBadge } from "@/components/status-badge";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { OrderFormDialog } from "@/features/sales/components/order-form-dialog";

export function OrdersListPage() {
  const queryClient = useQueryClient();
  const pagination = usePagination();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editOrder, setEditOrder] = useState<Order | undefined>();
  const [deleteTarget, setDeleteTarget] = useState<Order | null>(null);

  const filters = {
    cursor: pagination.cursor ?? undefined,
    status: statusFilter || undefined,
    search: search || undefined,
    limit: 25,
  };

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.orders.list(filters),
    queryFn: () => salesApi.listOrders(filters),
  });

  const orders = data?.data ?? [];
  const hasMore = (data?.meta as Record<string, unknown>)?.has_more === true;
  const nextCursor = (data?.meta as Record<string, unknown>)?.next_cursor as string | undefined;

  const deleteMutation = useMutation({
    mutationFn: (id: string) => salesApi.deleteOrder(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.orders.all });
      toast.success("Order deleted");
      setDeleteTarget(null);
    },
  });

  const lifecycleMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "ship" | "deliver" | "cancel" }) => {
      if (action === "ship") return salesApi.shipOrder(id);
      if (action === "deliver") return salesApi.deliverOrder(id);
      return salesApi.cancelOrder(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.orders.all });
      toast.success("Order updated");
    },
  });

  const openCreate = useCallback(() => {
    setEditOrder(undefined);
    setFormOpen(true);
  }, []);

  const columns: ColumnDef<Order, unknown>[] = [
    {
      accessorKey: "buyer_username",
      header: "Buyer",
      cell: ({ row }) => <span className="font-medium">@{row.original.buyer_username}</span>,
    },
    {
      accessorKey: "item_name",
      header: "Item",
      cell: ({ row }) => (
        <p className="max-w-[200px] truncate">{row.original.item_name}</p>
      ),
    },
    { accessorKey: "quantity", header: "Qty" },
    {
      accessorKey: "sale_price",
      header: "Price",
      cell: ({ row }) => formatCurrency(Number(row.original.sale_price)),
    },
    {
      accessorKey: "profit",
      header: "Profit",
      cell: ({ row }) => {
        const val = Number(row.original.profit);
        return <span className={val >= 0 ? "text-green-600" : "text-red-600"}>{formatCurrency(val)}</span>;
      },
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: "created_at",
      header: "Date",
      cell: ({ row }) => formatDate(row.original.created_at),
    },
    {
      id: "actions",
      header: "",
      enableSorting: false,
      cell: ({ row }) => {
        const o = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {o.status === "pending" && (
                <DropdownMenuItem onClick={() => lifecycleMutation.mutate({ id: o.id, action: "ship" })}>
                  <Truck className="mr-2 h-4 w-4" /> Mark Shipped
                </DropdownMenuItem>
              )}
              {o.status === "shipped" && (
                <DropdownMenuItem onClick={() => lifecycleMutation.mutate({ id: o.id, action: "deliver" })}>
                  <CheckCircle className="mr-2 h-4 w-4" /> Mark Delivered
                </DropdownMenuItem>
              )}
              {o.status === "pending" && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="text-destructive" onClick={() => lifecycleMutation.mutate({ id: o.id, action: "cancel" })}>
                    <XCircle className="mr-2 h-4 w-4" /> Cancel
                  </DropdownMenuItem>
                </>
              )}
              {o.status === "pending" && (
                <DropdownMenuItem className="text-destructive" onClick={() => setDeleteTarget(o)}>
                  Delete
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Orders"
        description="Track and manage your sales"
        actions={
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" /> Create Order
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={orders}
        isLoading={isLoading}
        searchPlaceholder="Search orders…"
        searchValue={search}
        onSearchChange={setSearch}
        emptyTitle="No orders"
        emptyDescription="Orders will appear here when sales are recorded."
        emptyAction={{ label: "Create Order", onClick: openCreate }}
        pagination={{
          page: pagination.page,
          canGoBack: pagination.canGoBack,
          hasMore,
          onNext: () => { if (nextCursor) pagination.goToNext(nextCursor); },
          onPrev: () => pagination.goToPrev(),
        }}
        toolbar={
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="shipped">Shipped</SelectItem>
              <SelectItem value="delivered">Delivered</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
        }
      />

      <OrderFormDialog open={formOpen} onOpenChange={setFormOpen} order={editOrder} />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
        title="Delete Order"
        description={`Delete this order for @${deleteTarget?.buyer_username}?`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={() => { if (deleteTarget) deleteMutation.mutate(deleteTarget.id); }}
      />
    </div>
  );
}
