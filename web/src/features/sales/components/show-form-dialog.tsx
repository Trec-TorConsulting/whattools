import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Repeat } from "lucide-react";
import { cn } from "@/lib/utils";

const DAYS_OF_WEEK = [
  { abbr: "mon", label: "Mon" },
  { abbr: "tue", label: "Tue" },
  { abbr: "wed", label: "Wed" },
  { abbr: "thu", label: "Thu" },
  { abbr: "fri", label: "Fri" },
  { abbr: "sat", label: "Sat" },
  { abbr: "sun", label: "Sun" },
] as const;

function getRecurrenceSummary(
  rule?: string,
  weeks?: number,
  days?: string,
  scheduledAt?: string,
): string | null {
  if (!rule || !weeks || !scheduledAt) return null;
  const start = new Date(scheduledAt);
  if (isNaN(start.getTime())) return null;

  if (rule === "weekly" && days) {
    const dayList = days.split(",").filter(Boolean);
    const totalShows = dayList.length * weeks;
    return `${totalShows} shows over ${weeks} week${weeks > 1 ? "s" : ""} (${dayList.join(", ")})`;
  }

  const countMap: Record<string, number> = { hourly: 1, daily: 1, weekly: 1, monthly: 1 };
  const total = (countMap[rule] ?? 1) * weeks;
  const unitMap: Record<string, string> = {
    hourly: `${total} show${total > 1 ? "s" : ""} over ${weeks} hour${weeks > 1 ? "s" : ""}`,
    daily: `${total} show${total > 1 ? "s" : ""} over ${weeks} day${weeks > 1 ? "s" : ""}`,
    weekly: `${total} show${total > 1 ? "s" : ""} over ${weeks} week${weeks > 1 ? "s" : ""}`,
    monthly: `${total} show${total > 1 ? "s" : ""} over ${weeks} month${weeks > 1 ? "s" : ""}`,
  };
  return unitMap[rule] ?? null;
}

type ShowFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  show?: Show;
};

