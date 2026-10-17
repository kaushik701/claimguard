import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, CLAIM_LABEL, SURFACES } from "../api/client";
import { EmptyState, ErrorBanner, Spinner, StatRow } from "../components/ui";

const RAMP = ["#FFF3E0", "#FFD8A8", "#FFB366", "#F08C2E", "#B34700"];
const TEXT = ["#3A1D00", "#3A1D00", "#3A1D00", "#3A1D00", "#FFFFFF"]; // >= 4.5:1 on each step

export default function PortfolioScreen() {
  const p = useQuery({ queryKey: ["portfolio"], queryFn: api.portfolio });
  if (p.isLoading) return <Spinner />;
  if (p.isError) return <ErrorBanner>{(p.error as Error).message}</ErrorBanner>;
  const d = p.data!;
  if (!d.heatmap.rows.length) return <EmptyState title="No flags yet.">Run a few audits (try the fictional samples) to see where risk sits.</EmptyState>;
  const top = Math.max(1, ...d.heatmap.rows.flatMap((r) => Object.values(r.counts)));
  const surf = Object.values(d.by_surface.reduce<Record<string, { surface: string; high: number; medium: number }>>((acc, x) => {
    const k = SURFACES[x.surface as keyof typeof SURFACES] ?? x.surface;
    acc[k] ??= { surface: k, high: 0, medium: 0 }; if (x.risk === "high" || x.risk === "medium") acc[k][x.risk] += x.count; return acc; }, {}));
  const total = d.by_surface.reduce((s, x) => s + x.count, 0);
  return <div className="space-y-4"><h1 className="text-xl font-bold">Portfolio</h1>
    <StatRow items={[{ label: "Flags", value: total }, { label: "Brands", value: d.heatmap.rows.length },
      { label: "High risk", value: d.by_surface.filter((x) => x.risk === "high").reduce((s, x) => s + x.count, 0), tone: "high" },
      { label: "Open", value: d.trend.reduce((s, x) => s + (x.open ?? 0), 0), tone: "medium" }]} />
    <section className="card p-4 cq"><div className="label mb-2">Flags by brand and claim type</div>
      <div className="overflow-x-auto"><table className="tbl"><thead><tr><th>Brand</th>{d.heatmap.types.map((t) => <th key={t}>{CLAIM_LABEL[t] ?? t}</th>)}</tr></thead>
        <tbody>{d.heatmap.rows.map((r) => <tr key={r.brand}><td className="font-semibold whitespace-nowrap">{r.brand}</td>
          {d.heatmap.types.map((t) => { const v = r.counts[t] ?? 0; const s = Math.min(4, Math.floor(((v * 5) - 1) / top));
            return <td key={t} className="text-center font-mono font-bold" style={v ? { background: RAMP[s], color: TEXT[s] } : {}}>{v || ""}</td>; })}</tr>)}</tbody></table></div></section>
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="card p-4"><div className="label mb-2">Flags by surface</div><div className="h-64"><ResponsiveContainer>
        <BarChart data={surf}><CartesianGrid strokeDasharray="3 3" stroke="var(--border)" /><XAxis dataKey="surface" fontSize={12} /><YAxis allowDecimals={false} fontSize={12} />
          <Tooltip /><Legend /><Bar dataKey="high" stackId="a" fill="#D92D20" name="High" /><Bar dataKey="medium" stackId="a" fill="#E0A040" name="Medium" /></BarChart></ResponsiveContainer></div></section>
      <section className="card p-4"><div className="label mb-2">Flags by regulator cited</div><div className="h-64"><ResponsiveContainer>
        <BarChart data={d.by_regulator} layout="vertical"><CartesianGrid strokeDasharray="3 3" stroke="var(--border)" /><XAxis type="number" allowDecimals={false} fontSize={12} />
          <YAxis type="category" dataKey="regulator" width={80} fontSize={12} /><Tooltip /><Bar dataKey="count" fill="#1F3A93" name="Citations" /></BarChart></ResponsiveContainer></div></section>
    </div>
    <section className="card p-4"><div className="label mb-2">Recurring risky phrasings</div>
      {d.phrasings.length ? <ul className="space-y-2">{d.phrasings.map((x) => <li key={x.phrase}><b className="font-mono">{x.count}×</b> {x.phrase}
        <div className="text-xs text-muted">{x.examples.slice(1).join(" · ")}</div></li>)}</ul> : <p className="text-sm text-muted">No repeated phrasing yet.</p>}</section>
  </div>;
}
