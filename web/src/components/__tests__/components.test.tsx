import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { StatCard } from "@/components/stat-card";
import { PageHeader } from "@/components/page-header";
import { Package } from "lucide-react";

describe("Badge", () => {
  it("renders with default variant", () => {
    render(<Badge>Test</Badge>);
    expect(screen.getByText("Test")).toBeInTheDocument();
  });

  it("renders with success variant", () => {
    render(<Badge variant="success">Active</Badge>);
    const badge = screen.getByText("Active");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("bg-success");
  });

  it("renders with destructive variant", () => {
    render(<Badge variant="destructive">Error</Badge>);
    expect(screen.getByText("Error")).toBeInTheDocument();
  });
});

describe("StatusBadge", () => {
  it("renders known statuses with correct labels", () => {
    render(<StatusBadge status="available" />);
    expect(screen.getByText("Available")).toBeInTheDocument();
  });

  it("renders shipped status", () => {
    render(<StatusBadge status="shipped" />);
    expect(screen.getByText("Shipped")).toBeInTheDocument();
  });

  it("handles label_created status", () => {
    render(<StatusBadge status="label_created" />);
    expect(screen.getByText("Label Created")).toBeInTheDocument();
  });

  it("capitalizes unknown statuses", () => {
    render(<StatusBadge status="custom_status" />);
    expect(screen.getByText("Custom_status")).toBeInTheDocument();
  });
});

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(<EmptyState title="No items" description="Add your first item" />);
    expect(screen.getByText("No items")).toBeInTheDocument();
    expect(screen.getByText("Add your first item")).toBeInTheDocument();
  });

  it("renders action button when provided", () => {
    render(
      <EmptyState
        title="No items"
        description="Start adding"
        action={{ label: "Add Item", onClick: () => {} }}
      />
    );
    expect(screen.getByRole("button", { name: "Add Item" })).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    render(<EmptyState icon={Package} title="No items" description="None" />);
    expect(screen.getByText("No items")).toBeInTheDocument();
  });
});

describe("StatCard", () => {
  it("renders title and value", () => {
    render(<StatCard title="Revenue" value="$5,000" icon={Package} />);
    expect(screen.getByText("Revenue")).toBeInTheDocument();
    expect(screen.getByText("$5,000")).toBeInTheDocument();
  });
});

describe("PageHeader", () => {
  it("renders title", () => {
    render(<PageHeader title="Inventory" />);
    expect(screen.getByText("Inventory")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(<PageHeader title="Items" description="Manage your items" />);
    expect(screen.getByText("Manage your items")).toBeInTheDocument();
  });

  it("renders action when provided", () => {
    render(<PageHeader title="Items" actions={<button>Add</button>} />);
    expect(screen.getByRole("button", { name: "Add" })).toBeInTheDocument();
  });
});
