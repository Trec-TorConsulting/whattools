import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link2, Link2Off, ExternalLink, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { queryKeys } from "@/lib/query-keys";
import { formatRelative } from "@/lib/utils";
import { whatnotApi } from "@/features/whatnot/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { PageSkeleton } from "@/components/loading-skeleton";

export function WhatnotSettingsPage() {
  const queryClient = useQueryClient();

  const { data: statusData, isLoading } = useQuery({
    queryKey: queryKeys.whatnot.status,
    queryFn: () => whatnotApi.status(),
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

  if (isLoading) return <PageSkeleton />;

  const status = statusData?.data;
  const isConnected = status?.connected;

  return (
    <div className="space-y-6">
      {/* Connection card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {isConnected ? (
              <Link2 className="h-5 w-5 text-green-500" />
            ) : (
              <Link2Off className="h-5 w-5 text-muted-foreground" />
            )}
            Whatnot Account
          </CardTitle>
          <CardDescription>
            Connect your Whatnot seller account to sync products, orders, livestreams,
            and images between WhatTools and Whatnot.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isConnected ? (
            <>
              <div className="flex items-start justify-between">
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Badge variant="success" className="gap-1">
                      <ShieldCheck className="h-3 w-3" />
                      Connected
                    </Badge>
                  </div>
                  <dl className="grid gap-2 text-sm">
                    <div className="flex gap-2">
                      <dt className="text-muted-foreground">Username:</dt>
                      <dd className="font-medium">@{status?.whatnot_username}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="text-muted-foreground">Scopes:</dt>
                      <dd>{status?.scopes || "full_access"}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="text-muted-foreground">Last synced:</dt>
                      <dd>{status?.last_sync_at ? formatRelative(status.last_sync_at) : "Never"}</dd>
                    </div>
                  </dl>
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

              <Separator />

              <p className="text-sm text-muted-foreground">
                Your account is connected. Head to the{" "}
                <a href="/whatnot" className="text-primary underline underline-offset-4 hover:text-primary/80">
                  Whatnot Dashboard
                </a>{" "}
                to sync data, manage listings, and view sync history.
              </p>
            </>
          ) : (
            <div className="space-y-4">
              <div className="rounded-lg border border-dashed p-6 text-center">
                <Link2Off className="mx-auto h-10 w-10 text-muted-foreground/50" />
                <h3 className="mt-3 text-sm font-medium">No account connected</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Connect your Whatnot seller account to start syncing your inventory,
                  orders, shows, and images automatically.
                </p>
                <Button
                  className="mt-4"
                  onClick={() => connectMutation.mutate()}
                  disabled={connectMutation.isPending}
                >
                  <Link2 className="mr-2 h-4 w-4" />
                  Connect Whatnot Account
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* What gets synced */}
      <Card>
        <CardHeader>
          <CardTitle>What gets synced</CardTitle>
          <CardDescription>
            Once connected, these data types will be available for sync
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <h4 className="text-sm font-medium">Products &amp; Images</h4>
              <p className="text-sm text-muted-foreground">
                Pull products from Whatnot or push your inventory items with images to create new listings.
              </p>
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-medium">Orders</h4>
              <p className="text-sm text-muted-foreground">
                Import orders automatically and push tracking numbers back to Whatnot for fulfillment.
              </p>
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-medium">Shows &amp; Livestreams</h4>
              <p className="text-sm text-muted-foreground">
                Sync your scheduled and past livestreams so you can track performance and manage listings.
              </p>
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-medium">Webhooks</h4>
              <p className="text-sm text-muted-foreground">
                Receive real-time updates when products sell, listings change, or bulk operations complete.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
