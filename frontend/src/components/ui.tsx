import { useEffect, useState, type ReactNode } from "react";
import { CLAIM_LABEL, pageUrl, type Citation, type Flag, type Risk, type Step } from "../api/client";

export const RISK_TEXT: Record<Risk, string> = { high: "High risk", medium: "Medium risk", low: "Low risk" };

export function RiskPill({ risk, n }: { risk: Risk; n?: number }) {
  const cls = risk === "high" ? "bg-high-bg text-high-fg" : risk === "medium" ? "bg-med-bg text-med-fg" : "bg-low-bg text-low-fg";
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold ${cls}`}>
    {n !== undefined && <span className="font-mono mr-1">{n}</span>}{RISK_TEXT[risk]}</span>;
}

export function Tag({ children }: { children: ReactNode }) {
  return <span className="inline-flex items-center rounded border border-border px-2 py-0.5 text-xs text-muted">{children}</span>;
}

export function StatTile({ label, value, tone }: { label: string; value: ReactNode; tone?: "high" | "medium" }) {
  const c = typeof value === "number" && value > 0 ? (tone === "high" ? "text-high-fg" : tone === "medium" ? "text-med-fg" : "") : "";
  return <div className="card px-4 py-3 min-w-0">
    <div className={`text-2xl font-bold font-mono ${c}`}>{value}</div><div className="text-xs text-muted">{label}</div></div>;
}

export function StatRow({ items }: { items: { label: string; value: ReactNode; tone?: "high" | "medium" }[] }) {
  return <div className="grid gap-2" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(130px, 100%), 1fr))" }}>
    {items.map((i) => <StatTile key={i.label} {...i} />)}</div>;
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="card border-dashed p-8 text-center"><p className="font-semibold">{title}</p>
    {children && <div className="text-sm text-muted mt-2">{children}</div>}</div>;
}

export function ErrorBanner({ children }: { children: ReactNode }) {
  return <div role="alert" className="rounded-lg border border-high-line bg-high-bg text-high-fg px-4 py-3 text-sm">{children}</div>;
}

export function InfoBanner({ children }: { children: ReactNode }) {
  return <div className="rounded-lg border border-med-line bg-med-bg text-med-fg px-4 py-3 text-sm">{children}</div>;
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return <div className="text-sm text-muted py-6 text-center" aria-live="polite">{label}</div>;
}

export function ConfidenceBar({ value }: { value: number | null }) {
  if (value === null || value === undefined) return <span className="text-xs text-muted">Rule-based (no confidence score)</span>;
  const pct = Math.round(value * 100);
  return <div className="flex items-center gap-2 text-xs"><span className="text-muted">Confidence</span>
    <div className="h-2 flex-1 max-w-[180px] rounded bg-border" aria-hidden>
      <div className="h-2 rounded bg-primary" style={{ width: `${pct}%` }} /></div><span className="font-mono">{pct}%</span></div>;
}

export function ProgressSteps({ steps }: { steps: Step[] }) {
  return <ol className="flex flex-wrap gap-2" aria-label="Progress">
    {steps.filter((s) => s.name !== "total").map((s) => (
      <li key={s.name} className={`rounded-full border px-3 py-1 text-xs font-semibold ${s.status === "done" ? "border-primary text-primary" :
        s.status === "running" ? "border-med-line text-med-fg animate-pulse" : s.status === "error" ? "border-high-line text-high-fg" : "border-border text-muted"}`}>
        {s.status === "done" ? "✓ " : ""}{s.name}{s.status === "done" && s.ms ? <span className="font-mono font-normal"> {(s.ms / 1000).toFixed(1)}s</span> : null}
      </li>))}
  </ol>;
}

export function CitationBlock({ c, onOpen }: { c: Citation; onOpen?: (c: Citation) => void }) {
  const low = c.ocr_conf !== null && c.ocr_conf !== undefined && c.ocr_conf < 0.8;
  return <div className="space-y-1">
    <blockquote className="quote text-[15px] leading-relaxed">“{c.quote}”</blockquote>
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
      <span className="font-mono text-text">{c.clause_id}</span><span>· {c.doc_title}</span>
      {c.section_path && <span>· {c.section_path}</span>}<span>· page {c.page}</span>
      {c.source === "ocr" && <span className={low ? "text-high-fg font-semibold" : "text-med-fg font-semibold"}>
        · read by OCR{c.ocr_conf ? ` (${Math.round(c.ocr_conf * 100)}%)` : ""}, check against the PDF</span>}
      {onOpen && <button className="underline text-primary min-h-[32px]" onClick={() => onOpen(c)}>Open page</button>}
    </div></div>;
}

export function PageViewer({ c, onClose }: { c: Citation | null; onClose: () => void }) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  if (!c) return null;
  return <div className="fixed inset-0 z-50 bg-black/40 flex justify-end" onClick={onClose} role="dialog" aria-label="PDF page">
    <div className="h-full w-full max-w-2xl bg-surface p-4 overflow-auto" onClick={(e) => e.stopPropagation()}>
      <div className="flex items-center justify-between gap-2 mb-3">
        <div><div className="font-semibold">{c.doc_title}</div><div className="text-xs text-muted">{c.clause_id} · page {c.page}</div></div>
        <button className="btn" onClick={onClose}>Close</button></div>
      <blockquote className="quote mb-3">“{c.quote}”</blockquote>
      <p className="text-xs text-muted mb-2">The quote above is the exact text the flag relies on; find it on the page below.
        <a className="underline text-primary ml-1" href={`/api/kb/pdfs/${c.doc_id}.pdf#page=${c.page}`} target="_blank" rel="noreferrer">Open the PDF</a></p>
      <img src={pageUrl(c.doc_id, c.page)} alt={`${c.doc_title}, page ${c.page}`} className="w-full border border-border rounded" />
    </div></div>;
}

