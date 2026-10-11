import { Inbox } from "lucide-react";

export default function EmptyState({
  title = "Nothing to display",
  description,
  icon: Icon = Inbox,
  action,
}) {
  return (
    <div
      data-testid="empty-state"
      className="flex flex-col items-center justify-center p-12 text-center rounded-xl border-2 border-dashed border-gray-200 bg-gray-50"
    >
      <Icon className="w-12 h-12 text-gray-400 mb-4" />
      <h3 className="text-base font-medium text-gray-800">{title}</h3>
      {description && <p className="text-sm text-gray-500 mt-1 max-w-md">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
