import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { queryKeys } from "@/lib/query-keys";
import { settingsApi } from "@/features/settings/api";
import { formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { PageSkeleton } from "@/components/loading-skeleton";
import { toast } from "sonner";

export function AccountSettingsPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.account.detail,
    queryFn: () => settingsApi.getAccount(),
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: { name: data?.data?.name ?? "" },
    values: data?.data ? { name: data.data.name } : undefined,
  });

  const mutation = useMutation({
    mutationFn: (d: { name: string }) => settingsApi.updateAccount(d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.account.detail });
      toast.success("Account updated");
    },
    onError: () => toast.error("Update failed"),
  });

  if (isLoading) return <PageSkeleton />;
  if (!data?.data) return <div>Account not found</div>;

  const account = data.data;

  return (
    <div className="space-y-6">
      <Card>
        <form onSubmit={handleSubmit((d) => mutation.mutate(d))}>
          <CardHeader>
            <CardTitle>Account Details</CardTitle>
            <CardDescription>Manage your business account settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="max-w-md space-y-2">
              <Label htmlFor="account-name">Business Name</Label>
              <Input id="account-name" {...register("name", { required: "Business name is required" })} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="flex items-center gap-4 rounded-lg border p-4">
              <div>
                <p className="text-sm font-medium">Plan</p>
                <p className="text-xs text-muted-foreground">Current subscription tier</p>
              </div>
              <Badge variant={account.plan_tier === "paid" ? "default" : "secondary"} className="ml-auto">
                {account.plan_tier.toUpperCase()}
              </Badge>
            </div>
            <div className="text-xs text-muted-foreground">
              Account created {formatDate(account.created_at)}
            </div>
          </CardContent>
          <CardFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving…" : "Save Changes"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
