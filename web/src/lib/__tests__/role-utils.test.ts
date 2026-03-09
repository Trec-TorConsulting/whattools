import { describe, it, expect } from "vitest";
import { isAtLeast, canAccessSales, canAccessShipping, canAccessAnalytics, canManageTeam, canChangeRoles, canManageAccount } from "@/lib/role-utils";

describe("isAtLeast", () => {
  it("owner is at least any role", () => {
    expect(isAtLeast("owner", "owner")).toBe(true);
    expect(isAtLeast("owner", "admin")).toBe(true);
    expect(isAtLeast("owner", "member")).toBe(true);
  });

  it("admin is at least admin and member", () => {
    expect(isAtLeast("admin", "admin")).toBe(true);
    expect(isAtLeast("admin", "member")).toBe(true);
    expect(isAtLeast("admin", "owner")).toBe(false);
  });

  it("member is only at least member", () => {
    expect(isAtLeast("member", "member")).toBe(true);
    expect(isAtLeast("member", "admin")).toBe(false);
    expect(isAtLeast("member", "owner")).toBe(false);
  });
});

describe("permission helpers", () => {
  it("canAccessSales requires admin+", () => {
    expect(canAccessSales("owner")).toBe(true);
    expect(canAccessSales("admin")).toBe(true);
    expect(canAccessSales("member")).toBe(false);
  });

  it("canAccessShipping requires admin+", () => {
    expect(canAccessShipping("owner")).toBe(true);
    expect(canAccessShipping("admin")).toBe(true);
    expect(canAccessShipping("member")).toBe(false);
  });

  it("canAccessAnalytics requires admin+", () => {
    expect(canAccessAnalytics("owner")).toBe(true);
    expect(canAccessAnalytics("admin")).toBe(true);
    expect(canAccessAnalytics("member")).toBe(false);
  });

  it("canManageTeam requires admin+", () => {
    expect(canManageTeam("owner")).toBe(true);
    expect(canManageTeam("admin")).toBe(true);
    expect(canManageTeam("member")).toBe(false);
  });

  it("canChangeRoles requires owner", () => {
    expect(canChangeRoles("owner")).toBe(true);
    expect(canChangeRoles("admin")).toBe(false);
    expect(canChangeRoles("member")).toBe(false);
  });

  it("canManageAccount requires owner", () => {
    expect(canManageAccount("owner")).toBe(true);
    expect(canManageAccount("admin")).toBe(false);
    expect(canManageAccount("member")).toBe(false);
  });
});