export function RewriteDiff({ original, suggested }: { original: string; suggested: string | null }) {
  if (!suggested) return null;
  return <div className="grid gap-2" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(220px, 100%), 1fr))" }}>
    <div className="rounded-lg bg-high-bg text-high-fg p-3"><div className="label !text-high-fg mb-1">As published</div>
      <div className="line-through">{original}</div></div>
    <div className="rounded-lg bg-low-bg text-low-fg p-3"><div className="label !text-low-fg mb-1">Suggested</div><div>{suggested}</div></div>
  </div>;
}

export function ClaimHighlighter({ text, flags, selected, onSelect }: { text: string; flags: Flag[]; selected?: number;
  onSelect?: (i: number) => void }) {
  const spans = flags.map((f, i) => ({ s: f.claim.start, e: f.claim.end, risk: f.reviewer_risk ?? f.risk, i }))
    .filter((x) => x.s >= 0 && x.e <= text.length && x.e > x.s).sort((a, b) => a.s - b.s);
  const out: ReactNode[] = [];
  let pos = 0;
  for (const sp of spans) {
    if (sp.s < pos) continue;
    out.push(text.slice(pos, sp.s));
    out.push(<mark key={sp.i} className={`hl-${sp.risk} ${sp.i === selected ? "hl-sel" : ""} cursor-pointer`}
      onClick={() => onSelect?.(sp.i)} title={RISK_TEXT[sp.risk]}>{text.slice(sp.s, sp.e)}<sup className="font-mono font-bold ml-0.5">{sp.i + 1}</sup></mark>);
    pos = sp.e;
  }
  out.push(text.slice(pos));
  return <div className="card p-4 whitespace-pre-wrap leading-7 text-[15px] break-words">{out}</div>;
}

