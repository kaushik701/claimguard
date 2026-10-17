"""Claim taxonomy: types, trigger patterns, qualifier detection.

Order of PRIORITY decides the primary type when a sentence matches several.
"""
from __future__ import annotations

import re

_F = re.IGNORECASE

CLAIM_TYPES: dict[str, dict] = {
    "nutrition_health": {
        "description": "Nutrient content or health-function claims on foods and beverages.",
        "patterns": [
            r"\bhealth\s*drinks?\b", r"\bimmunity\b", r"\bboosts?\s+(immunity|growth|brain|memory|energy|stamina)",
            r"\btaller\b", r"\bsharper\b", r"\b(improves?|enhances?)\s+(memory|concentration|focus|digestion)",
            r"\bhigh\s+(in\s+)?(protein|fibre|fiber|calcium)\b", r"\bsource\s+of\b.*\b(vitamins?|nutrients?|protein|calcium|iron)\b",
            r"\bvital\s+nutrients\b", r"\bsugar[- ]free\b", r"\blow[- ](fat|sugar|sodium|calorie)\b", r"\bcholesterol\b",
        ],
    },
    "environmental": {
        "description": "Green / environmental / sustainability claims.",
        "patterns": [
            r"\beco[- ]?friendly\b", r"\benvironment(ally)?[- ]friendly\b", r"\bplanet[- ]friendly\b", r"\bearth[- ]friendly\b",
            r"\bsustainabl[ey]\b", r"\bbiodegradab", r"\bcompostab", r"\brecyclab", r"\brecycled\b",
            r"\bplastic[- ](free|neutral)\b", r"\bcarbon[- ]neutral\b", r"\bnet[- ]zero\b", r"\bgreen(er)?\s+(choice|product|formula|planet|cleaning)\b",
            r"\bgo(ing)?\s+green\b", r"\bkind\s+to\s+(rivers|the\s+planet|nature|the\s+environment)\b",
        ],
    },
    "leadership": {
        "description": "Market leadership / No.1 / most-trusted claims.",
        "patterns": [
            r"\bno\.?\s?1\b", r"\bnumber\s+one\b", r"#\s?1\b", r"\bmost\s+(trusted|recommended|preferred|loved)\b",
            r"\bleading\s+brand\b", r"\bbest[- ]selling\b", r"\bmarket\s+leader\b", r"\b(india|world)'?s\s+(largest|favourite|favorite)\b",
        ],
    },
    "comparative": {
        "description": "Comparisons with competitors, 'ordinary' products or prior formulas.",
        "patterns": [
            r"\b(better|faster|stronger|whiter|brighter|cleaner|softer|longer|more\s+\w+|less\s+\w+)\s+than\b",
            r"\bvs\.?\s", r"\bversus\b", r"\bcompared\s+(to|with)\b",
            r"\b\d+(\.\d+)?\s?(x|times)\s+(more|better|faster|stronger|whiter|longer)\b",
            r"\bordinary\s+(soaps?|detergents?|powders?|toothpastes?|creams?|sunscreens?|shampoos?|bars?)\b",
            r"\bother\s+(leading\s+)?brands?\b", r"\bunlike\s+other\b",
        ],
    },
    "efficacy": {
        "description": "Performance/efficacy claims (germ-kill, stain removal, protection duration).",
        "patterns": [
            r"\b\d{1,3}(\.\d+)?\s?%(?!\s*(natural|pure|organic|recycled|biodegradab|less\s+plastic|vegan))", r"\bspf\s?\d+", r"\bpa\+{1,4}", r"\b\d+\s?(x|times)\b(?!\s*\d)", r"\b\d+[- ]?(hour|hr)s?\b",
            r"\b(kills?|removes?|fights?|eliminates?|destroys?)\b.*\b(germs?|bacteria|virus(es)?|stains?|plaque|odou?r|dandruff)\b",
            r"\bprotects?\s+(you\s+)?(against|from)\b", r"\b(complete|total|all[- ]round)\s+protection\b",
        ],
    },
    "appearance": {
        "description": "Skin/teeth/hair appearance transformation incl. fairness/whitening.",
        "patterns": [
            r"\bfair(er|ness)\b", r"\bwhiten(s|ing)?\b", r"\blighter\b.*\bskin\b", r"\blighten(s|ing)?\b",
            r"\bdark\s+spots?\b", r"\beven[- ]ton", r"\bglow(ing)?\b.*\bskin\b", r"\b\d+\s+shades?\b",
        ],
    },
    "time_bound": {
        "description": "Results promised within a time or number of uses.",
        "patterns": [
            r"\b(in|within|after)\s+(just\s+)?\d+\s+(seconds?|minutes?|hours?|days?|weeks?|wash(es)?|uses?|applications?)\b",
            r"\binstant(ly)?\b", r"\bovernight\b",
        ],
    },
    "scientific": {
        "description": "Clinical/scientific/expert endorsement claims.",
        "patterns": [
            r"\b(clinically|scientifically|dermatologically)\b", r"\b(lab|laboratory)[- ]tested\b",
            r"\b(dermatologists?|dentists?|doctors?|paediatricians?|pediatricians?)\b", r"\b(recommended|approved|endorsed)\s+by\b",
            r"\bproven\b",
        ],
    },
    "natural_purity": {
        "description": "Natural / pure / free-from / authenticity claims.",
        "patterns": [
            r"\bnatural(ly)?\b", r"\bpure\b", r"\borganic\b", r"\bherbal\b", r"\bayurvedic\b",
            r"\b(chemical|toxin|paraben|sulphate|sulfate|preservative)[- ]free\b", r"\bno\s+(chemicals|toxins|preservatives)\b",
            r"\bauthentic\b", r"\bgenuine\b", r"\btraditional\b",
            r"\breal\s+(fruit|milk|tomato(es)?|cocoa|honey|ginger|tulsi|herbs?|malt)\b", r"\bfresh\s+(milk|fruit|ingredients)\b",
        ],
    },
    "puffery": {
        "description": "Subjective, non-measurable praise (generally permitted).",
        "patterns": [
            r"\b(best|finest|softest|smoothest|ultimate|amazing|unbeatable|incredible|perfect|irresistible|delightful)\b",
        ],
    },
}

