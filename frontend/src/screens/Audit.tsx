import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError, CATEGORIES, CLAIM_LABEL, SURFACES, type Audit, type Citation, type Flag, type Step } from "../api/client";
import { ClaimHighlighter, EmptyState, ErrorBanner, FlagCard, InfoBanner, PageViewer, ProgressSteps, RiskPill, Spinner,
  StatRow, Toast, useKeys, useToast } from "../components/ui";

type Tab = "paste" | "upload" | "image" | "sample";
const STEP_NAMES = ["Reading", "Finding claims", "Finding rules", "Judging", "Checking"];

export default function AuditScreen() {
  const [params, setParams] = useSearchParams();
  const auditId = params.get("id") ? Number(params.get("id")) : null;
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
  const samples = useQuery({ queryKey: ["samples"], queryFn: api.samples });
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("sample");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [surface, setSurface] = useState("ecommerce");
  const [category, setCategory] = useState("home");
  const [brand, setBrand] = useState("");
  const [paid, setPaid] = useState(false);
  const [sample, setSample] = useState(0);
  const [steps, setSteps] = useState<Step[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sel, setSel] = useState(0);
  const [viewer, setViewer] = useState<Citation | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useToast();
  const audit = useQuery({ queryKey: ["audit", auditId], queryFn: () => api.audit(auditId!), enabled: !!auditId && !running });

  useEffect(() => {
    const s = samples.data?.[sample];
    if (tab === "sample" && s) {
      setText(s.text); setSurface(s.surface); setCategory(s.category); setBrand(s.brand); setPaid(!!s.is_paid_promotion);
    }
  }, [tab, sample, samples.data]);

  const publicDemo = health.data?.public_demo;
  async function run() {
    setError(null);
    const fd = new FormData();
    fd.set("surface", surface); fd.set("category", category); fd.set("brand", brand); fd.set("paid", String(paid));
    if (tab === "paste" || tab === "sample") { fd.set("input_type", "text"); fd.set("text", text); }
    else if (file) { fd.set("input_type", tab === "image" ? "image" : file.name.toLowerCase().endsWith(".pdf") ? "pdf" : "html"); fd.set("file", file); }
    else { setError("Choose a file first."); return; }
    setRunning(true); setSteps(STEP_NAMES.map((name) => ({ name, status: "pending", ms: 0 })));
    try {
      const { audit_id } = await api.createAudit(fd);
      await new Promise<void>((resolve, reject) => {
        const es = new EventSource(`/api/audits/${audit_id}/events`);
        es.addEventListener("step", (e) => {
          const st = JSON.parse((e as MessageEvent).data) as Step;
          setSteps((prev) => prev.map((p) => (p.name === st.name ? st : p)));
        });
        es.addEventListener("done", () => { es.close(); resolve(); });
        es.addEventListener("error", (e) => {
          es.close();
          const d = (e as MessageEvent).data;
          if (d) reject(new Error(JSON.parse(d).message)); else resolve();
        });
      });
      setSel(0); setParams({ id: String(audit_id) });
      await qc.invalidateQueries({ queryKey: ["audit", audit_id] });
      setToast(`Audit #${audit_id} complete`);
    } catch (e) {
      setError(e instanceof ApiError || e instanceof Error ? e.message : "The audit failed.");
    } finally { setRunning(false); }
  }

  const a = audit.data;
  const flags = a?.flags ?? [];
  async function act(f: Flag, action: string, extra?: Record<string, unknown>) {
    setBusy(true);
    try {
      await api.patchFlag(f.id, { action, ...extra });
      await qc.invalidateQueries({ queryKey: ["audit", auditId] });
      setToast(action === "set_risk" ? "Risk changed" : `Flag ${action === "accept" ? "accepted" : action === "dismiss" ? "dismissed" : "escalated"}`);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  const keys = useMemo(() => ({
    j: () => setSel((s) => Math.min(flags.length - 1, s + 1)), k: () => setSel((s) => Math.max(0, s - 1)),
    a: () => flags[sel] && act(flags[sel], "accept"), d: () => flags[sel] && act(flags[sel], "dismiss", { reason_code: "other" }),
    e: () => flags[sel] && act(flags[sel], "escalate"),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [flags, sel]);
  useKeys(keys);

  function csv(a: Audit) {
    const rows = [["no", "risk", "claim_type", "claim", "reason", "rules", "suggested", "status", "confidence"],
      ...a.flags.map((f, i) => [i + 1, f.reviewer_risk ?? f.risk, f.claim.claim_type, f.claim.text, f.reason,
        f.citations.map((c) => `${c.clause_id} p.${c.page}`).join("; "), f.rewrite ?? "", f.status, f.confidence ?? ""])];
    const blob = new Blob([rows.map((r) => r.map((x) => `"${String(x).replace(/"/g, '""')}"`).join(",")).join("\n")], { type: "text/csv" });
    const u = URL.createObjectURL(blob); const l = document.createElement("a"); l.href = u; l.download = `claimguard_audit_${a.id}.csv`; l.click();
  }

  return <div className="space-y-4">
    <section className="card p-4 space-y-3" aria-label="New audit">
      <div className="flex flex-wrap gap-2" role="tablist">
        {([["sample", "Sample (fictional)"], ["paste", "Paste text"], ["upload", "Upload saved page"], ["image", "Pack image"]] as [Tab, string][]).map(([t, l]) =>
          <button key={t} role="tab" aria-selected={tab === t} disabled={publicDemo && (t === "upload" || t === "image")}
            className={`btn ${tab === t ? "btn-primary" : ""}`} onClick={() => setTab(t)}>{l}</button>)}
      </div>
      {publicDemo && <p className="text-xs text-muted">Public demo: uploads are off; use the fictional samples or paste text.</p>}
      {tab === "sample" && <select className="input" value={sample} onChange={(e) => setSample(Number(e.target.value))} aria-label="Sample">
        {samples.data?.map((s, i) => <option key={s.listing_id} value={i}>{s.brand} · {SURFACES[s.surface as keyof typeof SURFACES]} · {s.title || s.text.slice(0, 40)}</option>)}</select>}
      {(tab === "paste" || tab === "sample") && <textarea className="input min-h-[140px]" value={text} onChange={(e) => setText(e.target.value)}
        aria-label="Listing or caption text" placeholder="Paste the listing or caption, including footnotes (*…) and declarations." />}
      {(tab === "upload" || tab === "image") && <input type="file" className="input" aria-label="File"
        accept={tab === "image" ? ".png,.jpg,.jpeg" : ".html,.htm,.pdf"} onChange={(e) => setFile(e.target.files?.[0] ?? null)} />}
      <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(180px, 100%), 1fr))" }}>
        <label className="space-y-1"><span className="label">Surface</span>
          <select className="input" value={surface} onChange={(e) => setSurface(e.target.value)}>
            {Object.entries(SURFACES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label className="space-y-1"><span className="label">Category</span>
          <select className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
            {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label className="space-y-1"><span className="label">Brand</span>
          <input className="input" value={brand} onChange={(e) => setBrand(e.target.value)} placeholder="e.g. Brightwash (fictional)" /></label>
        <label className="flex items-center gap-2 min-h-[44px] self-end"><input type="checkbox" className="h-5 w-5" checked={paid}
          disabled={surface !== "social_post"} onChange={(e) => setPaid(e.target.checked)} /><span className="text-sm">Paid promotion</span></label>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button className="btn btn-primary" disabled={running} onClick={run}>{running ? "Auditing…" : "Run audit"}</button>
        {steps.length > 0 && <ProgressSteps steps={running ? steps : (a?.steps ?? steps)} />}
      </div>
      {error && <ErrorBanner>{error}</ErrorBanner>}
    </section>

    {!auditId && !running && <EmptyState title="Pick a sample or paste a listing, then run the audit.">
      Every claim is found, matched to the five official rulebooks and, if risky, shown with the exact rule it relies on
      (quoted word for word, with document and page) and a suggested rewrite.</EmptyState>}
    {auditId && audit.isLoading && <Spinner />}
    {audit.isError && <ErrorBanner>{(audit.error as Error).message}</ErrorBanner>}
    {a && a.status === "error" && <ErrorBanner>The audit failed: {a.error}</ErrorBanner>}
    {a && a.status === "done" && <>
      {a.fallback_used && <InfoBanner>AI unavailable, showing rule-based result ({a.fallback_reason}).</InfoBanner>}
      <StatRow items={[{ label: "Claims found", value: a.stats.claims }, { label: "High risk", value: a.stats.high, tone: "high" },
        { label: "Medium risk", value: a.stats.medium, tone: "medium" }, { label: "Not covered by the knowledge base", value: a.stats.not_covered, tone: "medium" },
        { label: "Dropped by checks", value: a.stats.dropped }]} />
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="space-y-3 min-w-0"><div className="label">Input with claims marked</div>
          {a.image_url && <div className="relative card p-2"><img src={a.image_url} alt="Uploaded pack" className="w-full" id="packimg" />
            <OcrBoxes a={a} sel={sel} /></div>}
          <ClaimHighlighter text={a.text} flags={flags} selected={sel} onSelect={setSel} />
          <div className="text-xs text-muted">{(a.latency_ms / 1000).toFixed(1)} s · tokens {a.tokens_in}/{a.tokens_out}
            {a.cost_usd ? ` · US$${a.cost_usd}` : ""}</div>
        </section>
        <section className="space-y-3 min-w-0">
          {flags.length === 0 ? <EmptyState title="No medium or high-risk claims found.">No flags means no rule in the five documents was triggered; it is not clearance.</EmptyState> : <>
            <div className="flex flex-wrap gap-2" role="list">{flags.map((f, i) =>
              <button key={f.id} role="listitem" onClick={() => setSel(i)} className={`rounded-full border px-3 py-1 text-xs min-h-[36px] ${i === sel ? "border-primary" : "border-border"}`}>
                <span className="font-mono">{i + 1}</span> · {CLAIM_LABEL[f.claim.claim_type] ?? f.claim.claim_type} · {(f.reviewer_risk ?? f.risk).toUpperCase()}</button>)}</div>
            {flags[sel] && <FlagCard key={flags[sel].id} f={flags[sel]} n={sel + 1} onOpen={setViewer} busy={busy}
              onAction={(act_, extra) => act(flags[sel], act_, extra)} />}</>}
        </section>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <Panel title={`Not covered by the knowledge base (${a.not_covered.length})`} note="No clause in the five documents is about this kind of claim. Not judged.">
          {a.not_covered.map((c, i) => <li key={i}>{c.text} <span className="text-muted">({CLAIM_LABEL[c.claim_type] ?? c.claim_type})</span></li>)}</Panel>
        <Panel title={`Low-risk claims (${a.low_risk.length})`}>
          {a.low_risk.map((c, i) => <li key={i}>{c.text} <span className="text-muted">({CLAIM_LABEL[c.claim_type] ?? c.claim_type})</span></li>)}</Panel>
        <Panel title={`Dropped by checks (${a.dropped.length})`} note="Warnings removed because the quote or evidence could not be verified, or the second check disagreed.">
          {a.dropped.map((d, i) => <li key={i}>{d.claim} <span className="text-muted">— {d.reason}</span></li>)}</Panel>
      </div>
      <div className="flex flex-wrap gap-2">
        <button className="btn" onClick={() => csv(a)}>Download flags (CSV)</button>
        <a className="btn" href={`/api/reports/${a.id}.html`} target="_blank" rel="noreferrer">Printable report</a>
        {flags[0] && <span className="self-center"><RiskPill risk={flags[0].reviewer_risk ?? flags[0].risk} /></span>}
      </div>
    </>}
    {a && a.status !== "done" && a.status !== "error" && <Spinner label="Audit running…" />}
    <PageViewer c={viewer} onClose={() => setViewer(null)} />
    <Toast msg={toast} />
  </div>;
}

function Panel({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) {
  return <details className="card p-3" open><summary className="font-semibold cursor-pointer min-h-[32px]">{title}</summary>
    {note && <p className="text-xs text-muted mt-1">{note}</p>}<ul className="mt-2 space-y-1 text-sm list-disc pl-5">{children}</ul></details>;
}

function OcrBoxes({ a, sel }: { a: Audit; sel: number }) {
  const [size, setSize] = useState<{ w: number; h: number; nw: number; nh: number } | null>(null);
  useEffect(() => {
    const img = document.getElementById("packimg") as HTMLImageElement | null;
    if (!img) return;
    const upd = () => setSize({ w: img.clientWidth, h: img.clientHeight, nw: img.naturalWidth, nh: img.naturalHeight });
    if (img.complete) upd(); img.addEventListener("load", upd); window.addEventListener("resize", upd);
    return () => { img.removeEventListener("load", upd); window.removeEventListener("resize", upd); };
  }, [a.image_url]);
  if (!size || !size.nw) return null;
  const k = size.w / size.nw;
  return <>{a.flags.flatMap((f, i) => (f.boxes ?? []).map((b, j) =>
    <div key={`${i}-${j}`} className="absolute pointer-events-none rounded" style={{ left: 8 + b[0] * k, top: 8 + b[1] * k,
      width: (b[2] - b[0]) * k, height: (b[3] - b[1]) * k,
      border: `2px solid var(${(f.reviewer_risk ?? f.risk) === "high" ? "--high-line" : "--med-line"})`,
      outline: i === sel ? "2px solid var(--primary)" : undefined }} />))}</>;
}
