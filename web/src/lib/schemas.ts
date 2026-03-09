import { z } from "zod";

// Standard API response envelope
export const ApiMetaSchema = z.object({
  request_id: z.string(),
});

export const ApiErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  field: z.string().optional(),
});

export function ApiResponseSchema<T extends z.ZodTypeAny>(dataSchema: T) {
  return z.object({
    data: dataSchema,
    meta: ApiMetaSchema,
    errors: z.array(ApiErrorSchema).default([]),
  });
}

export function ApiListResponseSchema<T extends z.ZodTypeAny>(dataSchema: T) {
  return z.object({
    data: z.array(dataSchema),
    meta: ApiMetaSchema.extend({
      next_cursor: z.string().nullable().optional(),
      has_more: z.boolean().optional(),
    }),
    errors: z.array(ApiErrorSchema).default([]),
  });
}

// Auth schemas
export const LoginRequestSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

export const RegisterRequestSchema = z
  .object({
    name: z.string().min(2, "Name must be at least 2 characters"),
    email: z.string().email("Enter a valid email address"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string(),
    account_name: z.string().min(2, "Account name must be at least 2 characters"),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

export const ForgotPasswordSchema = z.object({
  email: z.string().email("Enter a valid email address"),
});

export const ResetPasswordSchema = z
  .object({
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

export const UserSchema = z.object({
  id: z.string(),
  email: z.string(),
  name: z.string(),
  role: z.enum(["owner", "admin", "member"]),
  account_id: z.string(),
  is_verified: z.boolean(),
  is_active: z.boolean(),
  created_at: z.string(),
});

export const AccountSchema = z.object({
  id: z.string(),
  name: z.string(),
  plan_tier: z.enum(["free", "paid"]),
  created_at: z.string(),
});

export const TokensSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
});

export const LoginResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  user: UserSchema,
});

// Inventory schemas
export const CategorySchema = z.object({
  id: z.string(),
  name: z.string(),
  account_id: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const ItemSchema = z.object({
  id: z.string(),
  name: z.string(),
  sku: z.string().nullable(),
  status: z.enum(["available", "sold", "reserved", "listed"]),
  cogs: z.string(),
  sale_price: z.string().nullable(),
  quantity: z.number(),
  notes: z.string().nullable(),
  category_id: z.string().nullable(),
  account_id: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  deleted_at: z.string().nullable().optional(),
});

export const CreateItemSchema = z.object({
  name: z.string().min(1, "Name is required"),
  sku: z.string().optional(),
  cogs: z.string().min(1, "Cost of goods is required"),
  sale_price: z.string().optional(),
  quantity: z.number().min(0, "Quantity must be 0 or more").default(1),
  notes: z.string().optional(),
  category_id: z.string().optional(),
  status: z.enum(["available", "sold", "reserved", "listed"]).default("available"),
});

// Sales schemas
export const ShowSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(["planned", "live", "completed", "cancelled"]),
  scheduled_at: z.string().nullable(),
  scheduled_end_at: z.string().nullable().optional(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  platform_url: z.string().nullable(),
  notes: z.string().nullable(),
  recurrence_rule: z.enum(["hourly", "daily", "weekly", "monthly"]).nullable().optional(),
  recurrence_days: z.string().nullable().optional(),
  recurrence_weeks: z.number().nullable().optional(),
  recurrence_group_id: z.string().nullable().optional(),
  account_id: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const CreateShowSchema = z.object({
  title: z.string().min(1, "Title is required"),
  scheduled_at: z.string().optional(),
  scheduled_end_at: z.string().optional(),
  platform_url: z.string().url().optional().or(z.literal("")),
  notes: z.string().optional(),
  recurrence_rule: z.enum(["hourly", "daily", "weekly", "monthly"]).optional(),
  recurrence_days: z.string().optional(),
  recurrence_weeks: z.number().min(1).max(8).optional(),
});

export const OrderSchema = z.object({
  id: z.string(),
  show_id: z.string(),
  buyer_username: z.string(),
  item_id: z.string(),
  item_name: z.string(),
  quantity: z.number(),
  sale_price: z.string(),
  platform_fees: z.string(),
  shipping_cost: z.string(),
  cogs: z.string(),
  profit: z.string(),
  status: z.enum(["pending", "shipped", "delivered", "cancelled"]),
  account_id: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const CreateOrderSchema = z.object({
  show_id: z.string().min(1, "Show is required"),
  buyer_username: z.string().min(1, "Buyer username is required"),
  item_id: z.string().min(1, "Item is required"),
  quantity: z.number().min(1).default(1),
  sale_price: z.string().min(1, "Sale price is required"),
  platform_fees: z.string().default("0"),
  shipping_cost: z.string().default("0"),
});

// Shipping schemas
export const ShipmentSchema = z.object({
  id: z.string(),
  order_id: z.string(),
  buyer_username: z.string(),
  status: z.enum(["pending", "label_created", "shipped", "delivered", "cancelled"]),
  tracking_number: z.string().nullable(),
  carrier: z.string().nullable(),
  ship_by_date: z.string().nullable(),
  shipped_at: z.string().nullable(),
  delivered_at: z.string().nullable(),
  address_line1: z.string().nullable(),
  address_line2: z.string().nullable(),
  city: z.string().nullable(),
  state: z.string().nullable(),
  zip_code: z.string().nullable(),
  weight_oz: z.number().nullable(),
  label_url: z.string().nullable(),
  account_id: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const CreateShipmentSchema = z.object({
  order_id: z.string().min(1, "Order is required"),
  buyer_username: z.string().min(1, "Buyer username is required"),
  carrier: z.string().optional(),
  ship_by_date: z.string().optional(),
  address_line1: z.string().optional(),
  address_line2: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  zip_code: z.string().optional(),
  weight_oz: z.number().optional(),
});

// Analytics schemas
export const AnalyticsSummarySchema = z.object({
  total_revenue: z.number(),
  total_profit: z.number(),
  total_orders: z.number(),
  total_shows: z.number(),
  avg_revenue_per_show: z.number(),
  avg_profit_per_show: z.number(),
  avg_orders_per_show: z.number(),
  profit_margin: z.number(),
});

export const TrendPointSchema = z.object({
  date: z.string(),
  revenue: z.number(),
  profit: z.number(),
  orders: z.number(),
});

export const CategoryAnalyticsSchema = z.object({
  category_id: z.string().nullable(),
  category_name: z.string(),
  revenue: z.number(),
  profit: z.number(),
  orders: z.number(),
  items_sold: z.number(),
});

export const TopItemSchema = z.object({
  item_id: z.string(),
  item_name: z.string(),
  revenue: z.number(),
  profit: z.number(),
  quantity_sold: z.number(),
});

export const ShowTimeSuggestionSchema = z.object({
  day: z.string(),
  hour: z.number(),
  score: z.number(),
  avg_revenue: z.number(),
  avg_profit: z.number(),
  avg_orders: z.number(),
  show_count: z.number(),
});

export const ShowTimeSuggestionsResponseSchema = z.object({
  recommendations: z.array(ShowTimeSuggestionSchema),
  avoid_slots: z.array(ShowTimeSuggestionSchema),
  category_insights: z.array(
    z.object({
      category: z.string(),
      best_day: z.string(),
      best_hour: z.number(),
      avg_profit: z.number(),
    })
  ),
});

export const ExportJobSchema = z.object({
  id: z.string(),
  report_type: z.string(),
  format: z.enum(["csv", "pdf"]),
  period: z.string(),
  status: z.enum(["pending", "processing", "completed", "failed"]),
  file_path: z.string().nullable(),
  file_size: z.number().nullable(),
  error_message: z.string().nullable(),
  expires_at: z.string().nullable(),
  created_at: z.string(),
});

export const CreateExportSchema = z.object({
  report_type: z.enum(["summary", "categories", "shows", "trends", "top_items", "full"]),
  format: z.enum(["csv", "pdf"]),
  period: z.string().default("30d"),
});

// Team schemas
export const TeamMemberSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string(),
  role: z.enum(["owner", "admin", "member"]),
  is_verified: z.boolean(),
  is_active: z.boolean(),
  created_at: z.string(),
});

export const InviteMemberSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  role: z.enum(["admin", "member"]),
});

export const UpdateProfileSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").optional(),
  email: z.string().email("Enter a valid email address").optional(),
});

export const ChangePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Current password is required"),
    new_password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

// Type exports
export type User = z.infer<typeof UserSchema>;
export type Account = z.infer<typeof AccountSchema>;
export type LoginRequest = z.infer<typeof LoginRequestSchema>;
export type RegisterRequest = z.infer<typeof RegisterRequestSchema>;
export type Item = z.infer<typeof ItemSchema>;
export type CreateItem = z.infer<typeof CreateItemSchema>;
export type Category = z.infer<typeof CategorySchema>;
export type Show = z.infer<typeof ShowSchema>;
export type CreateShow = z.infer<typeof CreateShowSchema>;
export type Order = z.infer<typeof OrderSchema>;
export type CreateOrder = z.infer<typeof CreateOrderSchema>;
export type Shipment = z.infer<typeof ShipmentSchema>;
export type CreateShipment = z.infer<typeof CreateShipmentSchema>;
export type AnalyticsSummary = z.infer<typeof AnalyticsSummarySchema>;
export type TrendPoint = z.infer<typeof TrendPointSchema>;
export type CategoryAnalytics = z.infer<typeof CategoryAnalyticsSchema>;
export type TopItem = z.infer<typeof TopItemSchema>;
export type ShowTimeSuggestion = z.infer<typeof ShowTimeSuggestionSchema>;
export type ExportJob = z.infer<typeof ExportJobSchema>;
export type CreateExport = z.infer<typeof CreateExportSchema>;
export type TeamMember = z.infer<typeof TeamMemberSchema>;