PRIORITY = [
    "nutrition_health", "environmental", "leadership", "comparative", "efficacy",
    "appearance", "time_bound", "scientific", "natural_purity", "puffery",
]

_COMPILED = {t: [re.compile(p, _F) for p in CLAIM_TYPES[t]["patterns"]] for t in PRIORITY}

QUALIFIER = re.compile(
    r"(\bas per\b|\baccording to\b|\bbased on\b|\bsource\s*:|\blab(oratory)?\s+(tests?|stud(y|ies)|conditions)\b|"
    r"\bin[- ]lab\b|\btested\s+(on|against|with)\b|\bclinical\s+(study|trial)\b|\bconsumer\s+(study|test|survey)\b|"
    r"\bstudy\s+(on|of|with)\b|\bindependent\s+(study|test|lab|clinical)\b|\bresults?\s+(may\s+)?vary\b|"
    r"\bwhen\s+used\s+as\s+directed\b|\bt\s*&\s*c\b|\bconditions\s+apply\b|\bn\s*=\s*\d+|"
    r"\b\d+\s+(participants|subjects|people|women|men|users)\b|\bnielsen\b|\bkantar\b|\biqvia\b|\bqr\s+code\b|"
    r"\bcertified\s+by\b|\bcertification\b|\bfssai[- ]permitted\b|\bexcluding\b|\bfacilities\s+exist\b|"
    r"\bcontribute[s]?\s+to\s+normal\b|\binternal\s+(study|formulation|data)\b|\bmat\s+\w+\s+(19|20)\d{2}\b)",
    _F,
)
YEAR = re.compile(r"\b(19|20)\d{2}\b")


def classify(sentence: str) -> str | None:
    for t in PRIORITY:
        if any(p.search(sentence) for p in _COMPILED[t]):
            return t
    return None


def matched_types(sentence: str) -> list[str]:
    return [t for t in PRIORITY if any(p.search(sentence) for p in _COMPILED[t])]
