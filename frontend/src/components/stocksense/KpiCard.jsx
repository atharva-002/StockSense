import { cn } from "@/lib/utils";

export default function KpiCard({ label, value, hint, tone = "indigo", testId }) {
  const tones = {
    indigo: "text-indigo-700",
    emerald: "text-emerald-700",
    amber: "text-amber-700",
    rose: "text-rose-700",
    gray: "text-gray-900",
  };
  return (
    <div
      data-testid={testId}
      className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-200 p-6 flex flex-col gap-3"
    >
      <span className="text-[10px] tracking-wider uppercase font-semibold text-gray-500">
        {label}
      </span>
      <span className={cn("text-3xl font-heading font-semibold tracking-tight", tones[tone])}>
        {value}
      </span>
      {hint && <span className="text-xs text-gray-500">{hint}</span>}
    </div>
  );
}
