import { Badge } from "@/components/ui/badge";
import { capitalize } from "@/lib/utils";

type StatusConfig = {
  variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning";
  label?: string;
};

const STATUS_MAP: Record<string, StatusConfig> = {
  // Show statuses
  planned: { variant: "secondary", label: "Planned" },
  live: { variant: "success", label: "Live" },
  completed: { variant: "default", label: "Completed" },
  cancelled: { variant: "destructive", label: "Cancelled" },

  // Order statuses
  pending: { variant: "warning", label: "Pending" },
  shipped: { variant: "default", label: "Shipped" },
  delivered: { variant: "success", label: "Delivered" },

  // Shipment statuses
  label_created: { variant: "secondary", label: "Label Created" },

  // Item statuses
  available: { variant: "success", label: "Available" },
  sold: { variant: "default", label: "Sold" },
  reserved: { variant: "warning", label: "Reserved" },
  listed: { variant: "secondary", label: "Listed" },

  // Export statuses
  processing: { variant: "warning", label: "Processing" },
  failed: { variant: "destructive", label: "Failed" },
};

export function StatusBadge({ status }: { status: string }) {
  const config = STATUS_MAP[status] ?? { variant: "outline" as const };
  return <Badge variant={config.variant}>{config.label ?? capitalize(status)}</Badge>;
}
