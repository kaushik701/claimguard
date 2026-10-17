# Gold sets
- dev.jsonl (89 seed items): for prompt and rubric work. Relabel `expected_clauses` with real clause IDs after Day 2.
- holdout.jsonl (30 seed items, never tuned on): grow to 200 by Day 8. Kaushik labels; a second person labels
  the same items blind into holdout_labels_b.jsonl. Agents must never edit these files.
- retrieval_gold.jsonl (Day 3), copilot_gold.jsonl (Day 6), listings_golden/ (Day 4).
Item: {"id","text","context","surface","category","claim_type","risk","expected_clauses":[],"notes"}
