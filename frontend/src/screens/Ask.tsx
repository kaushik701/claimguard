import { useState } from "react";
import { api, type Citation } from "../api/client";
import { ErrorBanner, PageViewer } from "../components/ui";

const STARTERS = ["Can I call a detergent eco-friendly if only the bottle is recycled?",
  "What must an influencer do when a post is paid?", "Can a malt drink be called a health drink?",
  "What do I need before saying 'India's No.1'?"];
type Turn = { role: "user" | "assistant"; text: string; covered?: boolean;
  citations?: { n: number; clause_id: string; doc: string; doc_id: string; page: number; quote: string; ocr_conf: number | null }[] };

export default function AskScreen() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [msg, setMsg] = useState("");
  const [sid, setSid] = useState<number | undefined>();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [viewer, setViewer] = useState<Citation | null>(null);
  async function send(text: string) {
    if (!text.trim()) return;
    setTurns((t) => [...t, { role: "user", text }]); setMsg(""); setBusy(true); setErr(null);
    try {
      const r = await api.ask({ session_id: sid, message: text });
      setSid(r.session_id);
      setTurns((t) => [...t, { role: "assistant", text: r.answer, covered: r.covered, citations: r.citations }]);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  return <div className="space-y-4 max-w-3xl">
    <h1 className="text-xl font-bold">Ask the Guidelines</h1>
    <p className="text-sm text-muted">Answers come only from the five documents, with the clause and page for each point. If they don't cover the question, it says so.</p>
    {turns.length === 0 && <div className="flex flex-wrap gap-2">{STARTERS.map((s) => <button key={s} className="btn text-sm" onClick={() => send(s)}>{s}</button>)}</div>}
    <div className="space-y-3" aria-live="polite">{turns.map((t, i) => t.role === "user"
      ? <div key={i} className="card p-3 ml-auto max-w-[85%] bg-bg"><b>You:</b> {t.text}</div>
      : <div key={i} className={`card p-4 space-y-3 ${t.covered ? "" : "border-med-line"}`}>
          <p className="leading-relaxed">{t.text}</p>
          {t.citations?.map((c) => <div key={c.n} className="space-y-1"><blockquote className="quote">[{c.n}] “{c.quote}”</blockquote>
            <div className="text-xs text-muted"><span className="font-mono text-text">{c.clause_id}</span> · {c.doc} · page {c.page}
              {c.ocr_conf ? " · read by OCR, check against the PDF" : ""}
              <button className="underline text-primary ml-2 min-h-[32px]" onClick={() => setViewer({ clause_id: c.clause_id, doc_id: c.doc_id,
                doc_title: c.doc, section_path: "", number: null, page: c.page, quote: c.quote, source: c.ocr_conf ? "ocr" : "text" })}>Open page</button></div></div>)}
          <p className="text-xs text-muted">Not legal advice.</p></div>)}
      {busy && <div className="text-sm text-muted">Searching the five documents…</div>}</div>
    {err && <ErrorBanner>{err}</ErrorBanner>}
    <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); send(msg); }}>
      <input className="input" value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Ask about a claim or a rule…" aria-label="Question" />
      <button className="btn btn-primary" disabled={busy}>Ask</button></form>
    <PageViewer c={viewer} onClose={() => setViewer(null)} />
  </div>;
}
