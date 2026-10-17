import { useQuery } from "@tanstack/react-query";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api/client";
import AskScreen from "./screens/Ask";
import AuditScreen from "./screens/Audit";
import EvalScreen from "./screens/Eval";
import KnowledgeScreen from "./screens/Knowledge";
import PortfolioScreen from "./screens/Portfolio";
import PreflightScreen from "./screens/Preflight";
import ReviewScreen from "./screens/Review";
import SettingsScreen from "./screens/Settings";

const NAV = [["/audit", "Audit"], ["/preflight", "Pre-flight"], ["/ask", "Ask"], ["/review", "Review"],
  ["/portfolio", "Portfolio"], ["/knowledge", "Knowledge"], ["/eval", "Eval"], ["/settings", "Settings"]] as const;

export default function App() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, staleTime: 60_000 });
  const noAi = health.data && Object.values(health.data.providers).every((v) => v !== "ok");
  return <div className="min-h-screen md:flex">
    <nav className="hidden md:flex md:flex-col md:w-52 shrink-0 border-r border-border bg-surface p-3 gap-1 sticky top-0 h-screen" aria-label="Main">
      <div className="px-2 py-3"><div className="text-xl font-bold text-primary">ClaimGuard</div>
        <div className="text-xs text-muted">Claims-risk auditor</div></div>
      {NAV.map(([to, label]) => <NavLink key={to} to={to} className={({ isActive }) =>
        `rounded px-3 py-2.5 text-sm font-semibold ${isActive ? "bg-bg text-primary" : "text-muted hover:text-text"}`}>{label}</NavLink>)}
    </nav>
    <div className="flex-1 min-w-0 pb-20 md:pb-0">
      <header className="border-b border-border bg-surface px-4 py-3 flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="md:hidden text-lg font-bold text-primary">ClaimGuard</span>
        {health.data?.public_demo && <span className="rounded-full bg-bg px-2 py-0.5 text-xs font-semibold text-primary">demo · fictional brands</span>}
        <span className="text-xs text-muted">Risk indicators, not legal advice · Not affiliated with or endorsed by any brand owner</span>
        {health.data && <span className="ml-auto text-xs text-muted">Knowledge base: {health.data.kb.clauses} clauses · {health.data.kb.docs} documents</span>}
      </header>
      {health.isError && <div className="m-4 rounded-lg border border-high-line bg-high-bg text-high-fg px-4 py-3 text-sm" role="alert">
        Cannot reach the ClaimGuard server. Start the backend (see README: “Run it”), then reload this page.</div>}
      {noAi && <div className="m-4 rounded-lg border border-med-line bg-med-bg text-med-fg px-4 py-3 text-sm">
        AI unavailable (no API key): audits show the rule-based result, and Ask the Guidelines is off.</div>}
      <main className="p-4 max-w-[1400px] mx-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/audit" replace />} />
          <Route path="/audit" element={<AuditScreen />} /><Route path="/preflight" element={<PreflightScreen />} />
          <Route path="/ask" element={<AskScreen />} /><Route path="/review" element={<ReviewScreen />} />
          <Route path="/portfolio" element={<PortfolioScreen />} /><Route path="/knowledge" element={<KnowledgeScreen />} />
          <Route path="/eval" element={<EvalScreen />} /><Route path="/settings" element={<SettingsScreen />} />
        </Routes>
      </main>
    </div>
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-surface border-t border-border flex overflow-x-auto" aria-label="Main">
      {NAV.map(([to, label]) => <NavLink key={to} to={to} className={({ isActive }) =>
        `flex-1 min-w-[64px] text-center py-3 text-xs font-semibold ${isActive ? "text-primary" : "text-muted"}`}>{label}</NavLink>)}
    </nav>
  </div>;
}
