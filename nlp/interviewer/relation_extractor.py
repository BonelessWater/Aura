"""
Relation Extractor — The Interviewer, Step 3.

Links symptom entities to their context:
  symptom → body location
  symptom → duration
  symptom → severity

At hackathon scope: uses rule-based proximity extraction.
For production: replace with fine-tuned BiomedBERT relation classifier.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class SymptomRelation:
    symptom:        str
    location:       Optional[str] = None
    duration_text:  Optional[str] = None
    severity:       Optional[str] = None


_SEVERITY_TERMS = {
    "mild", "moderate", "severe", "extreme", "intense",
    "intermittent", "persistent", "chronic", "acute",
    "occasional", "constant", "worsening", "improving",
    "debilitating", "excruciating", "manageable",
}

_LOCATION_TERMS = {
    "knee", "knees", "hip", "hips", "shoulder", "shoulders",
    "wrist", "wrists", "ankle", "ankles", "finger", "fingers",
    "joint", "joints", "hand", "hands", "foot", "feet",
    "elbow", "elbows", "lower back", "upper back", "neck",
    "spine", "abdomen", "stomach", "chest", "face", "scalp",
    "skin", "bilateral", "left side", "right side", "both sides",
}

_DURATION_TRIGGERS = {"for", "since", "past", "last", "over the past", "over the last"}


def extract_relations(
    symptom_entities: list[dict],  # from ner_pipeline.extract_entities
    full_text: str,
) -> list[SymptomRelation]:
    """
    For each symptom entity, extract contextual relations
    from the surrounding sentence.

    Args:
        symptom_entities: list of {text, label, start, end}
        full_text:        original patient narrative

    Returns:
        list of SymptomRelation objects
    """
    # Segment text into sentences
    sentences = _split_sentences(full_text)
    relations = []

    disease_entities = [
        e for e in symptom_entities
        if e["label"] in ("DISEASE", "SYMPTOM", "PROBLEM")
    ]

    for entity in disease_entities:
        # Find the sentence containing this entity
        sentence = _find_containing_sentence(entity["start"], sentences, full_text)
        if not sentence:
            sentence = full_text

        rel = SymptomRelation(symptom=entity["text"])
        rel.severity       = _extract_severity(sentence)
        rel.location       = _extract_location(sentence, entity["text"])
        rel.duration_text  = _extract_duration_phrase(sentence)
        relations.append(rel)

    return relations


def _split_sentences(text: str) -> list[tuple[int, int]]:
    """Return list of (start, end) character offsets per sentence."""
    boundaries = [0]
    for m in re.finditer(r"[.!?]\s+", text):
        boundaries.append(m.end())
    boundaries.append(len(text))
    return [(boundaries[i], boundaries[i+1]) for i in range(len(boundaries)-1)]


def _find_containing_sentence(
    char_offset: int,
    sentences: list[tuple[int, int]],
    text: str,
) -> Optional[str]:
    for start, end in sentences:
        if start <= char_offset < end:
            return text[start:end].strip()
    return None


def _extract_severity(sentence: str) -> Optional[str]:
    s_lower = sentence.lower()
    for term in _SEVERITY_TERMS:
        if term in s_lower:
            return term
    return None


def _extract_location(sentence: str, symptom: str) -> Optional[str]:
    s_lower = sentence.lower()
    # Look for location terms near the symptom mention
    sym_pos = s_lower.find(symptom.lower())
    window  = s_lower[max(0, sym_pos - 40): sym_pos + 40]
    for loc in sorted(_LOCATION_TERMS, key=len, reverse=True):
        if loc in window:
            return loc
    return None


def _extract_duration_phrase(sentence: str) -> Optional[str]:
    s_lower = sentence.lower()
    patterns = [
        r"for\s+(?:\d+|several|few|many)\s+(?:days?|weeks?|months?|years?)",
        r"since\s+\w+(?:\s+\d{4})?",
        r"(?:past|last)\s+\d+\s+(?:days?|weeks?|months?|years?)",
        r"over\s+(?:the\s+)?(?:past|last)\s+\d+\s+(?:days?|weeks?|months?|years?)",
    ]
    for pat in patterns:
        m = re.search(pat, s_lower)
        if m:
            return m.group(0)
    return None