export function FlagCard({ f, n, onOpen, onAction, busy }: { f: Flag; n: number; onOpen: (c: Citation) => void;
  onAction?: (action: string, extra?: { risk?: Risk; reason_code?: string; note?: string }) => void; busy?: boolean }) {
  const [note, setNote] = useState(f.reviewer_note ?? "");
  const [reason, setReason] = useState("substantiated");
  const risk = f.reviewer_risk ?? f.risk;
  return <article className="card p-4 space-y-3" aria-label={`Flag ${n}`}>
    <div className="flex flex-wrap items-center gap-2"><RiskPill risk={risk} n={n} />
      <Tag>{CLAIM_LABEL[f.claim.claim_type] ?? f.claim.claim_type}</Tag>
      {f.claim.source === "both" && <Tag>found by AI + rules</Tag>}{f.claim.source === "llm" && <Tag>found by AI</Tag>}
      <Tag>{f.status === "open" ? "Not reviewed" : f.status[0].toUpperCase() + f.status.slice(1)}</Tag>
      {f.reviewer_risk && f.reviewer_risk !== f.risk && <Tag>AI said {f.risk}</Tag>}</div>
    <h3 className="text-lg font-semibold break-words">{f.claim.text}</h3>
    <div><div className="label mb-1">Why it was flagged</div><p>{f.reason}</p></div>
    <ConfidenceBar value={f.confidence} />
    {f.verifier_note && <InfoBanner><b>Second check lowered this:</b> {f.verifier_note}</InfoBanner>}
    <div><div className="label mb-1">Rule{f.citations.length > 1 ? "s" : ""} it relies on</div>
      <div className="space-y-3">{f.citations.map((c) => <CitationBlock key={c.clause_id} c={c} onOpen={onOpen} />)}</div></div>
    {f.rewrite && <div><div className="label mb-1">Suggested direction</div><RewriteDiff original={f.claim.text} suggested={f.rewrite} />
      <p className="text-xs text-muted mt-1">Fill &lt;placeholders&gt; from the substantiation file. ClaimGuard never invents numbers or sources.</p>
      <button className="text-xs underline text-primary mt-1 min-h-[32px]" onClick={() => navigator.clipboard?.writeText(f.rewrite ?? "")}>Copy suggestion</button></div>}
    {onAction && <div className="space-y-2 border-t border-border pt-3">
      <input className="input" placeholder="Reviewer note (optional)" value={note} onChange={(e) => setNote(e.target.value)} aria-label="Reviewer note" />
      <div className="flex flex-wrap gap-2">
        <button className="btn btn-primary" disabled={busy} onClick={() => onAction("accept", { note })} title="a">Accept</button>
        <select className="input !w-auto" value={reason} onChange={(e) => setReason(e.target.value)} aria-label="Dismiss reason">
          <option value="substantiated">Substantiated</option><option value="not_a_claim">Not a claim</option>
          <option value="puffery">Puffery</option><option value="wrong_clause">Wrong clause</option>
          <option value="wrong_risk">Wrong risk</option><option value="other">Other</option></select>
        <button className="btn" disabled={busy} onClick={() => onAction("dismiss", { reason_code: reason, note })} title="d">Dismiss</button>
        <select className="input !w-auto" value="" aria-label="Change risk"
          onChange={(e) => e.target.value && onAction("set_risk", { risk: e.target.value as Risk, note })}>
          <option value="">Change risk…</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select>
        <button className="btn" disabled={busy} onClick={() => onAction("escalate", { note })} title="e">Escalate</button>
      </div><p className="text-xs text-muted">Keys: j / k next / previous, a accept, d dismiss, e escalate.</p></div>}
  </article>;
}

export function useKeys(map: Record<string, () => void>) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName) || e.metaKey || e.ctrlKey) return;
      map[e.key]?.();
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [map]);
}

export function Toast({ msg }: { msg: string | null }) {
  if (!msg) return null;
  return <div role="status" className="fixed bottom-20 md:bottom-6 right-4 z-50 card px-4 py-3 shadow-lg text-sm font-semibold">✓ {msg}</div>;
}

export function useToast(): [string | null, (m: string) => void] {
  const [m, setM] = useState<string | null>(null);
  useEffect(() => { if (!m) return; const t = setTimeout(() => setM(null), 2500); return () => clearTimeout(t); }, [m]);
  return [m, setM];
}
