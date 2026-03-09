import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Shield, UserCog } from "lucide-react";
import { queryKeys } from "@/lib/query-keys";
import { settingsApi } from "@/features/settings/api";
import { useAuth } from "@/hooks/use-auth";
import { canManageTeam, canChangeRoles } from "@/lib/role-utils";
import { formatDate } from "@/lib/utils";
import type { TeamMember } from "@/lib/schemas";
import { InviteMemberSchema } from "@/lib/schemas";
import { PageHeader } from "@/components/page-header";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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

const ROLE_BADGES: Record<string, "default" | "secondary" | "outline"> = {
  owner: "default",
  admin: "secondary",
  member: "outline",
};

export function TeamSettingsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"admin" | "member">("member");
  const [removeTarget, setRemoveTarget] = useState<TeamMember | null>(null);

  const canManage = user ? canManageTeam(user.role) : false;
  const canRoles = user ? canChangeRoles(user.role) : false;

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.account.members,
    queryFn: () => settingsApi.listMembers(),
  });

  const inviteMutation = useMutation({
    mutationFn: (data: { email: string; role: "admin" | "member" }) => settingsApi.inviteMember(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.account.members });
      toast.success("Invitation sent");
      setInviteOpen(false);
      setInviteEmail("");
    },
    onError: () => toast.error("Failed to send invitation"),
  });

  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: "admin" | "member" }) =>
      settingsApi.updateMemberRole(id, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.account.members });
      toast.success("Role updated");
    },
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => settingsApi.removeMember(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.account.members });
      toast.success("Member removed");
      setRemoveTarget(null);
    },
  });

  const members = data?.data ?? [];

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault();
    const result = InviteMemberSchema.safeParse({ email: inviteEmail, role: inviteRole });
    if (!result.success) {
      toast.error(result.error.errors[0]?.message ?? "Invalid input");
      return;
    }
    inviteMutation.mutate(result.data);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Team"
        description="Manage your team members and roles"
        actions={
          canManage ? (
            <Button onClick={() => setInviteOpen(true)}>
              <Plus className="mr-2 h-4 w-4" /> Invite Member
            </Button>
          ) : undefined
        }
      />

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      ) : members.length === 0 ? (
        <EmptyState
          icon={UserCog}
          title="No team members"
          description="Invite team members to collaborate."
          action={canManage ? { label: "Invite Member", onClick: () => setInviteOpen(true) } : undefined}
        />
      ) : (
        <div className="space-y-3">
          {members.map((member) => (
            <Card key={member.id}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback>
                      {member.name
                        .split(" ")
                        .map((n) => n[0])
                        .join("")
                        .toUpperCase()
                        .slice(0, 2)}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{member.name}</p>
                      <Badge variant={ROLE_BADGES[member.role] ?? "outline"}>
                        <Shield className="mr-1 h-3 w-3" />
                        {member.role}
                      </Badge>
                      {!member.is_active && <Badge variant="destructive">Inactive</Badge>}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {member.email} · Joined {formatDate(member.created_at)}
                    </p>
                  </div>
                </div>
                {canRoles && member.role !== "owner" && member.id !== user?.id && (
                  <div className="flex items-center gap-2">
                    <Select
                      value={member.role}
                      onValueChange={(role) =>
                        roleMutation.mutate({ id: member.id, role: role as "admin" | "member" })
                      }
                    >
                      <SelectTrigger className="w-[110px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="admin">Admin</SelectItem>
                        <SelectItem value="member">Member</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive"
                      onClick={() => setRemoveTarget(member)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Invite Dialog */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent className="sm:max-w-md">
          <form onSubmit={handleInvite}>
            <DialogHeader>
              <DialogTitle>Invite Team Member</DialogTitle>
              <DialogDescription>Send an invitation to join your team</DialogDescription>
            </DialogHeader>
            <div className="mt-4 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="invite-email">Email</Label>
                <Input
                  id="invite-email"
                  type="email"
                  placeholder="teammate@example.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Role</Label>
                <Select value={inviteRole} onValueChange={(v) => setInviteRole(v as "admin" | "member")}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin — manage shows, orders, shipments</SelectItem>
                    <SelectItem value="member">Member — view and manage inventory only</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter className="mt-6">
              <Button type="button" variant="outline" onClick={() => setInviteOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={inviteMutation.isPending}>
                {inviteMutation.isPending ? "Sending…" : "Send Invitation"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!removeTarget}
        onOpenChange={() => setRemoveTarget(null)}
        title="Remove Member"
        description={`Remove ${removeTarget?.name} from the team? They will lose access immediately.`}
        confirmLabel="Remove"
        variant="destructive"
        onConfirm={() => { if (removeTarget) removeMutation.mutate(removeTarget.id); }}
      />
    </div>
  );
}
