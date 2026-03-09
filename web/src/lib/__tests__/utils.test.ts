import { describe, it, expect } from "vitest";
import {
  cn,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatRelative,
  capitalize,
  truncate,
} from "@/lib/utils";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("px-2", "py-1")).toBe("px-2 py-1");
  });

  it("handles tailwind conflicts", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("handles conditional classes", () => {
    expect(cn("base", false && "hidden", "extra")).toBe("base extra");
  });
});

describe("formatCurrency", () => {
  it("formats numbers as USD", () => {
    expect(formatCurrency(1234.5)).toBe("$1,234.50");
  });

  it("handles string input", () => {
    expect(formatCurrency("99.99")).toBe("$99.99");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });
});

describe("formatDate", () => {
  it("formats ISO strings", () => {
    expect(formatDate("2024-06-15T10:30:00Z")).toBe("Jun 15, 2024");
  });

  it("formats Date objects", () => {
    expect(formatDate(new Date(2024, 0, 1))).toBe("Jan 1, 2024");
  });
});

describe("formatDateTime", () => {
  it("formats date with time", () => {
    const result = formatDateTime("2024-06-15T10:30:00Z");
    expect(result).toContain("Jun 15, 2024");
    expect(result).toMatch(/\d{1,2}:\d{2}\s[AP]M/);
  });
});

describe("formatRelative", () => {
  it("returns a string with ago suffix", () => {
    const pastDate = new Date(Date.now() - 60000).toISOString();
    expect(formatRelative(pastDate)).toContain("ago");
  });
});

describe("capitalize", () => {
  it("capitalizes first letter", () => {
    expect(capitalize("hello")).toBe("Hello");
  });

  it("lowercases rest", () => {
    expect(capitalize("HELLO")).toBe("Hello");
  });
});

describe("truncate", () => {
  it("truncates long strings", () => {
    expect(truncate("hello world", 5)).toBe("hello…");
  });

  it("does not truncate short strings", () => {
    expect(truncate("hi", 10)).toBe("hi");
  });
});
