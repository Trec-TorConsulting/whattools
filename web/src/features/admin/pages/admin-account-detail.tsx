import { useParams, Link } from "react-router";
import { toast } from "sonner";
import { ArrowLeft, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  useAdminAccount,
  useAdminUsers,
  useSuspendAccount,
  useUnsuspendAccount,
  useImpersonateUser,
} from "../hooks/use-admin-api";
import { useImpersonation } from "../hooks/use-impersonation";

export function AdminAccountDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: account, isLoading: accountLoading } = useAdminAccount(id!);
  const { data: usersData, isLoading: usersLoading } = useAdminUsers({ account_id: id });
  const suspendMutation = useSuspendAccount();
  const unsuspendMutation = useUnsuspendAccount();
  const impersonateMutation = useImpersonateUser();
  const { startImpersonation } = useImpersonation();

  function handleImpersonate(userId: string, userName: string) {
    impersonateMutation.mutate(userId, {
      onSuccess: (data) => {
        startImpersonation(data.access_token, data.user);
        toast.success(`Now impersonating ${userName}`);
      },
      onError: (e) => toast.error(e.message),
    });
  }

  if (accountLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!account) return <p className="text-muted-foreground">Account not found.</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/admin/accounts">
          <Button variant="ghost" size="icon"><ArrowLeft className="h-5 w-5" /></Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">{account.name}</h1>
          <p className="text-sm text-muted-foreground">Account ID: {account.id}</p>
        </div>
        {account.is_suspended ? (
          <Button
            variant="outline"
            onClick={() => unsuspendMutation.mutate(account.id, {
              onSuccess: () => toast.success("Account unsuspended"),
              onError: (e) => toast.error(e.message),
            })}
            disabled={unsuspendMutation.isPending}
          >
            Unsuspend
          </Button>
        ) : (
          <Button
            variant="destructive"
            onClick={() => {
              if (!confirm(`Suspend "${account.name}"?`)) return;
              suspendMutation.mutate(account.id, {
                onSuccess: () => toast.success("Account suspended"),
                onError: (e) => toast.error(e.message),
              });
            }}
            disabled={suspendMutation.isPending}
          >
            Suspend
          </Button>
        )}
      </div>

      {/* Account Info */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Plan</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant={account.plan_tier === "paid" ? "default" : "secondary"}>
              {account.plan_tier}
            </Badge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Status</CardTitle>
          </CardHeader>
          <CardContent>
            {account.is_suspended ? (
              <Badge variant="destructive">Suspended</Badge>
            ) : (
              <Badge className="bg-green-500/10 text-green-600" variant="secondary">Active</Badge>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Users</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-muted-foreground" />
              <span className="text-xl font-bold">{account.user_count}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Account Users */}
      <Card>
        <CardHeader>
          <CardTitle>Team Members</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {usersLoading
                ? Array.from({ length: 3 }).map((_, i) => (
                    <TableRow key={i}>
                      {Array.from({ length: 5 }).map((_, j) => (
                        <TableCell key={j}><Skeleton className="h-4 w-20" /></TableCell>
                      ))}
                    </TableRow>
                  ))
                : usersData?.users.map((user) => (
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
                      <TableCell className="text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleImpersonate(user.id, user.name || user.email)}
                          disabled={impersonateMutation.isPending || user.is_platform_admin}
                          title={user.is_platform_admin ? "Cannot impersonate admin" : `Impersonate ${user.name || user.email}`}
                        >
                          Impersonate
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
              {!usersLoading && usersData?.users.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                    No users found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
