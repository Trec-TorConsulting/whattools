import { useState } from "react";
import { Link } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { MoreHorizontal, Tag, Truck, CheckCircle, XCircle } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";
import { shippingApi } from "@/features/shipping/api";
import { usePagination } from "@/hooks/use-pagination";
import type { Shipment } from "@/lib/schemas";
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

export function ShipmentsListPage() {
  const queryClient = useQueryClient();
  const pagination = usePagination();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Shipment | null>(null);

  const filters = {
    cursor: pagination.cursor ?? undefined,
    status: statusFilter || undefined,
    search: search || undefined,
    limit: 25,
  };

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.shipments.list(filters),
    queryFn: () => shippingApi.listShipments(filters),
  });

  const payload = data?.data as Record<string, unknown> | undefined;
  const shipments = (payload?.items as Shipment[]) ?? [];
  const hasMore = !!payload?.next_cursor;
  const nextCursor = payload?.next_cursor as string | undefined;

  const deleteMutation = useMutation({
    mutationFn: (id: string) => shippingApi.deleteShipment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.shipments.all });
      toast.success("Shipment deleted");
      setDeleteTarget(null);
    },
  });

  const lifecycleMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "label" | "ship" | "deliver" | "cancel" }) => {
      if (action === "label") return shippingApi.createLabel(id);
      if (action === "ship") return shippingApi.markShipped(id);
      if (action === "deliver") return shippingApi.markDelivered(id);
      return shippingApi.cancelShipment(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.shipments.all });
      toast.success("Shipment updated");
    },
  });

  const columns: ColumnDef<Shipment, unknown>[] = [
    {
      accessorKey: "buyer_username",
      header: "Buyer",
      cell: ({ row }) => (
        <Link to={`/shipments/${row.original.id}`} className="font-medium text-primary hover:underline">
          @{row.original.buyer_username}
        </Link>
      ),
    },
    {
      accessorKey: "carrier",
      header: "Carrier",
      cell: ({ row }) => row.original.carrier ?? "—",
    },
    {
      accessorKey: "tracking_number",
      header: "Tracking",
      cell: ({ row }) =>
        row.original.tracking_number ? (
          <span className="font-mono text-xs">{row.original.tracking_number}</span>
        ) : (
          "—"
        ),
    },
    {
      accessorKey: "city",
      header: "Destination",
      cell: ({ row }) => {
        const s = row.original;
        return s.city && s.state ? `${s.city}, ${s.state}` : s.city ?? "—";
      },
    },
    {
      accessorKey: "ship_by_date",
      header: "Ship By",
      cell: ({ row }) => {
        if (!row.original.ship_by_date) return "—";
        const isOverdue = new Date(row.original.ship_by_date) < new Date() && row.original.status === "pending";
        return (
          <span className={isOverdue ? "font-medium text-destructive" : ""}>
            {formatDate(row.original.ship_by_date)}
          </span>
        );
      },
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      id: "actions",
      header: "",
      enableSorting: false,
      cell: ({ row }) => {
        const s = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link to={`/shipments/${s.id}`}>View Details</Link>
              </DropdownMenuItem>
              {s.status === "pending" && (
                <DropdownMenuItem onClick={() => lifecycleMutation.mutate({ id: s.id, action: "label" })}>
                  <Tag className="mr-2 h-4 w-4" /> Create Label
                </DropdownMenuItem>
              )}
              {(s.status === "pending" || s.status === "label_created") && (
                <DropdownMenuItem onClick={() => lifecycleMutation.mutate({ id: s.id, action: "ship" })}>
                  <Truck className="mr-2 h-4 w-4" /> Mark Shipped
                </DropdownMenuItem>
              )}
              {s.status === "shipped" && (
                <DropdownMenuItem onClick={() => lifecycleMutation.mutate({ id: s.id, action: "deliver" })}>
                  <CheckCircle className="mr-2 h-4 w-4" /> Mark Delivered
                </DropdownMenuItem>
              )}
              {(s.status === "pending" || s.status === "label_created") && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="text-destructive" onClick={() => lifecycleMutation.mutate({ id: s.id, action: "cancel" })}>
                    <XCircle className="mr-2 h-4 w-4" /> Cancel
                  </DropdownMenuItem>
                </>
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
        title="Shipments"
        description="Track and fulfill your orders"
      />

      <DataTable
        columns={columns}
        data={shipments}
        isLoading={isLoading}
        searchPlaceholder="Search shipments…"
        searchValue={search}
        onSearchChange={setSearch}
        emptyTitle="No shipments"
        emptyDescription="Shipments will appear here when orders are ready to ship."
        pagination={{
          page: pagination.page,
          canGoBack: pagination.canGoBack,
          hasMore,
          onNext: () => { if (nextCursor) pagination.goToNext(nextCursor); },
          onPrev: () => pagination.goToPrev(),
        }}
        toolbar={
          <Select value={statusFilter || "all"} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="label_created">Label Created</SelectItem>
              <SelectItem value="shipped">Shipped</SelectItem>
              <SelectItem value="delivered">Delivered</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
        }
      />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
        title="Delete Shipment"
        description="Are you sure you want to delete this shipment?"
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={() => { if (deleteTarget) deleteMutation.mutate(deleteTarget.id); }}
      />
    </div>
  );
}
