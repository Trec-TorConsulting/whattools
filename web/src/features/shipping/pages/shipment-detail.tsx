import { useParams, Link } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Tag, Truck, CheckCircle, XCircle, MapPin, Package } from "lucide-react";
import { queryKeys } from "@/lib/query-keys";
import { shippingApi } from "@/features/shipping/api";
import { formatDate, formatDateTime } from "@/lib/utils";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { PageSkeleton } from "@/components/loading-skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";

export function ShipmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.shipments.detail(id!),
    queryFn: () => shippingApi.getShipment(id!),
    enabled: !!id,
  });

  const lifecycleMutation = useMutation({
    mutationFn: (action: "label" | "ship" | "deliver" | "cancel") => {
      if (action === "label") return shippingApi.createLabel(id!);
      if (action === "ship") return shippingApi.markShipped(id!);
      if (action === "deliver") return shippingApi.markDelivered(id!);
      return shippingApi.cancelShipment(id!);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.shipments.detail(id!) });
      toast.success("Shipment updated");
    },
  });

  if (isLoading) return <PageSkeleton />;
  if (!data?.data) return <div>Shipment not found</div>;

  const shipment = data.data;
  const hasAddress = shipment.address_line1 || shipment.city;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/shipments"><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <PageHeader
          title={`Shipment for @${shipment.buyer_username}`}
          actions={
            <div className="flex items-center gap-2">
              <StatusBadge status={shipment.status} />
              {shipment.status === "pending" && (
                <Button size="sm" variant="outline" onClick={() => lifecycleMutation.mutate("label")}>
                  <Tag className="mr-1 h-4 w-4" /> Create Label
                </Button>
              )}
              {(shipment.status === "pending" || shipment.status === "label_created") && (
                <Button size="sm" onClick={() => lifecycleMutation.mutate("ship")}>
                  <Truck className="mr-1 h-4 w-4" /> Mark Shipped
                </Button>
              )}
              {shipment.status === "shipped" && (
                <Button size="sm" onClick={() => lifecycleMutation.mutate("deliver")}>
                  <CheckCircle className="mr-1 h-4 w-4" /> Mark Delivered
                </Button>
              )}
              {(shipment.status === "pending" || shipment.status === "label_created") && (
                <Button size="sm" variant="destructive" onClick={() => lifecycleMutation.mutate("cancel")}>
                  <XCircle className="mr-1 h-4 w-4" /> Cancel
                </Button>
              )}
            </div>
          }
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Shipping Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Package className="h-4 w-4" /> Shipping Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Carrier</p>
                <p className="text-sm font-medium">{shipment.carrier ?? "Not set"}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Tracking Number</p>
                <p className="font-mono text-sm">{shipment.tracking_number ?? "Not set"}</p>
              </div>
              {shipment.weight_oz && (
                <div>
                  <p className="text-xs text-muted-foreground">Weight</p>
                  <p className="text-sm">{shipment.weight_oz} oz</p>
                </div>
              )}
              {shipment.ship_by_date && (
                <div>
                  <p className="text-xs text-muted-foreground">Ship By</p>
                  <p className="text-sm">{formatDate(shipment.ship_by_date)}</p>
                </div>
              )}
            </div>
            <Separator />
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Created</p>
                <p className="text-sm">{formatDateTime(shipment.created_at)}</p>
              </div>
              {shipment.shipped_at && (
                <div>
                  <p className="text-xs text-muted-foreground">Shipped</p>
                  <p className="text-sm">{formatDateTime(shipment.shipped_at)}</p>
                </div>
              )}
              {shipment.delivered_at && (
                <div>
                  <p className="text-xs text-muted-foreground">Delivered</p>
                  <p className="text-sm">{formatDateTime(shipment.delivered_at)}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Address */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <MapPin className="h-4 w-4" /> Delivery Address
            </CardTitle>
          </CardHeader>
          <CardContent>
            {hasAddress ? (
              <div className="space-y-1 text-sm">
                <p className="font-medium">@{shipment.buyer_username}</p>
                {shipment.address_line1 && <p>{shipment.address_line1}</p>}
                {shipment.address_line2 && <p>{shipment.address_line2}</p>}
                <p>
                  {[shipment.city, shipment.state, shipment.zip_code].filter(Boolean).join(", ")}
                </p>
              </div>
            ) : (
              <p className="py-4 text-center text-sm text-muted-foreground">No address provided</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
