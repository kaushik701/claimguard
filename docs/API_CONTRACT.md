# API contract (frozen at end of Day 2 as `frontend/src/api/openapi.json`)

Base: `/api`. JSON unless noted. Errors: `{"error": {"code": str, "message": str}}`.

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/health` | | `{status, providers: {groq: ok|missing|error, gemini: …}, kb: {built_at, docs, clauses}}` |
| POST | `/audits` | multipart: `input_type` (text|html|pdf|image), `text?`, `file?`, `surface`, `category`, `brand?`, `paid` | `{audit_id}` |
| GET | `/audits/{id}/events` | SSE | events: `step` {name, status, ms}, `done` {audit_id}, `error` |
| GET | `/audits/{id}` | | `Audit` (input text, image_url?, ocr_boxes?, claims[], flags[] with citations, not_covered[], low_risk[], dropped[], stats, latency, cost) |
| GET | `/audits` | `?limit&brand&surface` | list of audit summaries |
| PATCH | `/flags/{id}` | `{action: accept|dismiss|escalate|set_risk, risk?, reason_code?, note?, reviewer?}` | updated `Flag` |
| GET | `/flags` | `?status&risk&claim_type&regulator&surface&brand&min_conf&max_conf` | `Flag[]` (review queue) |
| POST | `/preflight` | `{text, surface, category, paid}` | `{verdict: revise|check|clear, flags[]}` (synchronous, ≤ 30 s) |
| POST | `/ask` | `{session_id?, message}` | `{session_id, answer, citations[{n, clause_id, doc, page, quote}], covered}` |
| GET | `/kb/documents` | | `Document[]` with build stats |
| GET | `/kb/clauses` | `?q&doc&tag&page` | `Clause[]` (paged) |
| GET | `/kb/clauses/{clause_id}` | | `Clause` + `stats {used_in, accept_rate}` + `page_image_url` |
| PATCH | `/kb/clauses/{clause_id}/tags` | `{claim_types[], categories[], surfaces[]}` | writes overrides; returns `Clause` |
| GET | `/kb/pages/{doc_id}/{page}.png` | | page image |
| GET | `/portfolio` | | heatmap rows, by_regulator, by_surface, phrasings clusters, trend |
| GET | `/eval/runs` | | `EvalRun[]` |
| GET | `/eval/runs/{id}` | | metrics, per-type confusion, ablations, reliability bins |
| GET | `/reports/{audit_id}.html` | | printable report |

## Core types
```ts
type Risk = "high" | "medium" | "low";
interface Citation { clause_id: string; doc_id: string; doc_title: string; section_path: string;
  number: string | null; page: number; quote: string; source: "text" | "ocr" | "vision"; ocr_conf?: number }
interface Claim { id: string; text: string; start: number; end: number; claim_type: string;
  source: "llm" | "rule" | "both" }
interface Flag { id: string; claim: Claim; risk: Risk; reason: string; rewrite: string | null;
  confidence: number | null; verifier_note: string | null; citations: Citation[];
  status: "open" | "accepted" | "dismissed" | "escalated"; reviewer_risk: Risk | null; reviewer_note: string | null }
```
