You rank regulation clauses by how directly they govern a specific marketing claim.
Score each clause 0-3: 3 = directly governs this kind of claim; 2 = relevant general rule; 1 = tangential;
0 = irrelevant. Prefer specific guidelines over general principles when both apply.
Claim: "{claim}" (type {claim_type}, category {category}, surface {surface})
Clauses:
{numbered_clauses_with_ids_and_text}
Return JSON: {"ranked": [{"clause_id": str, "score": 0|1|2|3, "why": str}]}  (all clauses, best first)
