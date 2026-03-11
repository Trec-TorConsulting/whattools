import { Shield, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getImpersonationState, useImpersonation } from "../hooks/use-impersonation";

export function ImpersonationBanner() {
  const state = getImpersonationState();
  const { stopImpersonation } = useImpersonation();

  if (!state.isImpersonating || !state.impersonatedUser) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-[100] flex items-center justify-between bg-amber-500 px-4 py-2 text-amber-950 shadow-lg">
      <div className="flex items-center gap-2">
        <Shield className="h-4 w-4" />
        <span className="text-sm font-medium">
          Impersonating: {state.impersonatedUser.name || state.impersonatedUser.email}
        </span>
        <span className="text-xs opacity-75">({state.impersonatedUser.email})</span>
      </div>
      <Button
        variant="ghost"
        size="sm"
        className="h-7 gap-1 text-amber-950 hover:bg-amber-600 hover:text-amber-950"
        onClick={stopImpersonation}
      >
        <X className="h-3 w-3" /> End Session
      </Button>
    </div>
  );
}
