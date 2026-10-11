import { useEffect, useState, useMemo } from "react";
import { endpoints } from "@/lib/api";
import { fmtNumber, statusTone } from "@/lib/format";
import { CardSkeleton, ChartSkeleton } from "@/components/stocksense/Skeletons";
import KpiCard from "@/components/stocksense/KpiCard";
import StatusBadge from "@/components/stocksense/StatusBadge";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function InventoryPage() {
  const [catalog, setCatalog] = useState(null);
  const [store, setStore] = useState(1);
  const [item, setItem] = useState(1);
  const [leadTime, setLeadTime] = useState(7);
  const [serviceLevel, setServiceLevel] = useState(0.95);
  const [inv, setInv] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    endpoints.catalog().then((r) => setCatalog(r.data));
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      endpoints.inventory(store, item, leadTime, serviceLevel),
      endpoints.inventoryAlerts(leadTime, serviceLevel),
    ])
      .then(([a, b]) => {
        setInv(a.data);
        setAlerts(b.data);
      })
      .finally(() => setLoading(false));
  }, [store, item, leadTime, serviceLevel]);

  const sl = useMemo(() => Math.round(serviceLevel * 100), [serviceLevel]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-heading tracking-tight font-bold text-gray-900">
          Inventory Planner
        </h1>
        <p className="text-sm text-gray-600 mt-2 max-w-2xl">
          Convert the 28-day forecast + its intervals into safety stock, reorder points and
          order quantities. Tune lead time and service level to see the impact.
        </p>
      </div>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-5 lg:col-span-1">
          <div>
            <label className="text-[10px] tracking-wider uppercase font-semibold text-gray-500">
              Store
            </label>
            <Select value={String(store)} onValueChange={(v) => setStore(Number(v))}>
              <SelectTrigger className="mt-2" data-testid="inventory-store-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(catalog?.stores || []).map((s) => (
                  <SelectItem key={s} value={String(s)}>
                    Store {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-[10px] tracking-wider uppercase font-semibold text-gray-500">
              Item
            </label>
            <Select value={String(item)} onValueChange={(v) => setItem(Number(v))}>
              <SelectTrigger className="mt-2" data-testid="inventory-item-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(catalog?.items || []).map((i) => (
                  <SelectItem key={i} value={String(i)}>
                    Item {i}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <div className="flex justify-between items-center">
              <label className="text-[10px] tracking-wider uppercase font-semibold text-gray-500">
                Lead time (days)
              </label>
              <span className="text-sm font-medium text-indigo-700">{leadTime}</span>
            </div>
            <Slider
              className="mt-3"
              value={[leadTime]}
              onValueChange={(v) => setLeadTime(v[0])}
              min={1}
              max={30}
              step={1}
              data-testid="inventory-lead-time"
            />
          </div>
          <div>
            <div className="flex justify-between items-center">
              <label className="text-[10px] tracking-wider uppercase font-semibold text-gray-500">
                Service level
              </label>
              <span className="text-sm font-medium text-indigo-700">{sl}%</span>
            </div>
            <Slider
              className="mt-3"
              value={[serviceLevel]}
              onValueChange={(v) => setServiceLevel(v[0])}
              min={0.8}
              max={0.99}
              step={0.01}
              data-testid="inventory-service-level"
            />
          </div>
        </div>

        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-6">
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)
          ) : inv ? (
            <>
              <KpiCard
                label="Safety stock"
                value={fmtNumber(inv.safety_stock)}
                hint={`z = ${fmtNumber(inv.z, 3)}`}
                tone="indigo"
                testId="kpi-safety-stock"
              />
              <KpiCard
                label="Reorder point"
                value={fmtNumber(inv.reorder_point)}
                hint="trigger an order when stock ≤ this"
                tone="gray"
                testId="kpi-reorder-point"
              />
              <KpiCard
                label="Order quantity"
                value={fmtNumber(inv.order_quantity)}
                hint="(R, S) policy, review period 14d"
                tone="emerald"
                testId="kpi-order-quantity"
              />
              <KpiCard
                label="Stock-out risk"
                value={inv.stockout_risk?.toUpperCase() || "–"}
                hint={`μ = ${fmtNumber(inv.mean_daily_demand)} / day`}
                tone={
                  inv.stockout_risk === "high"
                    ? "rose"
                    : inv.stockout_risk === "medium"
                    ? "amber"
                    : "emerald"
                }
                testId="kpi-stockout-risk"
              />
            </>
          ) : null}
        </div>
      </section>

      <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-heading font-semibold text-gray-900">
            Top stock-out risk alerts
          </h2>
          <StatusBadge tone="indigo">
            lead {leadTime}d · SL {sl}%
          </StatusBadge>
        </div>
        {loading ? (
          <ChartSkeleton height={240} />
        ) : (
          <div className="overflow-x-auto">
            <Table data-testid="inventory-alerts-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Store</TableHead>
                  <TableHead>Item</TableHead>
                  <TableHead className="text-right">μ daily</TableHead>
                  <TableHead className="text-right">Safety</TableHead>
                  <TableHead className="text-right">Reorder</TableHead>
                  <TableHead className="text-right">Order Q</TableHead>
                  <TableHead>Risk</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(alerts?.alerts || []).map((r, i) => (
                  <TableRow key={`${r.store}-${r.item}-${i}`}>
                    <TableCell>Store {r.store}</TableCell>
                    <TableCell>Item {r.item}</TableCell>
                    <TableCell className="text-right">{fmtNumber(r.mean_daily_demand)}</TableCell>
                    <TableCell className="text-right">{fmtNumber(r.safety_stock)}</TableCell>
                    <TableCell className="text-right">{fmtNumber(r.reorder_point)}</TableCell>
                    <TableCell className="text-right">{fmtNumber(r.order_quantity)}</TableCell>
                    <TableCell>
                      <StatusBadge tone={statusTone(r.stockout_risk)}>
                        {r.stockout_risk}
                      </StatusBadge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>
    </div>
  );
}
