import { useState } from "react";
import { Link } from "react-router";
import { toast } from "sonner";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useAdminAccounts,
  useSuspendAccount,
  useUnsuspendAccount,
  useUpdateAccountPlan,
} from "../hooks/use-admin-api";
import { Skeleton } from "@/components/ui/skeleton";

export function AdminAccountsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [planFilter, setPlanFilter] = useState<string>("");
  const [suspendedFilter, setSuspendedFilter] = useState<string>("");

  const { data, isLoading } = useAdminAccounts({
    page,
    per_page: 25,
    search: search || undefined,
    plan_tier: planFilter || undefined,
    is_suspended: suspendedFilter === "true" ? true : suspendedFilter === "false" ? false : undefined,
  });

  const suspendMutation = useSuspendAccount();
  const unsuspendMutation = useUnsuspendAccount();
  const planMutation = useUpdateAccountPlan();

  function handleSuspend(accountId: string, name: string) {
    if (!confirm(`Suspend account "${name}"? Users will not be able to log in.`)) return;
    suspendMutation.mutate(accountId, {
      onSuccess: () => toast.success(`Account "${name}" suspended`),
      onError: (e) => toast.error(e.message),
    });
  }

  function handleUnsuspend(accountId: string, name: string) {
    unsuspendMutation.mutate(accountId, {
      onSuccess: () => toast.success(`Account "${name}" unsuspended`),
      onError: (e) => toast.error(e.message),
    });
  }

  function handlePlanChange(accountId: string, newPlan: string) {
    planMutation.mutate(
      { accountId, planTier: newPlan },
      {
        onSuccess: () => toast.success("Plan updated"),
        onError: (e) => toast.error(e.message),
      }
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Accounts</h1>
        <p className="text-muted-foreground">Manage all customer accounts</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search accounts..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-9"
          />
        </div>
        <Select value={planFilter} onValueChange={(v) => { setPlanFilter(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Plan" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Plans</SelectItem>
            <SelectItem value="free">Free</SelectItem>
            <SelectItem value="paid">Paid</SelectItem>
          </SelectContent>
        </Select>
        <Select value={suspendedFilter} onValueChange={(v) => { setSuspendedFilter(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="false">Active</SelectItem>
            <SelectItem value="true">Suspended</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Plan</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Users</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-20" /></TableCell>
                    ))}
                  </TableRow>
                ))
              : data?.accounts.map((account) => (
                  <TableRow key={account.id}>
                    <TableCell className="font-medium">
                      <Link to={`/admin/accounts/${account.id}`} className="hover:underline">
                        {account.name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Select
                        value={account.plan_tier}
                        onValueChange={(v) => handlePlanChange(account.id, v)}
                      >
                        <SelectTrigger className="h-7 w-20">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="free">Free</SelectItem>
                          <SelectItem value="paid">Paid</SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell>
                      {account.is_suspended ? (
                        <Badge variant="destructive">Suspended</Badge>
                      ) : (
                        <Badge variant="secondary" className="bg-green-500/10 text-green-600">Active</Badge>
                      )}
                    </TableCell>
                    <TableCell>{account.user_count}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(account.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      {account.is_suspended ? (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleUnsuspend(account.id, account.name)}
                          disabled={unsuspendMutation.isPending}
                        >
                          Unsuspend
                        </Button>
                      ) : (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleSuspend(account.id, account.name)}
                          disabled={suspendMutation.isPending}
                        >
                          Suspend
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
            {!isLoading && data?.accounts.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                  No accounts found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {data?.pagination && data.pagination.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {data.pagination.page} of {data.pagination.pages} ({data.pagination.total} total)
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft className="h-4 w-4" /> Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= (data.pagination.pages || 1)}
              onClick={() => setPage((p) => p + 1)}
            >
              Next <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
