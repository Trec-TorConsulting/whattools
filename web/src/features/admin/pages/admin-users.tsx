import { useState } from "react";
import { toast } from "sonner";
import { Search, ChevronLeft, ChevronRight, Shield, ShieldOff, KeyRound } from "lucide-react";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  useAdminUsers,
  useTogglePlatformAdmin,
  useResetUserPassword,
  useImpersonateUser,
} from "../hooks/use-admin-api";
import { useImpersonation } from "../hooks/use-impersonation";

export function AdminUsersPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [resetResult, setResetResult] = useState<{ token: string; email: string; expires: string } | null>(null);

  const { data, isLoading } = useAdminUsers({
    page,
    per_page: 25,
    search: search || undefined,
  });

  const toggleAdminMutation = useTogglePlatformAdmin();
  const resetPasswordMutation = useResetUserPassword();
  const impersonateMutation = useImpersonateUser();
  const { startImpersonation } = useImpersonation();

  function handleToggleAdmin(userId: string, currentStatus: boolean, email: string) {
    const action = currentStatus ? "demote" : "promote";
    if (!confirm(`${currentStatus ? "Demote" : "Promote"} ${email} ${currentStatus ? "from" : "to"} platform admin?`)) return;
    toggleAdminMutation.mutate(userId, {
      onSuccess: () => toast.success(`${email} ${action}d`),
      onError: (e) => toast.error(e.message),
    });
  }

  function handleResetPassword(userId: string, email: string) {
    if (!confirm(`Generate a password reset link for ${email}?`)) return;
    resetPasswordMutation.mutate(userId, {
      onSuccess: (data) => {
        setResetResult({ token: data.reset_token, email: data.user_email, expires: data.expires_at });
      },
      onError: (e) => toast.error(e.message),
    });
  }

  function handleImpersonate(userId: string, name: string) {
    impersonateMutation.mutate(userId, {
      onSuccess: (data) => {
        startImpersonation(data.access_token, data.user);
        toast.success(`Now impersonating ${name}`);
      },
      onError: (e) => toast.error(e.message),
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Users</h1>
        <p className="text-muted-foreground">Manage all platform users</p>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search by name or email..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="pl-9"
        />
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Admin</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 7 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-20" /></TableCell>
                    ))}
                  </TableRow>
                ))
              : data?.users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">{user.name || "—"}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{user.role}</Badge>
                    </TableCell>
                    <TableCell>
                      {user.is_active ? (
                        <Badge className="bg-green-500/10 text-green-600" variant="secondary">Active</Badge>
                      ) : (
                        <Badge variant="destructive">Inactive</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {user.is_platform_admin && (
                        <Badge className="bg-red-500/10 text-red-500">Admin</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(user.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          title={user.is_platform_admin ? "Demote from admin" : "Promote to admin"}
                          onClick={() => handleToggleAdmin(user.id, user.is_platform_admin, user.email)}
                          disabled={toggleAdminMutation.isPending}
                        >
                          {user.is_platform_admin ? (
                            <ShieldOff className="h-4 w-4 text-orange-500" />
                          ) : (
                            <Shield className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Reset password"
                          onClick={() => handleResetPassword(user.id, user.email)}
                          disabled={resetPasswordMutation.isPending}
                        >
                          <KeyRound className="h-4 w-4" />
                        </Button>
                        {!user.is_platform_admin && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleImpersonate(user.id, user.name || user.email)}
                            disabled={impersonateMutation.isPending}
                          >
                            Impersonate
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
            {!isLoading && data?.users.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                  No users found.
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
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              <ChevronLeft className="h-4 w-4" /> Previous
            </Button>
            <Button variant="outline" size="sm" disabled={page >= (data.pagination.pages || 1)} onClick={() => setPage((p) => p + 1)}>
              Next <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Reset Password Result Dialog */}
      <Dialog open={!!resetResult} onOpenChange={() => setResetResult(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Password Reset Token</DialogTitle>
            <DialogDescription>
              A password reset link has been generated for {resetResult?.email}. Send this link to the user.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium">Reset Link</label>
              <div className="mt-1 rounded-md bg-muted p-3 text-sm break-all font-mono">
                {window.location.origin}/reset-password?token={resetResult?.token}
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              Expires: {resetResult?.expires ? new Date(resetResult.expires).toLocaleString() : "—"}
            </p>
            <Button
              className="w-full"
              onClick={() => {
                navigator.clipboard.writeText(
                  `${window.location.origin}/reset-password?token=${resetResult?.token}`
                );
                toast.success("Reset link copied to clipboard");
              }}
            >
              Copy to Clipboard
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
