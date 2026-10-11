import { useEffect, useMemo, useState } from "react";
import { endpoints } from "@/lib/api";
import { fmtNumber } from "@/lib/format";
import { ChartSkeleton } from "@/components/stocksense/Skeletons";
import StatusBadge from "@/components/stocksense/StatusBadge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  BarChart,
  Bar,
  Cell,
} from "recharts";

const CHART = {
  actual: "#4F46E5",
  forecast: "#818CF8",
  interval: "#C7D2FE",
};

export default function ForecastPage() {
  const [catalog, setCatalog] = useState(null);
  const [store, setStore] = useState(1);
  const [item, setItem] = useState(1);
  const [data, setData] = useState(null);
  const [explain, setExplain] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    endpoints.catalog().then((r) => setCatalog(r.data));
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([endpoints.forecast(store, item, 28), endpoints.explain(store, item)])
      .then(([f, e]) => {
        setData(f.data);
        setExplain(e.data);
      })
      .finally(() => setLoading(false));
  }, [store, item]);

  const chartData = useMemo(() => {
    if (!data) return [];
    const hist = data.history_dates.map((d, i) => ({
      date: d,
      actual: data.history_sales[i],
    }));
    const forecast = data.forecast_dates.map((d, i) => ({
      date: d,
      forecast: data.forecast_mean[i],
      lower: data.forecast_lower[i],
      upper: data.forecast_upper[i],
      intervalBand: [data.forecast_lower[i], data.forecast_upper[i]],
    }));
    return [...hist, ...forecast];
  }, [data]);

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h1 className="text-4xl font-heading tracking-tight font-bold text-gray-900">
            28-day Forecast
          </h1>
          <p className="text-sm text-gray-600 mt-2 max-w-2xl">
            History + horizon forecast with 80% prediction interval (LightGBM quantile 0.1 / 0.9).
            Pick a store-item pair below.
          </p>
        </div>
        <div className="flex gap-3">
          <Select value={String(store)} onValueChange={(v) => setStore(Number(v))}>
            <SelectTrigger className="w-28" data-testid="forecast-store-select">
              <SelectValue placeholder="Store" />
            </SelectTrigger>
            <SelectContent>
              {(catalog?.stores || []).map((s) => (
                <SelectItem key={s} value={String(s)} data-testid={`store-opt-${s}`}>
                  Store {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={String(item)} onValueChange={(v) => setItem(Number(v))}>
            <SelectTrigger className="w-28" data-testid="forecast-item-select">
              <SelectValue placeholder="Item" />
            </SelectTrigger>
            <SelectContent>
              {(catalog?.items || []).map((i) => (
                <SelectItem key={i} value={String(i)} data-testid={`item-opt-${i}`}>
                  Item {i}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-heading font-semibold text-gray-900">
            Store {store} · Item {item}
          </h2>
          <div className="flex items-center gap-2">
            <StatusBadge tone="indigo">LightGBM quantile</StatusBadge>
            <StatusBadge tone="neutral">v{data?.model_version || "–"}</StatusBadge>
          </div>
        </div>
        {loading ? (
          <ChartSkeleton height={420} />
        ) : (
          <ResponsiveContainer width="100%" height={420}>
            <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "#6B7280" }}
                tickFormatter={(d) => d.slice(5)}
                minTickGap={40}
              />
              <YAxis tick={{ fontSize: 11, fill: "#6B7280" }} />
              <Tooltip
                contentStyle={{ borderRadius: 8, borderColor: "#E5E7EB", fontSize: 12 }}
                formatter={(v, k) => {
                  if (k === "intervalBand") return [v, "80% interval"];
                  return [fmtNumber(v, 2), k];
                }}
              />
              <Area
                type="monotone"
                dataKey="intervalBand"
                stroke="none"
                fill={CHART.interval}
                fillOpacity={0.6}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="actual"
                stroke={CHART.actual}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="forecast"
                stroke={CHART.forecast}
                strokeWidth={2.5}
                strokeDasharray="5 4"
                dot={false}
                connectNulls
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
        <div className="flex items-center gap-4 text-xs text-gray-600 mt-4">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-indigo-600 rounded" /> Actual
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 border-t-2 border-dashed border-indigo-400" /> Forecast
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-2.5 bg-indigo-200 rounded" /> 80% interval
          </span>
        </div>
      </section>

      <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-heading font-semibold text-gray-900">
              Top drivers for this series
            </h2>
            <p className="text-xs text-gray-500 mt-1">
              SHAP-attributed feature contributions, computed offline during training.
            </p>
          </div>
        </div>
        {loading ? (
          <ChartSkeleton height={320} />
        ) : (explain?.local_drivers || []).length === 0 ? (
          <p className="text-sm text-gray-500">No per-series SHAP example available.</p>
        ) : (
          <ResponsiveContainer width="100%" height={360}>
            <BarChart
              data={(explain.local_drivers || []).slice(0, 10)}
              layout="vertical"
              margin={{ left: 12, right: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis type="number" tick={{ fontSize: 11, fill: "#6B7280" }} />
              <YAxis
                dataKey="feature"
                type="category"
                width={110}
                tick={{ fontSize: 11, fill: "#374151" }}
              />
              <Tooltip
                contentStyle={{ borderRadius: 8, borderColor: "#E5E7EB", fontSize: 12 }}
                formatter={(v) => [fmtNumber(v, 3), "SHAP"]}
              />
              <Bar dataKey="shap" radius={[0, 4, 4, 0]}>
                {(explain.local_drivers || []).slice(0, 10).map((d, i) => (
                  <Cell key={i} fill={d.shap >= 0 ? "#4F46E5" : "#F43F5E"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </section>
    </div>
  );
}
