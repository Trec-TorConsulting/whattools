import { Link, Outlet, useLocation } from "react-router";
import { User, Users, Building } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { canManageTeam } from "@/lib/role-utils";
import { PageHeader } from "@/components/page-header";

const TABS = [
  { label: "Profile", href: "/settings", icon: User },
  { label: "Team", href: "/settings/team", icon: Users, minRole: "admin" as const },
  { label: "Account", href: "/settings/account", icon: Building, minRole: "owner" as const },
];

export function SettingsLayout() {
  const { user } = useAuth();
  const location = useLocation();

  const visibleTabs = TABS.filter((tab) => {
    if (!tab.minRole) return true;
    if (tab.minRole === "admin") return user ? canManageTeam(user.role) : false;
    return user?.role === "owner";
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Manage your account and preferences" />

      <div className="flex gap-6">
        {/* Side navigation */}
        <nav className="hidden w-48 shrink-0 space-y-1 lg:block">
          {visibleTabs.map((tab) => {
            const isActive = location.pathname === tab.href;
            return (
              <Link
                key={tab.href}
                to={tab.href}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </Link>
            );
          })}
        </nav>

        {/* Mobile tabs */}
        <div className="flex w-full flex-col gap-6">
          <div className="flex gap-2 border-b lg:hidden">
            {visibleTabs.map((tab) => {
              const isActive = location.pathname === tab.href;
              return (
                <Link
                  key={tab.href}
                  to={tab.href}
                  className={cn(
                    "flex items-center gap-1.5 border-b-2 px-3 pb-2 text-sm font-medium transition-colors",
                    isActive
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  )}
                >
                  <tab.icon className="h-4 w-4" />
                  {tab.label}
                </Link>
              );
            })}
          </div>
          <div className="flex-1">
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  );
}
