import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminAuditLogs } from "../hooks/use-admin-api";

const ACTION_COLORS: Record<string, string> = {
  "account.suspended": "bg-red-500/10 text-red-500",
  "account.unsuspended": "bg-green-500/10 text-green-600",
  "account.plan_changed": "bg-blue-500/10 text-blue-500",
  "user.password_reset_initiated": "bg-orange-500/10 text-orange-500",
  "user.promoted_to_admin": "bg-purple-500/10 text-purple-500",
  "user.demoted_from_admin": "bg-gray-500/10 text-gray-500",
  "user.impersonated": "bg-yellow-500/10 text-yellow-600",
};

export function AdminAuditLogsPage() {
  const [page, setPage] = useState(1);

  const { data, isLoading } = useAdminAuditLogs({ page, per_page: 50 });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Audit Log</h1>
        <p className="text-muted-foreground">All platform admin actions</p>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Timestamp</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Target</TableHead>
              <TableHead>IP Address</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 10 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 5 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-24" /></TableCell>
                    ))}
                  </TableRow>
                ))
              : data?.logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className={ACTION_COLORS[log.action] || ""}
                      >
                        {log.action}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[300px] truncate">
                      {log.description || "—"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {log.target_type}
                      {log.target_id && (
                        <span className="ml-1 font-mono text-xs">
                          {log.target_id.slice(0, 8)}...
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {log.ip_address || "—"}
                    </TableCell>
                  </TableRow>
                ))}
            {!isLoading && data?.logs.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                  No audit logs yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {data?.pagination && data.pagination.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {data.pagination.page} of {data.pagination.pages} ({data.pagination.total} total)
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              <ChevronLeft className="h-4 w-4" /> Previous
            </Button>
            <Button variant="outline" size="sm" disabled={page >= (data.pagination.pages || 1)} onClick={() => setPage((p) => p + 1)}>
              Next <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
