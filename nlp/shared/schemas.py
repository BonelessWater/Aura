"""
Pydantic schemas for all inter-component data contracts in Aura.

Every agent reads/writes these structures. All outputs are framed as
alignment scores and routing flags — never diagnoses.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class Cluster(str, Enum):
    SYSTEMIC   = "Systemic"
    GI         = "Gastrointestinal"
    ENDOCRINE  = "Endocrine"

class MarkerFlag(str, Enum):
    HIGH   = "HIGH"
    LOW    = "LOW"
    NORMAL = "NORMAL"

class Trend(str, Enum):
    STABLE     = "stable"
    ESCALATING = "escalating"
    RESOLVING  = "resolving"

class ModerationAction(str, Enum):
    SUPPRESS   = "SUPPRESS"
    FLAG       = "FLAG"
    ALLOW      = "ALLOW"
    DISCLAIMER = "DISCLAIMER"


# ── Thought Stream ─────────────────────────────────────────────────────────────

class ThoughtStreamEvent(BaseModel):
    agent:     str
    step:      str
    summary:   str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def log(self) -> None:
        import json
        print(json.dumps(self.model_dump(mode="json"), default=str))


# ── Extractor schemas ──────────────────────────────────────────────────────────

class MarkerValue(BaseModel):
    loinc_code:      Optional[str]  = None
    display_name:    str
    date:            str                          # ISO 8601: YYYY-MM-DD
    value:           float
    unit:            str
    ref_range_low:   Optional[float] = None
    ref_range_high:  Optional[float] = None
    flag:            MarkerFlag = MarkerFlag.NORMAL
    z_score_nhanes:  Optional[float] = None


class RatioTimepoint(BaseModel):
    date:  str
    value: float
    flag:  Optional[str] = None


class BioFingerprint(BaseModel):
    NLR:                    list[RatioTimepoint] = Field(default_factory=list)
    PLR:                    list[RatioTimepoint] = Field(default_factory=list)
    MLR:                    list[RatioTimepoint] = Field(default_factory=list)
    SII:                    list[RatioTimepoint] = Field(default_factory=list)
    CRP_Albumin:            list[RatioTimepoint] = Field(default_factory=list)
    C3_C4:                  list[RatioTimepoint] = Field(default_factory=list)
    ANA_titer_trend:        Optional[Trend]       = None
    sustained_abnormalities: list[str]            = Field(default_factory=list)
    morphological_shifts:    list[str]            = Field(default_factory=list)


class MarkerTimeline(BaseModel):
    loinc_code:   Optional[str]
    display_name: str
    values:       list[MarkerValue]
    trend:        Optional[Trend] = None


class LabReport(BaseModel):
    patient_id:          str
    markers:             list[MarkerTimeline]  = Field(default_factory=list)
    bio_fingerprint:     BioFingerprint        = Field(default_factory=BioFingerprint)
    thought_stream_event: Optional[ThoughtStreamEvent] = None


# ── Interviewer schemas ────────────────────────────────────────────────────────

class SymptomEntity(BaseModel):
    entity:           str
    location:         Optional[str]  = None
    duration_months:  Optional[int]  = None
    severity:         Optional[str]  = None
    onset:            Optional[str]  = None       # ISO 8601 partial date
    cluster_signal:   Optional[Cluster] = None
    snomed_concept:   Optional[str]  = None


class InterviewResult(BaseModel):
    patient_id:              str
    raw_text:                str
    symptoms:                list[SymptomEntity] = Field(default_factory=list)
    visual_keywords:         list[str]           = Field(default_factory=list)
    thought_stream_event:    Optional[ThoughtStreamEvent] = None

    @property
    def cluster_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {c.value: 0 for c in Cluster}
        for s in self.symptoms:
            if s.cluster_signal:
                counts[s.cluster_signal.value] += 1
        return counts


# ── Researcher schemas ─────────────────────────────────────────────────────────

class RetrievedPassage(BaseModel):
    chunk_id:    str
    doi:         Optional[str]
    journal:     Optional[str]
    year:        Optional[int]
    section:     Optional[str]
    cluster_tag: Optional[Cluster]
    text:        str
    score:       float


class ResearchResult(BaseModel):
    patient_id:           str
    sub_queries:          list[str]
    passages:             list[RetrievedPassage]   # top-10 after re-ranking
    thought_stream_event: Optional[ThoughtStreamEvent] = None


# ── Router schemas ─────────────────────────────────────────────────────────────

class DiseaseCandidate(BaseModel):
    disease:               str
    disease_alignment_score: float                # calibrated probability
    supporting_dois:       list[str]              = Field(default_factory=list)
    criteria_met:          list[str]              = Field(default_factory=list)
    criteria_count:        int                    = 0
    criteria_cap_applied:  bool                   = False
    drug_induced_flag:     bool                   = False


class RouterOutput(BaseModel):
    patient_id:             str
    cluster:                Cluster
    cluster_alignment_score: float                # calibrated probability
    routing_recommendation:  str                  # specialist type
    disease_candidates:      list[DiseaseCandidate]
    thought_stream_event:    Optional[ThoughtStreamEvent] = None


# ── Translator schemas ─────────────────────────────────────────────────────────

class TranslatorOutput(BaseModel):
    patient_id:              str
    soap_note:               str
    layman_compass:          str
    faithfulness_score:      float                # mean NLI score across sentences
    flagged_sentences:       list[str]            = Field(default_factory=list)
    fk_grade_level:          Optional[float]      = None
    thought_stream_event:    Optional[ThoughtStreamEvent] = None


# ── Moderator schemas ──────────────────────────────────────────────────────────

class ModerationResult(BaseModel):
    post_id:             str
    text:                str
    action:              ModerationAction
    confidence:          float
    extracted_drugs:     list[str]  = Field(default_factory=list)
    extracted_dosages:   list[str]  = Field(default_factory=list)
    reason:              Optional[str] = None
    thought_stream_event: Optional[ThoughtStreamEvent] = None


# ── Full patient bundle (passed between all agents) ────────────────────────────

class PatientBundle(BaseModel):
    """End-to-end container passed through the full Aura pipeline."""
    patient_id:        str
    lab_report:        Optional[LabReport]       = None
    interview_result:  Optional[InterviewResult] = None
    research_result:   Optional[ResearchResult]  = None
    router_output:     Optional[RouterOutput]    = None
    translator_output: Optional[TranslatorOutput] = None
