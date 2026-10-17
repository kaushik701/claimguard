You label clauses from Indian advertising regulations (ASCI Code and guidelines, CCPA greenwashing guidelines,
FSSAI Advertising and Claims Regulations 2018) so a retrieval system can find the right clause for a marketing
claim.

For EACH clause below, choose ALL labels that apply from these fixed lists. Do not invent labels.
claim_types: efficacy, comparative, leadership, time_bound, appearance, scientific, environmental,
  natural_purity, nutrition_health, disclosure, puffery, pricing_offer, celebrity_endorsement,
  awards_rankings, children, gender, general_truthfulness
categories: all, food, beauty, personal, home
surfaces: all, social_post, ecommerce, quick_commerce, brand_site, tv_print

Rules:
- "general_truthfulness" for broad clauses (truthful, substantiation, not misleading) that apply to any claim.
- categories = ["food"] only if the clause is specific to food/beverages; otherwise ["all"].
- surfaces = ["social_post"] only for influencer/creator-specific rules.
- If the clause is administrative (definitions of procedure, commencement, front matter), return empty lists
  and "administrative": true.

<<<INPUT
{clauses_block}
INPUT>>>
Return JSON: {"items": [{"clause_id": str, "claim_types": [...], "categories": [...], "surfaces": [...],
"administrative": bool, "rationale": "one sentence"}]}  (one item per clause, same clause_ids)
