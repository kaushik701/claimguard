import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, CLAIM_LABEL, pageUrl } from "../api/client";
import { ErrorBanner, Spinner, Tag, Toast, useToast } from "../components/ui";

export default function KnowledgeScreen() {
  const docs = useQuery({ queryKey: ["docs"], queryFn: api.documents });
  const [q, setQ] = useState("");
  const [doc, setDoc] = useState("");
  const [tag, setTag] = useState("");
  const [sel, setSel] = useState<string | null>(null);
  const query = `?${new URLSearchParams(Object.entries({ q, doc, tag, limit: "200" }).filter(([, v]) => v)).toString()}`;
  const clauses = useQuery({ queryKey: ["clauses", query], queryFn: () => api.clauses(query) });
  const detail = useQuery({ queryKey: ["clause", sel], queryFn: () => api.clause(sel!), enabled: !!sel });
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
  const [editing, setEditing] = useState<string>("");
  const [toast, setToast] = useToast();
  const qc = useQueryClient();
  async function saveTags() {
    if (!detail.data) return;
    await api.setTags(detail.data.clause_id, { claim_types: editing.split(",").map((s) => s.trim()).filter(Boolean),
      categories: detail.data.categories, surfaces: detail.data.surfaces });
    await qc.invalidateQueries({ queryKey: ["clause", sel] }); setToast("Tags saved (kept across rebuilds)");
  }
  return <div className="space-y-4"><h1 className="text-xl font-bold">Knowledge explorer</h1>
    <p className="text-sm text-muted">The five official PDFs are the only source of rules. How each page was read, and every clause with its page.</p>
    {docs.isError && <ErrorBanner>{(docs.error as Error).message}</ErrorBanner>}
    <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(240px, 100%), 1fr))" }}>
      {docs.data?.map((d) => <button key={d.doc_id} onClick={() => setDoc(doc === d.doc_id ? "" : d.doc_id)}
        className={`card p-3 text-left ${doc === d.doc_id ? "border-primary" : ""}`}>
        <div className="font-mono text-xs text-primary">{d.doc_id} · {d.regulator}</div><div className="font-semibold text-sm">{d.title}</div>
        <div className="text-xs text-muted mt-1">{d.pages} pages: {d.pages_text} text, {d.pages_ocr} OCR{d.ocr_mean_conf ? ` (${Math.round(d.ocr_mean_conf * 100)}%)` : ""}, {d.pages_excluded} excluded · {d.clauses_enabled}/{d.clauses} clauses in use</div>
        {d.excluded.length > 0 && <div className="text-xs text-muted mt-1">Excluded: {Array.from(new Set(d.excluded.map((x) => x.reason))).join("; ")}</div>}
      </button>)}</div>
    <div className="grid gap-2" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(200px, 100%), 1fr))" }}>
      <input className="input" placeholder="Search clause text (e.g. eco-friendly, substantiation)" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
      <select className="input" value={tag} onChange={(e) => setTag(e.target.value)} aria-label="Claim type">
        <option value="">Any claim type</option>{Object.entries(CLAIM_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
    {clauses.isLoading && <Spinner />}
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="space-y-2 max-h-[70vh] overflow-auto min-w-0"><div className="text-xs text-muted">{clauses.data?.total ?? 0} clauses</div>
        {clauses.data?.items.map((c) => <button key={c.clause_id} onClick={() => { setSel(c.clause_id); setEditing(c.claim_types.join(", ")); }}
          className={`card p-3 w-full text-left ${sel === c.clause_id ? "border-primary" : ""} ${c.enabled ? "" : "opacity-60"}`}>
          <div className="flex flex-wrap gap-2 items-center text-xs"><span className="font-mono text-primary">{c.clause_id}</span><span className="text-muted">p.{c.page_start}</span>
            {c.source === "ocr" && <Tag>OCR</Tag>}{!c.enabled && <Tag>not used</Tag>}{c.duplicate_of && <Tag>same as {c.duplicate_of}</Tag>}</div>
          <div className="text-sm mt-1 line-clamp-3">{c.text}</div></button>)}</div>
      <div className="min-w-0">{detail.data && <div className="card p-4 space-y-3 sticky top-4">
        <div className="font-mono text-primary">{detail.data.clause_id}</div><div className="text-sm text-muted">{detail.data.doc_title} · {detail.data.section_path} · page {detail.data.page_start}</div>
        {detail.data.ocr_conf !== null && <div className="text-xs text-med-fg font-semibold">Read by OCR ({Math.round((detail.data.ocr_conf ?? 0) * 100)}% confidence): check against the PDF page.</div>}
        <blockquote className="quote max-h-60 overflow-auto">{detail.data.text}</blockquote>
        <div className="flex flex-wrap gap-1">{detail.data.claim_types.map((t) => <Tag key={t}>{CLAIM_LABEL[t] ?? t}</Tag>)}
          <Tag>products: {detail.data.categories.join(", ")}</Tag><Tag>surfaces: {detail.data.surfaces.join(", ")}</Tag><Tag>tags: {detail.data.tag_source}</Tag></div>
        <div className="text-xs text-muted">Used in {detail.data.stats?.used_in ?? 0} reviewed flags{detail.data.stats?.accept_rate != null ? ` · reviewers agreed ${Math.round(detail.data.stats.accept_rate * 100)}%` : ""}</div>
        {!health.data?.public_demo && <div className="flex gap-2"><input className="input" value={editing} onChange={(e) => setEditing(e.target.value)} aria-label="Claim types (comma separated)" />
          <button className="btn" onClick={saveTags}>Save tags</button></div>}
        <img src={pageUrl(detail.data.doc_id, detail.data.page_start)} alt={`Page ${detail.data.page_start}`} className="w-full border border-border rounded" />
      </div>}</div>
    </div><Toast msg={toast} />
  </div>;
}
