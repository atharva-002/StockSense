import { NavLink, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { Menu, X, Activity } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Overview", testId: "nav-overview" },
  { to: "/forecast", label: "Forecast", testId: "nav-forecast" },
  { to: "/models", label: "Models", testId: "nav-models" },
  { to: "/inventory", label: "Inventory", testId: "nav-inventory" },
  { to: "/monitoring", label: "Monitoring", testId: "nav-monitoring" },
  { to: "/architecture", label: "Architecture", testId: "nav-architecture" },
];

export default function TopNav() {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  return (
    <header
      data-testid="top-nav"
      className="fixed top-0 inset-x-0 z-50 backdrop-blur-xl bg-white/85 border-b border-gray-200 shadow-sm"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <NavLink to="/" className="flex items-center gap-2" data-testid="brand-logo">
            <span className="w-9 h-9 rounded-lg bg-indigo-600 text-white flex items-center justify-center">
              <Activity className="w-5 h-5" />
            </span>
            <span className="font-heading font-semibold text-lg tracking-tight text-gray-900">
              StockSense
            </span>
            <span className="hidden md:inline-flex items-center ml-2 px-2 py-0.5 rounded-full text-[10px] font-medium border border-indigo-200 text-indigo-700 bg-indigo-50 uppercase tracking-wider">
              MLOps
            </span>
          </NavLink>

          <nav className="hidden md:flex items-center gap-6">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                data-testid={n.testId}
                className={({ isActive }) =>
                  cn(
                    "text-sm py-5 border-b-2 transition-colors",
                    isActive
                      ? "border-indigo-600 text-indigo-700 font-medium"
                      : "border-transparent text-gray-600 hover:text-gray-900"
                  )
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>

          <button
            type="button"
            className="md:hidden p-2 rounded-md text-gray-600 hover:bg-gray-100"
            onClick={() => setOpen(!open)}
            data-testid="mobile-menu-toggle"
            aria-label="Toggle menu"
          >
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {open && (
          <div className="md:hidden pb-4 space-y-1" data-testid="mobile-menu">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                data-testid={`${n.testId}-mobile`}
                className={({ isActive }) =>
                  cn(
                    "block px-3 py-2 rounded-md text-sm",
                    isActive
                      ? "bg-indigo-50 text-indigo-700 font-medium"
                      : "text-gray-700 hover:bg-gray-50"
                  )
                }
              >
                {n.label}
              </NavLink>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}