export function ShowFormDialog({ open, onOpenChange, show }: ShowFormDialogProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [repeatEnabled, setRepeatEnabled] = useState(false);
  const [selectedDays, setSelectedDays] = useState<string[]>([]);
  const isEditing = !!show;

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    control,
    formState: { errors },
  } = useForm<CreateShow>({
    resolver: zodResolver(CreateShowSchema),
    defaultValues: show
      ? {
          title: show.title,
          scheduled_at: show.scheduled_at ?? "",
          scheduled_end_at: show.scheduled_end_at ?? "",
          platform_url: show.platform_url ?? "",
          notes: show.notes ?? "",
        }
      : { recurrence_weeks: 1 },
  });

  const recurrenceRule = useWatch({ control, name: "recurrence_rule" });
  const recurrenceWeeks = useWatch({ control, name: "recurrence_weeks" });
  const scheduledAt = useWatch({ control, name: "scheduled_at" });
  const recurrenceDays = useWatch({ control, name: "recurrence_days" });

  const toggleDay = (abbr: string) => {
    const next = selectedDays.includes(abbr)
      ? selectedDays.filter((d) => d !== abbr)
      : [...selectedDays, abbr];
    setSelectedDays(next);
    setValue("recurrence_days", next.join(","));
  };

  const mutation = useMutation({
    mutationFn: (data: CreateShow) => {
      const payload = { ...data };
      if (!repeatEnabled) {
        delete payload.recurrence_rule;
        delete payload.recurrence_days;
        delete payload.recurrence_weeks;
      }
      return isEditing ? salesApi.updateShow(show.id, payload) : salesApi.createShow(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.shows.all });
      toast.success(
        isEditing
          ? "Show updated"
          : repeatEnabled
            ? "Created recurring shows"
            : "Show created",
      );
      reset();
      setRepeatEnabled(false);
      setSelectedDays([]);
      onOpenChange(false);
    },
    onError: () => {
      setError("Operation failed. Please try again.");
    },
  });

  const recurrenceSummary = repeatEnabled
    ? getRecurrenceSummary(recurrenceRule, recurrenceWeeks, recurrenceDays, scheduledAt)
    : null;

  const durationLabel: Record<string, string> = {
    hourly: "Hours",
    daily: "Days",
    weekly: "Weeks",
    monthly: "Months",
  };

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
          <div className="mt-6 space-y-5">
            {error && (
              <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
            )}
            <div className="space-y-2">
              <Label htmlFor="title">Title *</Label>
              <Input id="title" placeholder="Friday Night Cards Live" {...register("title")} />
              {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="scheduled_at">Start Time {repeatEnabled && "*"}</Label>
                <Input id="scheduled_at" type="datetime-local" {...register("scheduled_at")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="scheduled_end_at">End Time</Label>
                <Input id="scheduled_end_at" type="datetime-local" {...register("scheduled_end_at")} />
              </div>
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

            {/* Recurrence section - only for new shows */}
            {!isEditing && (
              <div className="rounded-lg border p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Repeat className="h-4 w-4 text-muted-foreground" />
                    <Label className="text-sm font-medium">Repeat Show</Label>
                  </div>
                  <Button
                    type="button"
                    variant={repeatEnabled ? "default" : "outline"}
                    size="sm"
                    onClick={() => {
                      setRepeatEnabled(!repeatEnabled);
                      if (!repeatEnabled) {
                        setValue("recurrence_rule", "weekly");
                        setValue("recurrence_weeks", 1);
                        setSelectedDays([]);
                        setValue("recurrence_days", undefined);
                      } else {
                        setValue("recurrence_rule", undefined);
                        setValue("recurrence_weeks", undefined);
                        setValue("recurrence_days", undefined);
                        setSelectedDays([]);
                      }
                    }}
                  >
                    {repeatEnabled ? "On" : "Off"}
                  </Button>
                </div>

                {repeatEnabled && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label className="text-xs text-muted-foreground">Frequency</Label>
                        <Select
                          value={recurrenceRule ?? "weekly"}
                          onValueChange={(v) => {
                            setValue("recurrence_rule", v as "hourly" | "daily" | "weekly" | "monthly");
                            if (v !== "weekly") {
                              setSelectedDays([]);
                              setValue("recurrence_days", undefined);
                            }
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="hourly">Hourly</SelectItem>
                            <SelectItem value="daily">Daily</SelectItem>
                            <SelectItem value="weekly">Weekly</SelectItem>
                            <SelectItem value="monthly">Monthly</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs text-muted-foreground">
                          {durationLabel[recurrenceRule ?? "weekly"] ?? "Periods"} to repeat
                        </Label>
                        <Select
                          value={String(recurrenceWeeks ?? 1)}
                          onValueChange={(v) => setValue("recurrence_weeks", Number(v))}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
                              <SelectItem key={n} value={String(n)}>
                                {n}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* Day-of-week picker for weekly frequency */}
                    {recurrenceRule === "weekly" && (
                      <div className="space-y-1">
                        <Label className="text-xs text-muted-foreground">
                          Shows per week (select days)
                        </Label>
                        <div className="flex gap-1">
                          {DAYS_OF_WEEK.map(({ abbr, label }) => (
                            <Button
                              key={abbr}
                              type="button"
                              variant={selectedDays.includes(abbr) ? "default" : "outline"}
                              size="sm"
                              className={cn(
                                "h-8 w-10 px-0 text-xs",
                                selectedDays.includes(abbr) && "font-semibold",
                              )}
                              onClick={() => toggleDay(abbr)}
                            >
                              {label}
                            </Button>
                          ))}
                        </div>
                        {selectedDays.length === 0 && (
                          <p className="text-xs text-muted-foreground">
                            Select at least one day, or leave empty to repeat on the same weekday
                          </p>
                        )}
                      </div>
                    )}

                    {recurrenceSummary && (
                      <p className="text-xs text-muted-foreground">{recurrenceSummary}</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending
                ? "Saving…"
                : isEditing
                  ? "Update"
                  : repeatEnabled
                    ? "Create Recurring Shows"
                    : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
