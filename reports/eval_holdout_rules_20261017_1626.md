# eval_holdout_rules_20261017_1626

| metric | value |
|---|---|
| n_items | 30 |
| detection_recall | 0.429 |
| non_claim_fp_rate | 0.5 |
| high_risk_precision | 0.889 |
| high_risk_recall | 0.471 |
| high_risk_f1 | 0.615 |
| risk_3class_accuracy | 0.5 |
| citation_accuracy | None |
| hallucinated_quote_rate_after_guard | 0.0 |
| pre_guard_bad_citation_rate | 0.0 |
| latency_p50_s | 0.01 |
| latency_p95_s | 0.05 |
| fallback_items | 0 |
| llm_calls | 0 |
| tokens_in | 0 |
| tokens_out | 0 |
| provider_fallbacks | 0 |
| cost_usd_per_item | 0.0 |
| partial | None |
| stopped | None |

## Disagreements

| id | text | gold | pred | cited |
|---|---|---|---|---|
| H-06 | Trusted by millions of Indian families. | medium | none |  |
| H-08 | See the difference in a week. | high | none |  |
| H-12 | Tested by experts. | medium | none |  |
| H-13 | Good for the planet, good for you. | high | none |  |
| H-15 | Zero-waste formula. | high | none |  |
| H-16 | Nature-pure, no harsh chemicals. | high | low |  |
| H-18 | Farm fresh flavour. | medium | none |  |
| H-19 | Helps build strong bones and muscles. | high | none |  |
| H-20 | Rich in antioxidants. | medium | none |  |
| H-21 | The ideal drink for growing kids' brain development. | high | none |  |
| H-23 | Shop now and save 20%. | none | high | ASCI-p19, ASCI-4.1 |
| H-24 | Controls dandruff from the very first use. | high | none |  |
| H-27 | India's No. 1 brand of ketchup (Kantar, value share, CY2025). | low | medium | FSSAI-4, FSSAI-p2-2 |
| H-28 | Non-toxic, safe for septic tanks. | high | none |  |
| H-30 | Dermat recommended for sensitive skin. | high | none |  |
