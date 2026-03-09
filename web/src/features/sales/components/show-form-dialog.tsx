import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CreateShowSchema, type CreateShow, type Show } from "@/lib/schemas";
import { queryKeys } from "@/lib/query-keys";
import { salesApi } from "@/features/sales/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type ShowFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  show?: Show;
};

export function ShowFormDialog({ open, onOpenChange, show }: ShowFormDialogProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const isEditing = !!show;

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateShow>({
    resolver: zodResolver(CreateShowSchema),
    defaultValues: show
      ? { title: show.title, scheduled_at: show.scheduled_at ?? "", platform_url: show.platform_url ?? "", notes: show.notes ?? "" }
      : {},
  });

  const mutation = useMutation({
    mutationFn: (data: CreateShow) =>
      isEditing ? salesApi.updateShow(show.id, data) : salesApi.createShow(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.shows.all });
      toast.success(isEditing ? "Show updated" : "Show created");
      reset();
      onOpenChange(false);
    },
    onError: () => {
      setError("Operation failed. Please try again.");
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={handleSubmit((d) => { setError(null); mutation.mutate(d); })}>
          <DialogHeader>
            <DialogTitle>{isEditing ? "Edit Show" : "Create Show"}</DialogTitle>
            <DialogDescription>
              {isEditing ? "Update show details" : "Schedule a new live show"}
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 space-y-4">
            {error && (
              <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
            )}
            <div className="space-y-2">
              <Label htmlFor="title">Title *</Label>
              <Input id="title" placeholder="Friday Night Cards Live" {...register("title")} />
              {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="scheduled_at">Scheduled Date & Time</Label>
              <Input id="scheduled_at" type="datetime-local" {...register("scheduled_at")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="platform_url">Whatnot URL</Label>
              <Input id="platform_url" placeholder="https://www.whatnot.com/live/..." {...register("platform_url")} />
              {errors.platform_url && <p className="text-xs text-destructive">{errors.platform_url.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Input id="notes" placeholder="Optional notes…" {...register("notes")} />
            </div>
          </div>
          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving…" : isEditing ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
