import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { ErrorBanner, Spinner } from "../components/ui";

export default function SettingsScreen() {
  const h = useQuery({ queryKey: ["health"], queryFn: api.health });
  const [name, setName] = useState(() => { try { return localStorage.getItem("reviewer") ?? ""; } catch { return ""; } });
  if (h.isLoading) return <Spinner />;
  if (h.isError) return <ErrorBanner>{(h.error as Error).message}</ErrorBanner>;
  const d = h.data!;
  return <div className="space-y-4 max-w-2xl"><h1 className="text-xl font-bold">Settings</h1>
    <section className="card p-4 space-y-2"><div className="label">AI providers</div>
      {Object.entries(d.providers).map(([k, v]) => <div key={k} className="flex justify-between"><span>{k}</span>
        <span className={v === "ok" ? "text-low-fg font-semibold" : "text-high-fg font-semibold"}>{v === "ok" ? "key present" : "no key"}</span></div>)}
      {d.last_error && <p className="text-xs text-high-fg">Last error: {d.last_error}</p>}
      <p className="text-xs text-muted">Keys are read from the server's environment (.env), never stored in the app.</p></section>
    <section className="card p-4 space-y-1"><div className="label">Models</div>
      {Object.entries(d.models).map(([k, v]) => <div key={k} className="flex justify-between gap-2 text-sm"><span className="text-muted">{k.replace("_model", "")}</span><span className="font-mono">{v}</span></div>)}</section>
    <section className="card p-4 space-y-1"><div className="label">Knowledge base</div>
      <p className="text-sm">{d.kb.clauses} clauses from {d.kb.docs} documents · built {d.kb.built_at ?? "never"}</p>
      <p className="text-xs text-muted">Rebuild: <code>python -m claimguard.kb build</code> in backend/.</p></section>
    <section className="card p-4 space-y-2"><label className="label" htmlFor="rev">Reviewer name (tags your decisions)</label>
      <input id="rev" className="input" value={name} onChange={(e) => { setName(e.target.value); try { localStorage.setItem("reviewer", e.target.value); } catch { /* private mode */ } }} /></section>
    <p className="text-xs text-muted">Mode: {d.public_demo ? "public demo (fictional samples, uploads off)" : "full (local)"}.</p>
  </div>;
}
