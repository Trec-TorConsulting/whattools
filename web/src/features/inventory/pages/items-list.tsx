import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Upload, Trash2, MoreHorizontal, Pencil, Tags } from "lucide-react";
import { Link } from "react-router";
import type { ColumnDef } from "@tanstack/react-table";
import { queryKeys } from "@/lib/query-keys";
import { formatCurrency, formatDate } from "@/lib/utils";
import { inventoryApi } from "@/features/inventory/api";
import { usePagination } from "@/hooks/use-pagination";
import type { Item, Category } from "@/lib/schemas";
import { PageHeader } from "@/components/page-header";
import { DataTable } from "@/components/data-table";
import { StatusBadge } from "@/components/status-badge";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
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
import { ItemFormDialog } from "@/features/inventory/components/item-form-dialog";
import { CsvImportDialog } from "@/features/inventory/components/csv-import-dialog";

export function ItemsListPage() {
  const queryClient = useQueryClient();
  const pagination = usePagination();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [formOpen, setFormOpen] = useState(false);
  const [editItem, setEditItem] = useState<Item | undefined>();
  const [deleteTarget, setDeleteTarget] = useState<Item | null>(null);
  const [csvOpen, setCsvOpen] = useState(false);

  const filters = {
    cursor: pagination.cursor ?? undefined,
    status: statusFilter || undefined,
    category_id: categoryFilter || undefined,
    search: search || undefined,
    limit: 25,
  };

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.items.list(filters),
    queryFn: () => inventoryApi.listItems(filters),
  });

  const { data: categoriesData } = useQuery({
    queryKey: queryKeys.categories.all,
    queryFn: () => inventoryApi.listCategories(),
  });

  const itemsPayload = data?.data as Record<string, unknown> | undefined;
  const items = (itemsPayload?.items as Item[]) ?? [];
  const categories: Category[] =
    (categoriesData?.data as unknown as Record<string, unknown>)?.categories as Category[] ?? [];
  const hasMore = !!itemsPayload?.next_cursor;
  const nextCursor = itemsPayload?.next_cursor as string | undefined;

  const deleteMutation = useMutation({
    mutationFn: (id: string) => inventoryApi.deleteItem(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.items.all });
      toast.success("Item deleted");
      setDeleteTarget(null);
    },
    onError: () => toast.error("Failed to delete item"),
  });

  const openEdit = useCallback((item: Item) => {
    setEditItem(item);
    setFormOpen(true);
  }, []);

  const openCreate = useCallback(() => {
    setEditItem(undefined);
    setFormOpen(true);
  }, []);

  const columns: ColumnDef<Item, unknown>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <div>
          <p className="font-medium">{row.original.name}</p>
          {row.original.sku && (
            <p className="text-xs text-muted-foreground">SKU: {row.original.sku}</p>
          )}
        </div>
      ),
    },
    {
      accessorKey: "quantity",
      header: "Qty",
    },
    {
      accessorKey: "cogs",
      header: "COGS",
      cell: ({ row }) => formatCurrency(Number(row.original.cogs)),
    },
    {
      accessorKey: "sale_price",
      header: "Price",
      cell: ({ row }) =>
        row.original.sale_price ? formatCurrency(Number(row.original.sale_price)) : "—",
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: "created_at",
      header: "Added",
      cell: ({ row }) => formatDate(row.original.created_at),
    },
    {
      id: "actions",
      header: "",
      enableSorting: false,
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => openEdit(row.original)}>
              <Pencil className="mr-2 h-4 w-4" /> Edit
            </DropdownMenuItem>
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => setDeleteTarget(row.original)}
            >
              <Trash2 className="mr-2 h-4 w-4" /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Inventory"
        description="Manage your items and stock levels"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link to="/inventory/categories">
                <Tags className="mr-2 h-4 w-4" /> Categories
              </Link>
            </Button>
            <Button variant="outline" onClick={() => setCsvOpen(true)}>
              <Upload className="mr-2 h-4 w-4" /> Import CSV
            </Button>
            <Button onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" /> Add Item
            </Button>
          </div>
        }
      />

      <DataTable
        columns={columns}
        data={items}
        isLoading={isLoading}
        searchPlaceholder="Search items…"
        searchValue={search}
        onSearchChange={setSearch}
        emptyTitle="No items found"
        emptyDescription="Get started by adding your first item."
        emptyAction={{ label: "Add Item", onClick: openCreate }}
        pagination={{
          page: pagination.page,
          canGoBack: pagination.canGoBack,
          hasMore,
          onNext: () => {
            if (nextCursor) pagination.goToNext(nextCursor);
          },
          onPrev: () => pagination.goToPrev(),
        }}
        toolbar={
          <div className="flex gap-2">
            <Select value={statusFilter || "all"} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="available">Available</SelectItem>
                <SelectItem value="sold">Sold</SelectItem>
                <SelectItem value="reserved">Reserved</SelectItem>
                <SelectItem value="listed">Listed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={categoryFilter || "all"} onValueChange={(v) => setCategoryFilter(v === "all" ? "" : v)}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="All categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {categories.map((cat) => (
                  <SelectItem key={cat.id} value={cat.id}>
                    {cat.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        }
      />

      <ItemFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        item={editItem}
        categories={categories}
      />

      <CsvImportDialog open={csvOpen} onOpenChange={setCsvOpen} />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
        title="Delete Item"
        description={`Are you sure you want to delete "${deleteTarget?.name}"? This item can be restored later.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={() => {
          if (deleteTarget) deleteMutation.mutate(deleteTarget.id);
        }}
      />
    </div>
  );
}
