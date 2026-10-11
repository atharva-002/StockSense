import { cn } from "@/lib/utils";

const TONE = {
  ok: "bg-emerald-50 text-emerald-800 border-emerald-200",
  warning: "bg-amber-50 text-amber-800 border-amber-200",
  drift: "bg-rose-50 text-rose-800 border-rose-200",
  neutral: "bg-gray-50 text-gray-700 border-gray-200",
  indigo: "bg-indigo-50 text-indigo-700 border-indigo-200",
};

export default function StatusBadge({ tone = "neutral", children, className, ...props }) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
        TONE[tone] || TONE.neutral,
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
