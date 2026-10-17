import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, CLAIM_LABEL, SURFACES, type Citation, type Flag } from "../api/client";
import { EmptyState, ErrorBanner, FlagCard, PageViewer, RiskPill, Spinner, Toast, useKeys, useToast } from "../components/ui";

export default function ReviewScreen() {
  const [status, setStatus] = useState("open");
  const [risk, setRisk] = useState("");
  const [type, setType] = useState("");
  const [maxConf, setMaxConf] = useState("");
  const q = `?${new URLSearchParams(Object.entries({ status, risk, claim_type: type, max_conf: maxConf }).filter(([, v]) => v)).toString()}`;
  const flags = useQuery({ queryKey: ["flags", q], queryFn: () => api.flags(q) });
  const [sel, setSel] = useState(0);
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const [viewer, setViewer] = useState<Citation | null>(null);
  const [toast, setToast] = useToast();
  const qc = useQueryClient();
  const list = flags.data ?? [];
  async function act(ids: number[], action: string, extra?: Record<string, unknown>) {
    for (const id of ids) await api.patchFlag(id, { action, ...extra });
    setChecked(new Set()); await qc.invalidateQueries({ queryKey: ["flags"] });
    setToast(`${ids.length} flag${ids.length > 1 ? "s" : ""} ${action === "accept" ? "accepted" : action === "dismiss" ? "dismissed" : "updated"}`);
  }
  const keys = useMemo(() => ({
    j: () => setSel((s) => Math.min(list.length - 1, s + 1)), k: () => setSel((s) => Math.max(0, s - 1)),
    a: () => list[sel] && act([list[sel].id], "accept"), d: () => list[sel] && act([list[sel].id], "dismiss", { reason_code: "other" }),
    e: () => list[sel] && act([list[sel].id], "escalate"),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [list, sel]);
  useKeys(keys);
  const f: Flag | undefined = list[sel];
  return <div className="space-y-4">
    <h1 className="text-xl font-bold">Review queue</h1>
    <p className="text-sm text-muted">Every flag across audits, least confident first (the most useful to review). Your decisions teach the next audits.</p>
    <div className="grid gap-2" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(160px, 100%), 1fr))" }}>
      <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
        <option value="open">Open</option><option value="accepted">Accepted</option><option value="dismissed">Dismissed</option>
        <option value="escalated">Escalated</option><option value="">All</option></select>
      <select className="input" value={risk} onChange={(e) => setRisk(e.target.value)} aria-label="Risk">
        <option value="">Any risk</option><option value="high">High</option><option value="medium">Medium</option></select>
      <select className="input" value={type} onChange={(e) => setType(e.target.value)} aria-label="Claim type">
        <option value="">Any claim type</option>{Object.entries(CLAIM_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
      <select className="input" value={maxConf} onChange={(e) => setMaxConf(e.target.value)} aria-label="Confidence">
        <option value="">Any confidence</option><option value="0.5">Below 50%</option><option value="0.7">Below 70%</option></select>
    </div>
    {checked.size > 0 && <div className="flex gap-2"><button className="btn btn-primary" onClick={() => act([...checked], "accept")}>Accept {checked.size}</button>
      <button className="btn" onClick={() => act([...checked], "dismiss", { reason_code: "other" })}>Dismiss {checked.size}</button></div>}
    {flags.isLoading && <Spinner />}{flags.isError && <ErrorBanner>{(flags.error as Error).message}</ErrorBanner>}
    {flags.data && list.length === 0 && <EmptyState title="Nothing to review here.">Run an audit, or change the filters.</EmptyState>}
    {list.length > 0 && <div className="grid gap-4 lg:grid-cols-2">
      <div className="cq min-w-0"><table className="tbl tbl-cards"><thead><tr><th></th><th>Risk</th><th>Claim</th><th>Type</th><th>Where</th><th>Conf.</th></tr></thead>
        <tbody>{list.map((x, i) => <tr key={x.id} onClick={() => setSel(i)} className={`cursor-pointer ${i === sel ? "bg-bg" : ""}`}>
          <td data-l="Select"><input type="checkbox" className="h-5 w-5" aria-label="Select" checked={checked.has(x.id)} onClick={(e) => e.stopPropagation()}
            onChange={(e) => { const s = new Set(checked); if (e.target.checked) s.add(x.id); else s.delete(x.id); setChecked(s); }} /></td>
          <td data-l="Risk"><RiskPill risk={x.reviewer_risk ?? x.risk} /></td><td data-l="Claim">{x.claim.text}</td>
          <td data-l="Type">{CLAIM_LABEL[x.claim.claim_type] ?? x.claim.claim_type}</td>
          <td data-l="Where">{x.brand || "–"} · {SURFACES[x.surface as keyof typeof SURFACES] ?? x.surface}</td>
          <td data-l="Conf." className="font-mono">{x.confidence === null ? "rule" : `${Math.round(x.confidence * 100)}%`}</td></tr>)}</tbody></table></div>
      {f && <div className="space-y-2 min-w-0"><Link className="text-sm underline text-primary" to={`/audit?id=${f.audit_id}`}>Open audit #{f.audit_id}</Link>
        <FlagCard key={f.id} f={f} n={sel + 1} onOpen={setViewer} onAction={(a, extra) => act([f.id], a, extra)} /></div>}
    </div>}
    <PageViewer c={viewer} onClose={() => setViewer(null)} /><Toast msg={toast} />
  </div>;
}
