"""
NER Extractor — The Moderator, Stage 2.

Only triggered on posts classified as 'potentially_harmful'.
Extracts drug names and dosage patterns to make the SUPPRESS/FLAG/ALLOW decision.

Uses scispaCy + en_ner_bc5cdr_md for drug/disease NER.
Custom EntityRuler for dosage patterns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModerationEntities:
    drugs:    list[str] = field(default_factory=list)
    dosages:  list[str] = field(default_factory=list)
    diseases: list[str] = field(default_factory=list)


# ── Dosage pattern regex ──────────────────────────────────────────────────────

_DOSAGE_PATTERNS = [
    r"\d+\s*mg(?:/day|/week|/kg)?",          # "500mg/day"
    r"\d+\s*mcg(?:/day|/week)?",             # "50mcg"
    r"\d+\s*g(?:/day)?",                     # "2g/day"
    r"\d+\s*(?:tablets?|capsules?|pills?)",  # "2 tablets"
    r"(?:take|taking|took)\s+\d+",           # "take 3"
    r"dose\s+of\s+\d+",                      # "dose of 200"
    r"\d+\s*IU",                             # "1000 IU"
    r"\d+\s*ml(?:/day)?",                    # "10ml"
]

_DOSAGE_RE = re.compile("|".join(_DOSAGE_PATTERNS), re.IGNORECASE)


def extract_moderation_entities(text: str) -> ModerationEntities:
    """
    Extract drugs, dosages, and diseases from a forum post.
    Uses scispaCy if available; falls back to regex-only.
    """
    result = ModerationEntities()

    # ── Dosage extraction (regex — fast, no model needed) ──────────────────
    dosage_matches = _DOSAGE_RE.findall(text)
    result.dosages = [m.strip() for m in dosage_matches if m.strip()]

    # ── NER for drugs and diseases ─────────────────────────────────────────
    try:
        import spacy
        nlp = _get_moderation_nlp()
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("CHEMICAL", "DRUG"):
                result.drugs.append(ent.text)
            elif ent.label_ == "DISEASE":
                result.diseases.append(ent.text)
    except Exception:
        # Fallback: simple known-drug regex list
        result.drugs = _regex_drug_extract(text)

    # Deduplicate
    result.drugs    = list(set(result.drugs))
    result.diseases = list(set(result.diseases))
    return result


def decide_action(entities: ModerationEntities) -> tuple[str, str]:
    """
    Apply decision logic:
      drug + specific dosage → SUPPRESS + warning
      drug + general mention (no dosage) → FLAG
      anecdotal claim, no dosage → ALLOW + DISCLAIMER

    Returns (action, reason).
    """
    has_drug   = bool(entities.drugs)
    has_dosage = bool(entities.dosages)

    if has_drug and has_dosage:
        return (
            "SUPPRESS",
            f"Post contains specific drug dosage recommendation: "
            f"{entities.drugs[:2]} at {entities.dosages[:2]}"
        )
    elif has_drug:
        return (
            "FLAG",
            f"Post mentions drug(s) without specific dosage: {entities.drugs[:3]}. "
            f"Queued for moderator review."
        )
    elif entities.diseases:
        return (
            "DISCLAIMER",
            "Post discusses medical conditions — automatic disclaimer appended."
        )
    else:
        return "ALLOW", "No harmful content detected."


# ── spaCy NLP for moderation (lazy load) ─────────────────────────────────────

_moderation_nlp = None


def _get_moderation_nlp():
    global _moderation_nlp
    if _moderation_nlp is not None:
        return _moderation_nlp

    import spacy
    try:
        _moderation_nlp = spacy.load("en_ner_bc5cdr_md")
    except OSError:
        try:
            _moderation_nlp = spacy.load("en_core_sci_lg")
        except OSError:
            _moderation_nlp = spacy.blank("en")

    # Add dosage EntityRuler
    ruler = _moderation_nlp.add_pipe(
        "entity_ruler", before="ner" if "ner" in _moderation_nlp.pipe_names else "last"
    )
    ruler.add_patterns([
        {"label": "DRUG", "pattern": [{"LOWER": {"IN": _KNOWN_DRUGS}}]},
    ])
    return _moderation_nlp


# ── Known drug list for regex fallback ───────────────────────────────────────

_KNOWN_DRUGS = {
    "prednisone", "prednisolone", "methotrexate", "hydroxychloroquine",
    "sulfasalazine", "leflunomide", "azathioprine", "mycophenolate",
    "rituximab", "belimumab", "tocilizumab", "baricitinib",
    "tofacitinib", "upadacitinib", "adalimumab", "etanercept",
    "infliximab", "certolizumab", "golimumab", "abatacept",
    "ibuprofen", "naproxen", "celecoxib", "aspirin",
    "levothyroxine", "methimazole", "propylthiouracil",
    "insulin", "metformin", "cyclosporine", "tacrolimus",
}


def _regex_drug_extract(text: str) -> list[str]:
    text_lower = text.lower()
    return [d for d in _KNOWN_DRUGS if d in text_lower]
