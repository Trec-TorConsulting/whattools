import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link2, Link2Off, RefreshCw, ArrowUpDown, Package, ShoppingCart, Tv, AlertCircle } from "lucide-react";
import { toast } from "sonner";

import { queryKeys } from "@/lib/query-keys";
import { formatDateTime, formatRelative } from "@/lib/utils";
import { whatnotApi } from "@/features/whatnot/api";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageSkeleton } from "@/components/loading-skeleton";

export function WhatnotDashboardPage() {
  const queryClient = useQueryClient();

  const { data: statusData, isLoading: statusLoading } = useQuery({
    queryKey: queryKeys.whatnot.status,
    queryFn: () => whatnotApi.status(),
  });

  const { data: syncData, isLoading: syncLoading } = useQuery({
    queryKey: queryKeys.whatnot.syncStatus,
    queryFn: () => whatnotApi.syncStatus(),
  });

  const connectMutation = useMutation({
    mutationFn: () => whatnotApi.connect(),
    onSuccess: ({ data }) => {
      window.location.href = data.authorize_url;
    },
    onError: () => toast.error("Failed to start Whatnot connection"),
  });

  const disconnectMutation = useMutation({
    mutationFn: () => whatnotApi.disconnect(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.whatnot.status });
      toast.success("Disconnected from Whatnot");
    },
    onError: () => toast.error("Failed to disconnect"),
  });

  const fullSyncMutation = useMutation({
    mutationFn: () => whatnotApi.fullSync(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.whatnot.syncStatus });
      toast.success("Full sync started");
    },
    onError: () => toast.error("Failed to start sync"),
  });

  const pullProductsMutation = useMutation({
    mutationFn: () => whatnotApi.pullProducts(),
    onSuccess: ({ data }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.whatnot.syncStatus });
      queryClient.invalidateQueries({ queryKey: queryKeys.items.all });
      toast.success(`Products synced: ${data.created} created, ${data.updated} updated`);
    },
    onError: () => toast.error("Failed to pull products"),
  });

  const syncOrdersMutation = useMutation({
    mutationFn: () => whatnotApi.syncOrders(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.whatnot.syncStatus });
      queryClient.invalidateQueries({ queryKey: queryKeys.orders.all });
      toast.success("Orders synced successfully");
    },
    onError: () => toast.error("Failed to sync orders"),
  });

  const syncLivestreamsMutation = useMutation({
    mutationFn: () => whatnotApi.syncLivestreams(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.whatnot.syncStatus });
      queryClient.invalidateQueries({ queryKey: queryKeys.shows.all });
      toast.success("Livestreams synced successfully");
    },
    onError: () => toast.error("Failed to sync livestreams"),
  });

  if (statusLoading) return <PageSkeleton />;

  const status = statusData?.data;
  const syncStatus = syncData?.data;
  const isConnected = status?.connected;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Whatnot Integration"
        description="Connect and sync your Whatnot seller account"
        actions={
          isConnected ? (
            <Button
              onClick={() => fullSyncMutation.mutate()}
              disabled={fullSyncMutation.isPending}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${fullSyncMutation.isPending ? "animate-spin" : ""}`} />
              Full Sync
            </Button>
          ) : undefined
        }
      />

      {/* Connection status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {isConnected ? (
              <Link2 className="h-5 w-5 text-green-500" />
            ) : (
              <Link2Off className="h-5 w-5 text-muted-foreground" />
            )}
            Connection Status
          </CardTitle>
          <CardDescription>
            {isConnected
              ? `Connected as @${status?.whatnot_username}`
              : "Connect your Whatnot seller account to sync products, orders, and livestreams."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isConnected ? (
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">
                  Last synced: {status?.last_sync_at ? formatRelative(status.last_sync_at) : "Never"}
                </p>
                <p className="text-sm text-muted-foreground">Scopes: {status?.scopes || "full_access"}</p>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => disconnectMutation.mutate()}
                disabled={disconnectMutation.isPending}
              >
                <Link2Off className="mr-2 h-4 w-4" />
                Disconnect
              </Button>
            </div>
          ) : (
            <Button onClick={() => connectMutation.mutate()} disabled={connectMutation.isPending}>
              <Link2 className="mr-2 h-4 w-4" />
              Connect Whatnot Account
            </Button>
          )}
        </CardContent>
      </Card>

      {isConnected && (
        <>
          {/* Quick sync actions */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Package className="h-4 w-4" />
                  Products
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  onClick={() => pullProductsMutation.mutate()}
                  disabled={pullProductsMutation.isPending}
                >
                  <ArrowUpDown className={`mr-2 h-4 w-4 ${pullProductsMutation.isPending ? "animate-spin" : ""}`} />
                  Sync Products
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <ShoppingCart className="h-4 w-4" />
                  Orders
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  onClick={() => syncOrdersMutation.mutate()}
                  disabled={syncOrdersMutation.isPending}
                >
                  <ArrowUpDown className={`mr-2 h-4 w-4 ${syncOrdersMutation.isPending ? "animate-spin" : ""}`} />
                  Sync Orders
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Tv className="h-4 w-4" />
                  Livestreams
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  onClick={() => syncLivestreamsMutation.mutate()}
                  disabled={syncLivestreamsMutation.isPending}
                >
                  <ArrowUpDown className={`mr-2 h-4 w-4 ${syncLivestreamsMutation.isPending ? "animate-spin" : ""}`} />
                  Sync Livestreams
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Sync history */}
          <Card>
            <CardHeader>
              <CardTitle>Sync History</CardTitle>
              <CardDescription>Recent synchronization activity</CardDescription>
            </CardHeader>
            <CardContent>
              {syncLoading ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
              ) : syncStatus?.recent && syncStatus.recent.length > 0 ? (
                <div className="space-y-3">
                  {syncStatus.recent.map((log, i) => (
                    <div key={i} className="flex items-center justify-between rounded-lg border p-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium capitalize">
                            {log.sync_type.replace("_", " ")}
                          </span>
                          <Badge
                            variant={
                              log.status === "completed"
                                ? "success"
                                : log.status === "failed"
                                  ? "destructive"
                                  : "secondary"
                            }
                          >
                            {log.status}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {formatDateTime(log.started_at)}
                        </p>
                      </div>
                      <div className="text-right text-sm">
                        {log.status === "completed" ? (
                          <span className="text-muted-foreground">
                            {log.items_created} created, {log.items_updated} updated
                          </span>
                        ) : log.status === "failed" ? (
                          <span className="flex items-center gap-1 text-destructive">
                            <AlertCircle className="h-3 w-3" />
                            {log.error_message || "Error"}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">In progress...</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No sync history yet. Run a sync to get started.</p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
