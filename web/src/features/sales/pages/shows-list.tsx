import { useState, useCallback } from "react";
import { Link } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, MoreHorizontal, Tv, Play, CheckCircle, XCircle } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import { queryKeys } from "@/lib/query-keys";
import { formatDate, formatRelative } from "@/lib/utils";
import { salesApi } from "@/features/sales/api";
import { usePagination } from "@/hooks/use-pagination";
import type { Show } from "@/lib/schemas";
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
import { ShowFormDialog } from "@/features/sales/components/show-form-dialog";

export function ShowsListPage() {
  const queryClient = useQueryClient();
  const pagination = usePagination();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editShow, setEditShow] = useState<Show | undefined>();
  const [deleteTarget, setDeleteTarget] = useState<Show | null>(null);

  const filters = {
    cursor: pagination.cursor ?? undefined,
    status: statusFilter || undefined,
    search: search || undefined,
    limit: 25,
  };

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.shows.list(filters),
    queryFn: () => salesApi.listShows(filters),
  });

  const shows = data?.data ?? [];
  const hasMore = (data?.meta as Record<string, unknown>)?.has_more === true;
  const nextCursor = (data?.meta as Record<string, unknown>)?.next_cursor as string | undefined;

  const deleteMutation = useMutation({
    mutationFn: (id: string) => salesApi.deleteShow(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.shows.all });
      toast.success("Show deleted");
      setDeleteTarget(null);
    },
  });

  const lifecycleMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "start" | "complete" | "cancel" }) => {
      if (action === "start") return salesApi.startShow(id);
      if (action === "complete") return salesApi.completeShow(id);
      return salesApi.cancelShow(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.shows.all });
      toast.success("Show updated");
    },
  });

  const openCreate = useCallback(() => {
    setEditShow(undefined);
    setFormOpen(true);
  }, []);

  const columns: ColumnDef<Show, unknown>[] = [
    {
      accessorKey: "title",
      header: "Title",
      cell: ({ row }) => (
        <Link to={`/shows/${row.original.id}`} className="font-medium text-primary hover:underline">
          {row.original.title}
        </Link>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: "scheduled_at",
      header: "Scheduled",
      cell: ({ row }) =>
        row.original.scheduled_at ? formatRelative(row.original.scheduled_at) : "—",
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) => formatDate(row.original.created_at),
    },
    {
      id: "actions",
      header: "",
      enableSorting: false,
      cell: ({ row }) => {
        const show = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link to={`/shows/${show.id}`}>
                  <Tv className="mr-2 h-4 w-4" /> View Details
                </Link>
              </DropdownMenuItem>
              {show.status === "planned" && (
                <DropdownMenuItem onClick={() => lifecycleMutation.mutate({ id: show.id, action: "start" })}>
                  <Play className="mr-2 h-4 w-4" /> Go Live
                </DropdownMenuItem>
              )}
              {show.status === "live" && (
                <DropdownMenuItem onClick={() => lifecycleMutation.mutate({ id: show.id, action: "complete" })}>
                  <CheckCircle className="mr-2 h-4 w-4" /> Complete
                </DropdownMenuItem>
              )}
              {(show.status === "planned" || show.status === "live") && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-destructive"
                    onClick={() => lifecycleMutation.mutate({ id: show.id, action: "cancel" })}
                  >
                    <XCircle className="mr-2 h-4 w-4" /> Cancel
                  </DropdownMenuItem>
                </>
              )}
              {show.status === "planned" && (
                <DropdownMenuItem className="text-destructive" onClick={() => setDeleteTarget(show)}>
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
        title="Shows"
        description="Manage your live selling shows"
        actions={
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" /> Create Show
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={shows}
        isLoading={isLoading}
        searchPlaceholder="Search shows…"
        searchValue={search}
        onSearchChange={setSearch}
        emptyTitle="No shows"
        emptyDescription="Create your first live show to start selling."
        emptyAction={{ label: "Create Show", onClick: openCreate }}
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
              <SelectItem value="planned">Planned</SelectItem>
              <SelectItem value="live">Live</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
        }
      />

      <ShowFormDialog open={formOpen} onOpenChange={setFormOpen} show={editShow} />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
        title="Delete Show"
        description={`Delete "${deleteTarget?.title}"? This cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={() => { if (deleteTarget) deleteMutation.mutate(deleteTarget.id); }}
      />
    </div>
  );
}
