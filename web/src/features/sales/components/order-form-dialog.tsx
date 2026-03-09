import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CreateOrderSchema, type CreateOrder, type Order } from "@/lib/schemas";
import { queryKeys } from "@/lib/query-keys";
import { salesApi } from "@/features/sales/api";
import { inventoryApi } from "@/features/inventory/api";
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

type OrderFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  order?: Order;
  showId?: string;
};

export function OrderFormDialog({ open, onOpenChange, order, showId }: OrderFormDialogProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const isEditing = !!order;

  const { data: showsData } = useQuery({
    queryKey: queryKeys.shows.all,
    queryFn: () => salesApi.listShows({ limit: 100 }),
    enabled: !isEditing,
  });

  const { data: itemsData } = useQuery({
    queryKey: queryKeys.items.all,
    queryFn: () => inventoryApi.listItems({ status: "available", limit: 100 }),
    enabled: !isEditing,
  });

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<CreateOrder>({
    resolver: zodResolver(CreateOrderSchema),
    defaultValues: order
      ? {
          show_id: order.show_id,
          buyer_username: order.buyer_username,
          item_id: order.item_id,
          quantity: order.quantity,
          sale_price: order.sale_price,
          platform_fees: order.platform_fees,
          shipping_cost: order.shipping_cost,
        }
      : { quantity: 1, platform_fees: "0", shipping_cost: "0", show_id: showId ?? "" },
  });

  const mutation = useMutation({
    mutationFn: (data: CreateOrder) =>
      isEditing ? salesApi.updateOrder(order.id, data) : salesApi.createOrder(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.orders.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.shows.all });
      toast.success(isEditing ? "Order updated" : "Order created");
      reset();
      onOpenChange(false);
    },
    onError: () => setError("Operation failed"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={handleSubmit((d) => { setError(null); mutation.mutate(d); })}>
          <DialogHeader>
            <DialogTitle>{isEditing ? "Edit Order" : "Create Order"}</DialogTitle>
            <DialogDescription>
              {isEditing ? "Update order details" : "Record a new sale"}
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 space-y-4">
            {error && <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}

            {!isEditing && (
              <div className="space-y-2">
                <Label>Show *</Label>
                <Select value={watch("show_id")} onValueChange={(v) => setValue("show_id", v)}>
                  <SelectTrigger><SelectValue placeholder="Select show" /></SelectTrigger>
                  <SelectContent>
                    {(showsData?.data ?? []).map((s) => (
                      <SelectItem key={s.id} value={s.id}>{s.title}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.show_id && <p className="text-xs text-destructive">{errors.show_id.message}</p>}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="buyer_username">Buyer Username *</Label>
              <Input id="buyer_username" placeholder="@buyer" {...register("buyer_username")} />
              {errors.buyer_username && <p className="text-xs text-destructive">{errors.buyer_username.message}</p>}
            </div>

            {!isEditing && (
              <div className="space-y-2">
                <Label>Item *</Label>
                <Select value={watch("item_id")} onValueChange={(v) => setValue("item_id", v)}>
                  <SelectTrigger><SelectValue placeholder="Select item" /></SelectTrigger>
                  <SelectContent>
                    {(itemsData?.data ?? []).map((item) => (
                      <SelectItem key={item.id} value={item.id}>{item.name} ({item.sku ?? "No SKU"})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.item_id && <p className="text-xs text-destructive">{errors.item_id.message}</p>}
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="quantity">Quantity</Label>
                <Input id="quantity" type="number" min={1} {...register("quantity", { valueAsNumber: true })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sale_price">Sale Price *</Label>
                <Input id="sale_price" placeholder="0.00" {...register("sale_price")} />
                {errors.sale_price && <p className="text-xs text-destructive">{errors.sale_price.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="platform_fees">Platform Fees</Label>
                <Input id="platform_fees" placeholder="0.00" {...register("platform_fees")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="shipping_cost">Shipping Cost</Label>
                <Input id="shipping_cost" placeholder="0.00" {...register("shipping_cost")} />
              </div>
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
