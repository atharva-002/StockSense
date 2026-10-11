import { useEffect, useState } from "react";
import { subscribeWakeUp, isWakingUp } from "@/lib/api";
import { Loader2 } from "lucide-react";

export default function WakeBanner() {
  const [visible, setVisible] = useState(isWakingUp());
  useEffect(() => subscribeWakeUp(setVisible), []);
  if (!visible) return null;
  return (
    <div
      data-testid="wake-banner"
      className="fixed top-16 inset-x-0 z-40 bg-amber-50 border-b border-amber-200 text-amber-900 text-sm py-2.5"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center gap-3">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Waking up the server, this can take up to a minute…</span>
      </div>
    </div>
  );
}
