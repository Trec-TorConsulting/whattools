import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, Plus, FileText, Loader2, CheckCircle, XCircle, Clock } from "lucide-react";
import { queryKeys } from "@/lib/query-keys";
import { analyticsApi } from "@/features/analytics/api";
import { formatDate } from "@/lib/utils";
import type { ExportJob, CreateExport } from "@/lib/schemas";

import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

const STATUS_ICONS: Record<string, React.ReactNode> = {
  pending: <Clock className="h-4 w-4 text-muted-foreground" />,
  processing: <Loader2 className="h-4 w-4 animate-spin text-primary" />,
  completed: <CheckCircle className="h-4 w-4 text-green-500" />,
  failed: <XCircle className="h-4 w-4 text-destructive" />,
};

const REPORT_LABELS: Record<string, string> = {
  summary: "Summary Report",
  categories: "Category Performance",
  shows: "Shows Performance",
  trends: "Revenue Trends",
  top_items: "Top Items",
  full: "Full Report",
};

export function ExportsPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [reportType, setReportType] = useState<string>("summary");
  const [format, setFormat] = useState<string>("csv");
  const [period, setPeriod] = useState<string>("30d");

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.exports.all,
    queryFn: () => analyticsApi.listExports(),
    refetchInterval: (query) => {
      const exports = query.state.data?.data;
      if (exports?.some((e: ExportJob) => e.status === "pending" || e.status === "processing")) {
        return 3000;
      }
      return false;
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: CreateExport) => analyticsApi.createExport(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.exports.all });
      toast.success("Export started");
      setCreateOpen(false);
    },
    onError: () => toast.error("Failed to create export"),
  });

  const handleDownload = async (job: ExportJob) => {
    try {
      const blob = await analyticsApi.downloadExport(job.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${job.report_type}-${job.period}.${job.format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Download failed");
    }
  };

  const exports = data?.data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Exports"
        description="Generate and download reports"
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" /> New Export
          </Button>
        }
      />

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      ) : exports.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No exports"
          description="Create your first report export."
          action={{ label: "New Export", onClick: () => setCreateOpen(true) }}
        />
      ) : (
        <div className="space-y-3">
          {exports.map((job) => (
            <Card key={job.id}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  {STATUS_ICONS[job.status]}
                  <div>
                    <p className="text-sm font-medium">{REPORT_LABELS[job.report_type] ?? job.report_type}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(job.created_at)} · {job.period} · {job.format.toUpperCase()}
                      {job.file_size ? ` · ${(job.file_size / 1024).toFixed(1)} KB` : ""}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={job.status === "completed" ? "success" : job.status === "failed" ? "destructive" : "secondary"}>
                    {job.status}
                  </Badge>
                  {job.status === "completed" && (
                    <Button size="sm" variant="outline" onClick={() => handleDownload(job)}>
                      <Download className="mr-1 h-4 w-4" /> Download
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Export Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create Export</DialogTitle>
            <DialogDescription>Generate a report to download</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Report Type</Label>
              <Select value={reportType} onValueChange={setReportType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="summary">Summary Report</SelectItem>
                  <SelectItem value="categories">Category Performance</SelectItem>
                  <SelectItem value="shows">Shows Performance</SelectItem>
                  <SelectItem value="trends">Revenue Trends</SelectItem>
                  <SelectItem value="top_items">Top Items</SelectItem>
                  <SelectItem value="full">Full Report</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Format</Label>
              <Select value={format} onValueChange={setFormat}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="csv">CSV</SelectItem>
                  <SelectItem value="pdf">PDF</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Period</Label>
              <Select value={period} onValueChange={setPeriod}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="7d">Last 7 days</SelectItem>
                  <SelectItem value="30d">Last 30 days</SelectItem>
                  <SelectItem value="90d">Last 90 days</SelectItem>
                  <SelectItem value="365d">Last year</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button
              disabled={createMutation.isPending}
              onClick={() => createMutation.mutate({
                report_type: reportType as CreateExport["report_type"],
                format: format as CreateExport["format"],
                period,
              })}
            >
              {createMutation.isPending ? "Creating…" : "Create Export"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
