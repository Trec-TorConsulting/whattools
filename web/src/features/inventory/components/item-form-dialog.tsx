import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CreateItemSchema, type CreateItem, type Item, type Category } from "@/lib/schemas";
import { queryKeys } from "@/lib/query-keys";
import { inventoryApi } from "@/features/inventory/api";
import { ApiClientError } from "@/lib/api-client";
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

type ItemFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item?: Item;
  categories: Category[];
};

export function ItemFormDialog({ open, onOpenChange, item, categories }: ItemFormDialogProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const isEditing = !!item;

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<CreateItem>({
    resolver: zodResolver(CreateItemSchema),
    defaultValues: item
      ? {
          name: item.name,
          sku: item.sku ?? "",
          cogs: item.cogs,
          sale_price: item.sale_price ?? "",
          quantity: item.quantity,
          notes: item.notes ?? "",
          category_id: item.category_id ?? "",
          status: item.status,
        }
      : { quantity: 1, status: "available" },
  });

  const categoryId = watch("category_id");

  const mutation = useMutation({
    mutationFn: (data: CreateItem) =>
      isEditing ? inventoryApi.updateItem(item.id, data) : inventoryApi.createItem(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.items.all });
      toast.success(isEditing ? "Item updated" : "Item created");
      reset();
      onOpenChange(false);
    },
    onError: (err) => {
      if (err instanceof ApiClientError) {
        setError(err.errors[0]?.message ?? "Operation failed");
      } else {
        setError("An unexpected error occurred");
      }
    },
  });

  const onSubmit = (data: CreateItem) => {
    setError(null);
    mutation.mutate(data);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>{isEditing ? "Edit Item" : "Add Item"}</DialogTitle>
            <DialogDescription>
              {isEditing ? "Update item details" : "Add a new item to your inventory"}
            </DialogDescription>
          </DialogHeader>

          <div className="mt-4 space-y-4">
            {error && (
              <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="name">Item Name *</Label>
                <Input id="name" placeholder="Vintage Pokémon Card" {...register("name")} />
                {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="sku">SKU</Label>
                <Input id="sku" placeholder="PKM-001" {...register("sku")} />
              </div>

              <div className="space-y-2">
                <Label htmlFor="quantity">Quantity *</Label>
                <Input id="quantity" type="number" min={0} {...register("quantity", { valueAsNumber: true })} />
                {errors.quantity && <p className="text-xs text-destructive">{errors.quantity.message}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="cogs">Cost (COGS) *</Label>
                <Input id="cogs" placeholder="0.00" {...register("cogs")} />
                {errors.cogs && <p className="text-xs text-destructive">{errors.cogs.message}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="sale_price">Sale Price</Label>
                <Input id="sale_price" placeholder="0.00" {...register("sale_price")} />
              </div>

              <div className="space-y-2">
                <Label>Category</Label>
                <Select
                  value={categoryId ?? ""}
                  onValueChange={(v) => setValue("category_id", v || undefined)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((cat) => (
                      <SelectItem key={cat.id} value={cat.id}>
                        {cat.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Status</Label>
                <Select
                  value={watch("status")}
                  onValueChange={(v) => setValue("status", v as CreateItem["status"])}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="available">Available</SelectItem>
                    <SelectItem value="sold">Sold</SelectItem>
                    <SelectItem value="reserved">Reserved</SelectItem>
                    <SelectItem value="listed">Listed</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="notes">Notes</Label>
                <Input id="notes" placeholder="Optional notes…" {...register("notes")} />
              </div>
            </div>
          </div>

          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving…" : isEditing ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
