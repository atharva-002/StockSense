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

export default function MonitoringPage() {
  const [drift, setDrift] = useState(null);
  const [card, setCard] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([endpoints.drift(), endpoints.modelCard()])
      .then(([d, c]) => {
        setDrift(d.data);
        setCard(c.data);
      })
      .finally(() => setLoading(false));
  }, []);

  const toneFor = (s) => (s === "OK" ? "ok" : s === "WARNING" ? "warning" : "drift");

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-heading tracking-tight font-bold text-gray-900">
          Drift Monitoring & Model Card
        </h1>
        <p className="text-sm text-gray-600 mt-2 max-w-2xl">
          Per-feature PSI + KS tests against the training distribution, plus a model card for
          auditability.
        </p>
      </div>

      <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <h2 className="text-lg font-heading font-semibold text-gray-900">
            Drift report
          </h2>
          {drift && (
            <div className="flex items-center gap-2">
              <StatusBadge tone={toneFor(drift.overall_status)} data-testid="drift-overall-badge">
                overall · {drift.overall_status}
              </StatusBadge>
              {drift.retrain_recommended && (
                <StatusBadge tone="drift">retrain recommended</StatusBadge>
              )}
            </div>
          )}
        </div>
        {loading ? (
          <ChartSkeleton height={300} />
        ) : (
          <>
            <p className="text-sm text-gray-600 mb-4">{drift?.recommendation}</p>
            <div className="overflow-x-auto">
              <Table data-testid="drift-table">
                <TableHeader>
                  <TableRow>
                    <TableHead>Feature</TableHead>
                    <TableHead className="text-right">PSI</TableHead>
                    <TableHead>PSI status</TableHead>
                    <TableHead className="text-right">KS stat</TableHead>
                    <TableHead className="text-right">KS p-value</TableHead>
                    <TableHead>KS status</TableHead>
                    <TableHead>Overall</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(drift?.features || []).map((f) => (
                    <TableRow key={f.feature}>
                      <TableCell className="font-mono text-xs">{f.feature}</TableCell>
                      <TableCell className="text-right">{fmtNumber(f.psi, 3)}</TableCell>
                      <TableCell>
                        <StatusBadge tone={toneFor(f.psi_status)}>{f.psi_status}</StatusBadge>
                      </TableCell>
                      <TableCell className="text-right">{fmtNumber(f.ks_stat, 3)}</TableCell>
                      <TableCell className="text-right">{fmtNumber(f.ks_pvalue, 3)}</TableCell>
                      <TableCell>
                        <StatusBadge tone={toneFor(f.ks_status)}>{f.ks_status}</StatusBadge>
                      </TableCell>
                      <TableCell>
                        <StatusBadge tone={toneFor(f.status)}>{f.status}</StatusBadge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </>
        )}
      </section>

      <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-heading font-semibold text-gray-900 mb-4">Model card</h2>
        {loading || !card ? (
          <ChartSkeleton height={180} />
        ) : (
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-y-4 gap-x-8 text-sm">
            <div>
              <dt className="text-[10px] tracking-wider uppercase font-semibold text-gray-500">
                Name
              </dt>
              <dd className="mt-1 text-gray-800">{card.name}</dd>
            </div>
            <div>
              <dt className="text-[10px] tracking-wider uppercase font-semibold text-gray-500">
                Version
              </dt>
              <dd className="mt-1 font-mono text-xs text-gray-800">{card.version}</dd>
            </div>
            <div>
              <dt className="text-[10px] tracking-wider uppercase font-semibold text-gray-500">
                Task
              </dt>
              <dd className="mt-1 text-gray-800">{card.task}</dd>
            </div>
            <div>
              <dt className="text-[10px] tracking-wider uppercase font-semibold text-gray-500">
                Architecture
              </dt>
              <dd className="mt-1 text-gray-800">{card.architecture}</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="text-[10px] tracking-wider uppercase font-semibold text-gray-500">
                Training data
              </dt>
              <dd className="mt-1 text-gray-800">{card.training_data}</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="text-[10px] tracking-wider uppercase font-semibold text-gray-500">
                Test metrics
              </dt>
              <dd className="mt-1 text-gray-800">
                MAPE {fmtNumber(card.metrics?.test_mape)}% · RMSE {fmtNumber(card.metrics?.test_rmse)} ·
                MAE {fmtNumber(card.metrics?.test_mae)}
              </dd>
            </div>
            <div className="md:col-span-2">
              <dt className="text-[10px] tracking-wider uppercase font-semibold text-gray-500">
                Limitations
              </dt>
              <dd className="mt-1 text-gray-800 list-disc">
                <ul className="list-disc list-inside space-y-1">
                  {(card.limitations || []).map((l, i) => (
                    <li key={i}>{l}</li>
                  ))}
                </ul>
              </dd>
            </div>
            <div className="md:col-span-2">
              <dt className="text-[10px] tracking-wider uppercase font-semibold text-gray-500">
                Features used
              </dt>
              <dd className="mt-2 flex flex-wrap gap-2">
                {(card.features || []).map((f) => (
                  <StatusBadge tone="indigo" key={f}>
                    {f}
                  </StatusBadge>
                ))}
              </dd>
            </div>
          </dl>
        )}
      </section>
    </div>
  );
}
