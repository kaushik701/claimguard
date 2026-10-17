import { useState } from "react";
import { api, CATEGORIES, SURFACES, type Citation } from "../api/client";
import { EmptyState, ErrorBanner, FlagCard, InfoBanner, PageViewer, Toast, useToast } from "../components/ui";

const DRAFT = "Been using the new Glowvia (fictional) vitamin C serum for a week and my dark spots are GONE. Clinically proven to brighten skin in just 7 days, 100% natural and chemical-free. Dermatologists recommend it! Use my code GLOW20.";

export default function PreflightScreen() {
  const [text, setText] = useState(DRAFT);
  const [surface, setSurface] = useState("social_post");
  const [category, setCategory] = useState("beauty");
  const [paid, setPaid] = useState(true);
  const [res, setRes] = useState<Awaited<ReturnType<typeof api.preflight>> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [viewer, setViewer] = useState<Citation | null>(null);
  const [toast, setToast] = useToast();
  async function check() {
    setBusy(true); setErr(null);
    try { setRes(await api.preflight({ text, surface, category, paid })); setToast("Pre-flight check done"); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  const verdict = res && { revise: ["Revise before publishing", "bg-high-bg text-high-fg"], check: ["Check before publishing", "bg-med-bg text-med-fg"],
    clear: ["No flags found", "bg-low-bg text-low-fg"] }[res.verdict];
  return <div className="space-y-4">
    <section className="card p-4 space-y-3"><h1 className="text-xl font-bold">Pre-flight a draft</h1>
      <p className="text-sm text-muted">For agencies and creators: check copy before it goes out. Same rules and checks as an audit.</p>
      <textarea className="input min-h-[120px]" value={text} onChange={(e) => setText(e.target.value)} aria-label="Draft" />
      <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(180px, 100%), 1fr))" }}>
        <select className="input" value={surface} onChange={(e) => setSurface(e.target.value)} aria-label="Format">
          {Object.entries(SURFACES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        <select className="input" value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category">
          {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        <label className="flex items-center gap-2 min-h-[44px]"><input type="checkbox" className="h-5 w-5" checked={paid}
          onChange={(e) => setPaid(e.target.checked)} />Paid promotion</label>
        <button className="btn btn-primary" disabled={busy || !text.trim()} onClick={check}>{busy ? "Checking…" : "Check draft"}</button>
      </div>{err && <ErrorBanner>{err}</ErrorBanner>}</section>
    {!res && !busy && <EmptyState title="Paste a draft and press Check draft." />}
    {res && verdict && <>
      <div className={`rounded-lg p-4 text-lg font-bold ${verdict[1]}`} role="status">{verdict[0]}</div>
      <p className="text-xs text-muted">{res.caveat}</p>
      {res.fallback_used && <InfoBanner>AI unavailable, showing rule-based result.</InfoBanner>}
      {res.flags.length > 0 && <button className="btn" onClick={() => {
        navigator.clipboard?.writeText(res.flags.filter((f) => f.rewrite).map((f) => `${f.claim.text}\n→ ${f.rewrite}`).join("\n\n"));
        setToast("Fixes copied"); }}>Copy all fixes</button>}
      <div className="grid gap-3 lg:grid-cols-2">{res.flags.map((f, i) =>
        <FlagCard key={i} f={{ ...f, id: i, status: "open", reviewer_risk: null, reviewer_note: null }} n={i + 1} onOpen={setViewer} />)}</div>
      {res.not_covered.length > 0 && <div className="card p-3 text-sm"><b>Not covered by the knowledge base:</b> {res.not_covered.map((c) => c.text).join(" · ")}</div>}
    </>}
    <PageViewer c={viewer} onClose={() => setViewer(null)} /><Toast msg={toast} />
  </div>;
}
