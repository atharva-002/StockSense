import { useEffect, useState } from "react";
import { endpoints } from "@/lib/api";
import { fmtNumber, fmtPct, statusTone } from "@/lib/format";
import KpiCard from "@/components/stocksense/KpiCard";
import { CardSkeleton, ChartSkeleton } from "@/components/stocksense/Skeletons";
import StatusBadge from "@/components/stocksense/StatusBadge";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  ComposedChart,
} from "recharts";

const CHART_COLORS = {
  actual: "#4F46E5",
  forecast: "#818CF8",
  interval: "#C7D2FE",
  baseline: "#9CA3AF",
};

export default function OverviewPage() {
  const [eda, setEda] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [drift, setDrift] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      endpoints.eda(),
      endpoints.models(),
      endpoints.drift(),
      endpoints.inventoryAlerts(7, 0.95),
    ])
      .then(([e, m, d, a]) => {
        setEda(e.data);
        setMetrics(m.data);
        setDrift(d.data);
        setAlerts(a.data);
      })
      .finally(() => setLoading(false));
  }, []);

  const kpi = {
    bestModel: metrics?.best_model || "–",
    improvement: metrics?.improvement_over_naive_pct,
    nStores: eda?.n_stores,
    nItems: eda?.n_items,
    activeAlerts: (alerts?.alerts || []).filter((r) => r.stockout_risk === "high").length,
    driftStatus: drift?.overall_status || "OK",
  };

  const monthly = (eda?.monthly_trend || []).map((r) => ({ ...r }));
  const weekly = eda?.weekly_seasonality || [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-heading tracking-tight font-bold text-gray-900">
          Demand Overview
        </h1>
        <p className="text-sm text-gray-600 mt-2 max-w-2xl">
          End-to-end demand forecasting and inventory monitoring across every store–item pair,
          powered by LightGBM, SHAP explainability and continuous drift monitoring.
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
          <KpiCard
            label="Best model"
            value={kpi.bestModel}
            hint="winner of CV + hold-out"
            tone="indigo"
            testId="kpi-best-model"
          />
          <KpiCard
            label="MAPE vs naive"
            value={fmtPct(kpi.improvement)}
            hint="improvement over seasonal naive"
            tone="emerald"
            testId="kpi-improvement"
          />
          <KpiCard
            label="Coverage"
            value={`${kpi.nStores} × ${kpi.nItems}`}
            hint="stores × items"
            tone="gray"
            testId="kpi-coverage"
          />
          <KpiCard
            label="Stock-out alerts"
            value={kpi.activeAlerts}
            hint="high-risk series"
            tone={kpi.activeAlerts > 0 ? "rose" : "emerald"}
            testId="kpi-alerts"
          />
          <KpiCard
            label="Drift status"
            value={kpi.driftStatus}
            hint={drift?.retrain_recommended ? "retrain recommended" : "model healthy"}
            tone={
              kpi.driftStatus === "OK"
                ? "emerald"
                : kpi.driftStatus === "WARNING"
                ? "amber"
                : "rose"
            }
            testId="kpi-drift"
          />
        </div>
      )}

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-heading font-semibold text-gray-900">
              Monthly sales trend
            </h2>
            <StatusBadge tone="indigo">2013 – 2017</StatusBadge>
          </div>
          {loading ? (
            <ChartSkeleton />
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={monthly} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="salesG" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={CHART_COLORS.actual} stopOpacity={0.35} />
                    <stop offset="95%" stopColor={CHART_COLORS.actual} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="period" tick={{ fontSize: 11, fill: "#6B7280" }} />
                <YAxis tick={{ fontSize: 11, fill: "#6B7280" }} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, borderColor: "#E5E7EB", fontSize: 12 }}
                />
                <Area type="monotone" dataKey="sales" stroke="none" fill="url(#salesG)" />
                <Line
                  type="monotone"
                  dataKey="sales"
                  stroke={CHART_COLORS.actual}
                  strokeWidth={2.5}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-heading font-semibold text-gray-900 mb-4">
            Weekly seasonality
          </h2>
          {loading ? (
            <ChartSkeleton height={320} />
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={weekly} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#6B7280" }} />
                <YAxis tick={{ fontSize: 11, fill: "#6B7280" }} />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#E5E7EB", fontSize: 12 }} />
                <Bar dataKey="avg_sales" fill={CHART_COLORS.actual} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-heading font-semibold text-gray-900 mb-4">
            Yearly seasonality
          </h2>
          {loading ? (
            <ChartSkeleton height={260} />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={eda?.yearly_seasonality || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#6B7280" }} />
                <YAxis tick={{ fontSize: 11, fill: "#6B7280" }} />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#E5E7EB", fontSize: 12 }} />
                <Line
                  type="monotone"
                  dataKey="avg_sales"
                  stroke={CHART_COLORS.forecast}
                  strokeWidth={2.5}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-heading font-semibold text-gray-900 mb-4">
            Top stock-out alerts
          </h2>
          {loading ? (
            <ChartSkeleton height={260} />
          ) : (alerts?.alerts || []).length === 0 ? (
            <p className="text-sm text-gray-500">No alerts right now.</p>
          ) : (
            <ul className="divide-y divide-gray-100" data-testid="overview-alerts-list">
              {(alerts.alerts || []).slice(0, 6).map((a, i) => (
                <li
                  key={`${a.store}-${a.item}-${i}`}
                  className="py-3 flex items-center justify-between"
                >
                  <div className="text-sm">
                    <span className="font-medium text-gray-800">
                      Store {a.store} · Item {a.item}
                    </span>
                    <span className="text-gray-500 ml-2 text-xs">
                      ROP {fmtNumber(a.reorder_point)} · Safety {fmtNumber(a.safety_stock)}
                    </span>
                  </div>
                  <StatusBadge tone={statusTone(a.stockout_risk)}>{a.stockout_risk}</StatusBadge>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
