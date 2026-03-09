import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type StatCardProps = {
  title: string;
  value: string;
  description?: string;
  icon?: LucideIcon;
  trend?: { value: number; label: string };
  className?: string;
};

export function StatCard({ title, value, description, icon: Icon, trend, className }: StatCardProps) {
  return (
    <Card className={cn("relative overflow-hidden", className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          {Icon && (
            <div className="rounded-lg bg-primary/10 p-2">
              <Icon className="h-4 w-4 text-primary" />
            </div>
          )}
        </div>
        <div className="mt-2">
          <p className="text-2xl font-bold tracking-tight">{value}</p>
          {(trend || description) && (
            <p className="mt-1 text-xs text-muted-foreground">
              {trend && (
                <span
                  className={cn(
                    "mr-1 font-medium",
                    trend.value > 0 ? "text-success" : trend.value < 0 ? "text-destructive" : ""
                  )}
                >
                  {trend.value > 0 ? "+" : ""}
                  {trend.value}%
                </span>
              )}
              {trend?.label ?? description}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
