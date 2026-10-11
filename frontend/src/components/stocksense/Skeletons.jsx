import { cn } from "@/lib/utils";

export function Skeleton({ className }) {
  return (
    <div
      className={cn("animate-pulse bg-gray-200 rounded-xl", className)}
      data-testid="skeleton"
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 flex flex-col gap-3">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-8 w-32" />
      <Skeleton className="h-3 w-16" />
    </div>
  );
}

export function ChartSkeleton({ height = 320 }) {
  return <Skeleton className="w-full rounded-xl" style={{ height }} />;
}
