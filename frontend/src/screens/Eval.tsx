import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { EmptyState, ErrorBanner, Spinner } from "../components/ui";

const TARGETS: [string, string, number, boolean][] = [
  ["high_risk_precision", "High-risk precision", 0.85, true], ["high_risk_recall", "High-risk recall", 0.75, true],
  ["high_risk_f1", "High-risk F1", 0, true], ["detection_recall", "Claim detection recall", 0.9, true],
  ["non_claim_fp_rate", "Non-claim false positives", 0.1, false], ["citation_accuracy", "Citation accuracy", 0.9, true],
  ["hallucinated_quote_rate_after_guard", "Hallucinated quotes (after guard)", 0, false], ["latency_p95_s", "Latency p95 (s)", 20, false],
];

export default function EvalScreen() {
  const runs = useQuery({ queryKey: ["evalruns"], queryFn: api.evalRuns });
  if (runs.isLoading) return <Spinner />;
  if (runs.isError) return <ErrorBanner>{(runs.error as Error).message}</ErrorBanner>;
  const list = runs.data ?? [];
  if (!list.length) return <EmptyState title="No evaluation runs yet.">Run <code>python -m claimguard.eval run --set holdout</code> from backend/.</EmptyState>;
  const latest = list.find((r) => r.set_name === "holdout" && r.config.ablate === "default") ?? list[0];
  const m = latest.metrics;
  const abl = list.filter((r) => r.set_name === latest.set_name).reduce<Record<string, { name: string; f1: number; recall: number; precision: number }>>((acc, r) => {
    acc[r.config.ablate] ??= { name: r.config.ablate === "default" ? "full system" : r.config.ablate === "rules" ? "rules only" : `no ${r.config.ablate}`,
      f1: Number(r.metrics.high_risk_f1 ?? 0), recall: Number(r.metrics.high_risk_recall ?? 0), precision: Number(r.metrics.high_risk_precision ?? 0) }; return acc; }, {});
  return <div className="space-y-4"><h1 className="text-xl font-bold">Evaluation</h1>
    <p className="text-sm text-muted">Measured on the <b>{latest.set_name}</b> set ({String(m.n_items)} items, never used for tuning). Honest numbers, including misses.
      {m.partial ? ` Partial run: ${m.partial} (${m.stopped}).` : ""}</p>
    <div className="grid gap-2" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(170px, 100%), 1fr))" }}>
      {TARGETS.map(([k, label, target, higher]) => { const v = m[k]; const num = typeof v === "number" ? v : null;
        const ok = num === null ? null : target === 0 && higher ? null : higher ? num >= target : num <= target;
        return <div key={k} className="card p-3"><div className="text-2xl font-bold font-mono">{num === null ? "n/a" : num}</div>
          <div className="text-xs text-muted">{label}</div>
          {target > 0 || !higher ? <div className={`text-xs font-semibold ${ok === null ? "text-muted" : ok ? "text-low-fg" : "text-high-fg"}`}>
            target {higher ? "≥" : "≤"} {target}{ok === null ? "" : ok ? " · met" : " · not met"}</div> : null}</div>; })}</div>
    {m.citation_accuracy === null && <p className="text-xs text-muted">Citation accuracy is n/a: the gold set does not yet list expected clause IDs for each item (needs a human labeller).</p>}
    <section className="card p-4"><div className="label mb-2">Ablations: high-risk F1 / recall / precision</div><div className="h-64"><ResponsiveContainer>
      <BarChart data={Object.values(abl)}><CartesianGrid strokeDasharray="3 3" stroke="var(--border)" /><XAxis dataKey="name" fontSize={12} /><YAxis domain={[0, 1]} fontSize={12} />
        <Tooltip /><Bar dataKey="f1" fill="#1F3A93" name="F1" /><Bar dataKey="recall" fill="#E0A040" name="Recall" /><Bar dataKey="precision" fill="#0F5A2F" name="Precision" /></BarChart>
    </ResponsiveContainer></div></section>
    <section className="card p-4 cq"><div className="label mb-2">Run history</div><table className="tbl tbl-cards"><thead><tr><th>Run</th><th>Set</th><th>Config</th><th>P</th><th>R</th><th>F1</th><th>p95 s</th><th>Tokens</th></tr></thead>
      <tbody>{list.map((r) => <tr key={r.id}><td data-l="Run">#{r.id} {r.created_at.slice(0, 16)}</td><td data-l="Set">{r.set_name}</td><td data-l="Config">{r.config.ablate}</td>
        <td data-l="P">{String(r.metrics.high_risk_precision)}</td><td data-l="R">{String(r.metrics.high_risk_recall)}</td><td data-l="F1">{String(r.metrics.high_risk_f1)}</td>
        <td data-l="p95 s">{String(r.metrics.latency_p95_s)}</td><td data-l="Tokens">{Number(r.metrics.tokens_in ?? 0) + Number(r.metrics.tokens_out ?? 0)}</td></tr>)}</tbody></table></section>
  </div>;
}
