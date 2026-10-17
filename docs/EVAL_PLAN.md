# Evaluation plan

## Datasets (`data/gold/`)
| File | Size | Use | Rule |
|---|---|---|---|
| `dev.jsonl` | ~120 claims | Prompt/rubric development, few-shot source | Anyone may look |
| `holdout.jsonl` | 200 claims | Reported numbers only | Never used for prompts, examples or tags; CI fails if a holdout string appears in prompts/ or memory |
| `holdout_labels_b.jsonl` | 200 | Second labeller (blind) | Cohen's κ reported |
| `retrieval_gold.jsonl` | 100 claims → expected clause_ids | Retrieval recall@k | Built from KB after Day 2 |
| `copilot_gold.jsonl` | 40 questions → expected clause_ids + "covered" | Copilot | Includes 10 out-of-scope questions |
| `listings_golden/` | 12 full listings/captions/pack images | End-to-end regression | Recorded LLM outputs for CI |

Item format: `{"id", "text", "context", "surface", "category", "claim_type", "risk": high|medium|low|none,
"expected_clauses": [...], "notes"}`. Write items in the way real listings and creators phrase things;
include Hinglish (~10%), footnotes, multi-claim sentences, puffery, and non-claims.

## Metrics
| Metric | Target | Notes |
|---|---|---|
| Claim detection recall | ≥ 0.90 | per item |
| Non-claim false-positive rate | ≤ 0.10 | |
| High-risk precision / recall / F1 | ≥ 0.85 / ≥ 0.75 / – | headline numbers |
| 3-class risk accuracy | report | |
| Citation accuracy | ≥ 0.90 | any cited clause ∈ expected_clauses |
| Hallucinated quote rate | 0 | after citation guard (pre-guard rate also reported) |
| Retrieval recall@5 | ≥ 0.85 | |
| Copilot: grounded answer rate / correct refusal rate | ≥ 0.90 / ≥ 0.90 | |
| Calibration (ECE) | report | reliability diagram |
| Latency p50/p95 | p95 < 20 s | per listing |
| Cost per listing | < US$0.01 | priced from config |
| Inter-annotator κ | report | if < 0.6, show uncertainty in UI |

## Ablations (shown on the Eval page)
rules only · LLM without rule safety net · no reranker · BM25 only · dense only · no verifier · no few-shot
memory · no query expansion.

## Commands
```
python -m claimguard.eval run --set holdout --config default
python -m claimguard.eval run --set holdout --ablate verifier
python -m claimguard.eval retrieval
python -m claimguard.eval copilot
python -m claimguard.eval kappa
```
Each run writes `reports/eval_<set>_<config>_<date>.{json,md}` and a row in `eval_runs`.
