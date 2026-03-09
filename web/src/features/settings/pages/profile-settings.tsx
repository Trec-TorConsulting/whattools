
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { UpdateProfileSchema, ChangePasswordSchema } from "@/lib/schemas";
import { queryKeys } from "@/lib/query-keys";
import { settingsApi } from "@/features/settings/api";
import { useAuth } from "@/hooks/use-auth";
import { ApiClientError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

export function ProfileSettingsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // Profile form
  const {
    register: registerProfile,
    handleSubmit: handleProfile,
    formState: { errors: profileErrors },
  } = useForm({
    resolver: zodResolver(UpdateProfileSchema),
    defaultValues: { name: user?.name ?? "", email: user?.email ?? "" },
  });

  const profileMutation = useMutation({
    mutationFn: (data: { name?: string; email?: string }) => settingsApi.updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.user.current });
      toast.success("Profile updated");
    },
    onError: (err) => {
      toast.error(err instanceof ApiClientError ? err.errors[0]?.message ?? "Update failed" : "Update failed");
    },
  });

  // Password form
  const {
    register: registerPassword,
    handleSubmit: handlePassword,
    reset: resetPassword,
    formState: { errors: passwordErrors },
  } = useForm({
    resolver: zodResolver(ChangePasswordSchema),
  });

  const passwordMutation = useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      settingsApi.changePassword(data),
    onSuccess: () => {
      toast.success("Password changed");
      resetPassword();
    },
    onError: (err) => {
      toast.error(err instanceof ApiClientError ? err.errors[0]?.message ?? "Failed" : "Failed to change password");
    },
  });

  return (
    <div className="space-y-6">
      {/* Profile */}
      <Card>
        <form onSubmit={handleProfile((d) => profileMutation.mutate(d))}>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
            <CardDescription>Update your personal information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" {...registerProfile("name")} />
                {profileErrors.name && <p className="text-xs text-destructive">{profileErrors.name.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" {...registerProfile("email")} />
                {profileErrors.email && <p className="text-xs text-destructive">{profileErrors.email.message}</p>}
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button type="submit" disabled={profileMutation.isPending}>
              {profileMutation.isPending ? "Saving…" : "Save Changes"}
            </Button>
          </CardFooter>
        </form>
      </Card>

      {/* Password */}
      <Card>
        <form onSubmit={handlePassword((d) => passwordMutation.mutate({ current_password: d.current_password, new_password: d.new_password }))}>
          <CardHeader>
            <CardTitle>Change Password</CardTitle>
            <CardDescription>Update your password to keep your account secure</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="max-w-md space-y-4">
              <div className="space-y-2">
                <Label htmlFor="current_password">Current Password</Label>
                <Input id="current_password" type="password" {...registerPassword("current_password")} />
                {passwordErrors.current_password && (
                  <p className="text-xs text-destructive">{String(passwordErrors.current_password.message)}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="new_password">New Password</Label>
                <Input id="new_password" type="password" {...registerPassword("new_password")} />
                {passwordErrors.new_password && (
                  <p className="text-xs text-destructive">{String(passwordErrors.new_password.message)}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm_password">Confirm New Password</Label>
                <Input id="confirm_password" type="password" {...registerPassword("confirm_password")} />
                {passwordErrors.confirm_password && (
                  <p className="text-xs text-destructive">{String(passwordErrors.confirm_password.message)}</p>
                )}
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button type="submit" disabled={passwordMutation.isPending}>
              {passwordMutation.isPending ? "Changing…" : "Change Password"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
