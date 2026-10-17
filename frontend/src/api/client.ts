// Typed client for the ClaimGuard API (contract: src/api/openapi.json). VITE_USE_MOCKS=true serves mock data.
import mockAudit from "./mock/audit.json";

export type Risk = "high" | "medium" | "low";
export interface Citation { clause_id: string; doc_id: string; doc_title: string; section_path: string;
  number: string | null; page: number; quote: string; source: "text" | "ocr" | "vision"; ocr_conf?: number | null }
export interface Claim { id: string; text: string; start: number; end: number; claim_type: string; source: string }
export interface Flag { id: number; audit_id?: number; claim: Claim; risk: Risk; reason: string; rewrite: string | null;
  confidence: number | null; verifier_note: string | null; citations: Citation[];
  status: "open" | "accepted" | "dismissed" | "escalated"; reviewer_risk: Risk | null; reviewer_note: string | null;
  brand?: string; surface?: string; category?: string; boxes?: number[][] }
export interface Step { name: string; status: string; ms: number }
export interface Audit { id: number; created_at: string; status: string; error: string | null; input_type: string;
  surface: string; category: string; brand: string; paid: boolean; text: string; image_url: string | null;
  ocr_boxes: { text: string; conf: number; box: number[]; start: number; end: number }[]; steps: Step[];
  claims: Claim[]; flags: Flag[]; not_covered: Claim[]; low_risk: Claim[]; dropped: { claim: string; reason: string; stage: string }[];
  fallback_used: boolean; fallback_reason: string | null;
  stats: { claims: number; high: number; medium: number; not_covered: number; dropped: number };
  latency_ms: number; tokens_in: number; tokens_out: number; cost_usd: number | null }
export interface Clause { clause_id: string; doc_id: string; regulator: string; doc_title: string; section_path: string;
  number: string | null; text: string; page_start: number; page_end: number; source: string; ocr_conf: number | null;
  claim_types: string[]; categories: string[]; surfaces: string[]; enabled: boolean; tag_source: string;
  duplicate_of: string | null; stats?: { used_in: number; accept_rate: number | null }; page_image_url?: string }

const MOCK = import.meta.env.VITE_USE_MOCKS === "true";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError(0, "offline", "Cannot reach the ClaimGuard server. Is the backend running on port 8000?");
  }
  if (!r.ok) {
    let msg = `Request failed (${r.status}).`, code = "error";
    try { const j = await r.json(); msg = j.error?.message ?? msg; code = j.error?.code ?? code; } catch { /* not json */ }
    throw new ApiError(r.status, code, msg);
  }
  return r.headers.get("content-type")?.includes("json") ? r.json() : (r.text() as unknown as T);
}
const json = (body: unknown, method = "POST"): RequestInit =>
  ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  health: () => req<{ status: string; providers: Record<string, string>; kb: { built_at: string | null; docs: number; clauses: number };
    public_demo: boolean; models: Record<string, string>; last_error: string | null }>("/health"),
  samples: () => req<{ listing_id: string; surface: string; brand: string; category: string; is_paid_promotion?: boolean;
    title: string; text: string }[]>("/samples"),
  createAudit: (fd: FormData) => MOCK ? Promise.resolve({ audit_id: 1 }) :
    req<{ audit_id: number }>("/audits", { method: "POST", body: fd }),
  audit: (id: number) => MOCK ? Promise.resolve(mockAudit as unknown as Audit) : req<Audit>(`/audits/${id}`),
  audits: () => req<{ id: number; created_at: string; brand: string; surface: string; category: string; status: string;
    snippet: string; high: number; medium: number; fallback_used: boolean }[]>("/audits"),
  patchFlag: (id: number, body: { action: string; risk?: Risk; reason_code?: string; note?: string; reviewer?: string }) =>
    req<Flag>(`/flags/${id}`, json(body, "PATCH")),
  flags: (q: string) => req<Flag[]>(`/flags${q}`),
  preflight: (body: { text: string; surface: string; category: string; paid: boolean }) =>
    req<{ verdict: "revise" | "check" | "clear"; flags: Flag[]; not_covered: Claim[]; fallback_used: boolean; caveat: string }>(
      "/preflight", json(body)),
  ask: (body: { session_id?: number; message: string }) =>
    req<{ session_id: number; answer: string; covered: boolean; question: string;
      citations: { n: number; clause_id: string; doc: string; doc_id: string; page: number; quote: string; ocr_conf: number | null }[] }>(
      "/ask", json(body)),
  documents: () => req<{ doc_id: string; title: string; regulator: string; source_url: string; pages: number; pages_text: number;
    pages_ocr: number; pages_excluded: number; excluded: { page: number; reason: string }[]; clauses: number;
    clauses_enabled: number; ocr_mean_conf: number | null }[]>("/kb/documents"),
  clauses: (q: string) => req<{ total: number; items: Clause[] }>(`/kb/clauses${q}`),
  clause: (id: string) => req<Clause>(`/kb/clauses/${encodeURIComponent(id)}`),
  setTags: (id: string, body: { claim_types: string[]; categories: string[]; surfaces: string[] }) =>
    req<Clause>(`/kb/clauses/${encodeURIComponent(id)}/tags`, json(body, "PATCH")),
  portfolio: () => req<{ heatmap: { types: string[]; rows: { brand: string; counts: Record<string, number> }[] };
    by_regulator: { regulator: string; count: number }[]; by_surface: { surface: string; risk: string; count: number }[];
    phrasings: { phrase: string; count: number; examples: string[] }[]; trend: { day: string; open?: number; resolved?: number }[] }>("/portfolio"),
  evalRuns: () => req<{ id: number; created_at: string; set_name: string; config: { ablate: string };
    metrics: Record<string, number | string | null> }[]>("/eval/runs"),
  evalRun: (id: number) => req<{ id: number; set_name: string; config: { ablate: string }; metrics: Record<string, unknown> }>(`/eval/runs/${id}`),
};

export const pageUrl = (doc: string, page: number) => `/api/kb/pages/${doc}/${page}.png`;

export const CLAIM_LABEL: Record<string, string> = {
  efficacy: "Efficacy", comparative: "Comparative", leadership: "Leadership / No.1", time_bound: "Time-bound",
  appearance: "Appearance", scientific: "Scientific / expert", environmental: "Environmental",
  natural_purity: "Natural / purity", nutrition_health: "Nutrition / health", awards_rankings: "Awards / rankings",
  pricing_offer: "Price / offer", celebrity_endorsement: "Celebrity endorsement", puffery: "Puffery",
  disclosure: "Ad disclosure", general_truthfulness: "General truthfulness", children: "Children", gender: "Gender",
};
export const SURFACES = { ecommerce: "E-commerce", quick_commerce: "Quick commerce", brand_site: "Brand site",
  social_post: "Social post" } as const;
export const CATEGORIES = { home: "Home care", beauty: "Beauty", personal: "Personal care", food: "Food & beverages" } as const;
