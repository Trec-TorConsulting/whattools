import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper, type ColumnDef } from "@tanstack/react-table";
import { MoreHorizontal, Eye, Upload, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { queryKeys } from "@/lib/query-keys";
import { whatnotApi } from "@/features/whatnot/api";
import type { WhatnotListing } from "@/lib/schemas";
import { PageHeader } from "@/components/page-header";
import { DataTable } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { usePagination } from "@/hooks/use-pagination";

const columnHelper = createColumnHelper<WhatnotListing>();

export function WhatnotListingsPage() {
  const queryClient = useQueryClient();
  const pagination = usePagination();

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.whatnot.listings({ cursor: pagination.cursor }),
    queryFn: () => whatnotApi.listListings({ cursor: pagination.cursor ?? undefined, limit: 25 }),
  });

  const publishMutation = useMutation({
    mutationFn: (id: string) => whatnotApi.publishListing(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.whatnot.listings() });
      toast.success("Listing published");
    },
    onError: () => toast.error("Failed to publish listing"),
  });

  const unpublishMutation = useMutation({
    mutationFn: (id: string) => whatnotApi.unpublishListing(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.whatnot.listings() });
      toast.success("Listing unpublished");
    },
    onError: () => toast.error("Failed to unpublish listing"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => whatnotApi.deleteListing(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.whatnot.listings() });
      toast.success("Listing deleted");
    },
    onError: () => toast.error("Failed to delete listing"),
  });

  const columns: ColumnDef<WhatnotListing, unknown>[] = [
    columnHelper.accessor("title", {
      header: "Title",
      cell: (info) => <span className="font-medium">{info.getValue() || "Untitled"}</span>,
    }),
    columnHelper.accessor("status", {
      header: "Status",
      cell: (info) => {
        const s = info.getValue();
        return (
          <Badge variant={s === "published" ? "success" : s === "draft" ? "secondary" : "outline"}>
            {s || "unknown"}
          </Badge>
        );
      },
    }),
    columnHelper.accessor("price", {
      header: "Price",
      cell: (info) => {
        const v = info.getValue();
        return v != null ? `$${(v / 100).toFixed(2)}` : "—";
      },
    }),
    columnHelper.display({
      id: "actions",
      cell: ({ row }) => {
        const listing = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => publishMutation.mutate(listing.id)}>
                <Upload className="mr-2 h-4 w-4" /> Publish
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => unpublishMutation.mutate(listing.id)}>
                <Eye className="mr-2 h-4 w-4" /> Unpublish
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => deleteMutation.mutate(listing.id)}
                className="text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" /> Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    }),
  ];

  const listings = data?.data ?? [];
  const hasMore = (data?.meta as Record<string, unknown>)?.has_more as boolean | undefined;
  const nextCursor = (data?.meta as Record<string, unknown>)?.next_cursor as string | undefined;

  return (
    <div className="space-y-6">
      <PageHeader title="Whatnot Listings" description="Manage your listings on Whatnot" />

      <DataTable
        columns={columns}
        data={listings}
        isLoading={isLoading}
        onPrevious={pagination.cursor ? () => pagination.goToPrev() : undefined}
        onNext={hasMore && nextCursor ? () => pagination.goToNext(nextCursor) : undefined}
      />
    </div>
  );
}
