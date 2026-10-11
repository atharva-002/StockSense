import { useEffect, useState } from "react";
import { endpoints } from "@/lib/api";
import { fmtNumber } from "@/lib/format";
import { ChartSkeleton } from "@/components/stocksense/Skeletons";
import StatusBadge from "@/components/stocksense/StatusBadge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  BarChart,
  Bar,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function ModelsPage() {
  const [metrics, setMetrics] = useState(null);
  const [experiments, setExperiments] = useState(null);
  const [shap, setShap] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      endpoints.models(),
      endpoints.experiments(),
      endpoints.explain(1, 1),
    ])
      .then(([m, e, s]) => {
        setMetrics(m.data);
        setExperiments(e.data);
        setShap(s.data);
      })
      .finally(() => setLoading(false));
  }, []);

  const comp = metrics?.comparison || [];
  const cv = metrics?.cv_folds || [];
  const byStore = metrics?.error_by_store || [];
  const byItem = metrics?.error_by_item || [];
  const globalImp = shap?.global_importance || [];
  const runs = experiments?.runs || [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-heading tracking-tight font-bold text-gray-900">
          Model Comparison & Experiments
        </h1>
        <p className="text-sm text-gray-600 mt-2 max-w-2xl">
          Expanding-window cross-validation + hold-out test. Winner is logged and
          registered in MLflow.
        </p>
      </div>

      <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-heading font-semibold text-gray-900">
            Hold-out test comparison
          </h2>
          <StatusBadge tone="indigo">best: {metrics?.best_model || "–"}</StatusBadge>
        </div>
        {loading ? (
          <ChartSkeleton height={160} />
        ) : (
          <Table data-testid="models-comparison-table">
            <TableHeader>
              <TableRow>
                <TableHead>Model</TableHead>
                <TableHead className="text-right">MAPE %</TableHead>
                <TableHead className="text-right">sMAPE %</TableHead>
                <TableHead className="text-right">RMSE</TableHead>
                <TableHead className="text-right">MAE</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {comp.map((r) => (
                <TableRow key={r.model} data-testid={`model-row-${r.model}`}>
                  <TableCell className="font-medium">
                    {r.model === metrics?.best_model ? (
                      <span className="text-indigo-700">{r.model} ★</span>
                    ) : (
                      r.model
                    )}
                  </TableCell>
                  <TableCell className="text-right">{fmtNumber(r.mape)}</TableCell>
                  <TableCell className="text-right">{fmtNumber(r.smape)}</TableCell>
                  <TableCell className="text-right">{fmtNumber(r.rmse)}</TableCell>
                  <TableCell className="text-right">{fmtNumber(r.mae)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </section>

      <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-heading font-semibold text-gray-900 mb-4">
          Cross-validation folds (expanding window)
        </h2>
        {loading ? (
          <ChartSkeleton height={200} />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fold</TableHead>
                  <TableHead>Train end</TableHead>
                  <TableHead>Val range</TableHead>
                  <TableHead className="text-right">Naive MAPE</TableHead>
                  <TableHead className="text-right">Ridge MAPE</TableHead>
                  <TableHead className="text-right">LightGBM MAPE</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {cv.map((f) => (
                  <TableRow key={f.fold}>
                    <TableCell>#{f.fold}</TableCell>
                    <TableCell className="text-xs">{f.train_end}</TableCell>
                    <TableCell className="text-xs text-gray-600">
                      {f.val_start} → {f.val_end}
                    </TableCell>
                    <TableCell className="text-right">{fmtNumber(f.naive.mape)}</TableCell>
                    <TableCell className="text-right">{fmtNumber(f.linear.mape)}</TableCell>
                    <TableCell className="text-right font-medium text-indigo-700">
                      {fmtNumber(f.lightgbm.mape)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-heading font-semibold text-gray-900 mb-4">
            Global feature importance (SHAP)
          </h2>
          {loading ? (
            <ChartSkeleton height={320} />
          ) : (
            <ResponsiveContainer width="100%" height={360}>
              <BarChart
                data={globalImp.slice(0, 12)}
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
                />
                <Bar dataKey="importance" fill="#4F46E5" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-heading font-semibold text-gray-900 mb-4">
            Error by store
          </h2>
          {loading ? (
            <ChartSkeleton height={320} />
          ) : (
            <ResponsiveContainer width="100%" height={360}>
              <BarChart data={byStore} margin={{ left: 0, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis
                  dataKey="key"
                  tick={{ fontSize: 11, fill: "#6B7280" }}
                  tickFormatter={(k) => `S${k}`}
                />
                <YAxis tick={{ fontSize: 11, fill: "#6B7280" }} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, borderColor: "#E5E7EB", fontSize: 12 }}
                />
                <Bar dataKey="mape" fill="#818CF8" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>

      <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-heading font-semibold text-gray-900 mb-4">
          MLflow experiment history
        </h2>
        {loading ? (
          <ChartSkeleton height={120} />
        ) : runs.length === 0 ? (
          <p className="text-sm text-gray-500">No MLflow runs recorded yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Run</TableHead>
                <TableHead>Model version</TableHead>
                <TableHead>Best</TableHead>
                <TableHead className="text-right">LightGBM MAPE</TableHead>
                <TableHead className="text-right">Naive MAPE</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.map((r) => (
                <TableRow key={r.run_id}>
                  <TableCell className="font-mono text-xs">
                    {r.run_name || r.run_id?.slice(0, 8)}
                  </TableCell>
                  <TableCell className="text-xs">{r.model_version}</TableCell>
                  <TableCell>
                    <StatusBadge tone="indigo">{r.best_model}</StatusBadge>
                  </TableCell>
                  <TableCell className="text-right">
                    {fmtNumber(r.metrics?.lightgbm_mape)}
                  </TableCell>
                  <TableCell className="text-right">
                    {fmtNumber(r.metrics?.seasonal_naive_mape)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </section>
    </div>
  );
}
