"""
NER Pipeline — The Interviewer, Step 1.

Extracts clinical entities from free-text patient narratives using:
  - scispaCy (en_core_sci_lg + en_ner_bc5cdr_md)
  - Custom EntityRuler for duration phrases and severity qualifiers
  - Fine-tuned on BC5CDR + NCBI Disease (HuggingFace bigbio datasets)

GPU requirement: training only. Inference runs on CPU.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── EntityRuler patterns ──────────────────────────────────────────────────────

DURATION_PATTERNS = [
    # "for 3 months", "for six weeks", "for about 2 years"
    {"label": "DURATION", "pattern": [
        {"LOWER": "for"},
        {"IS_DIGIT": True, "OP": "?"},
        {"LOWER": {"IN": ["one","two","three","four","five","six","seven","eight",
                           "nine","ten","several","few","many","about"]}, "OP": "?"},
        {"IS_DIGIT": True, "OP": "?"},
        {"LOWER": {"IN": ["day","days","week","weeks","month","months","year","years"]}},
    ]},
    # "since January 2022", "since last year"
    {"label": "DURATION", "pattern": [
        {"LOWER": "since"},
        {"OP": "+"},
    ]},
    # "past 3 months", "last 6 weeks"
    {"label": "DURATION", "pattern": [
        {"LOWER": {"IN": ["past","last","over","the last","the past"]}},
        {"IS_DIGIT": True, "OP": "?"},
        {"LOWER": {"IN": ["day","days","week","weeks","month","months","year","years"]}},
    ]},
]

SEVERITY_PATTERNS = [
    {"label": "SEVERITY", "pattern": [{"LOWER": {"IN": [
        "mild", "moderate", "severe", "extreme", "intense",
        "intermittent", "persistent", "chronic", "acute",
        "occasional", "constant", "worsening", "improving",
        "debilitating", "excruciating",
    ]}}]},
]

BODY_LOCATION_PATTERNS = [
    {"label": "LOCATION", "pattern": [
        {"LOWER": {"IN": ["bilateral","left","right","both","diffuse","generalized"]}},
        {"OP": "?"},
        {"LOWER": {"IN": [
            "knee","knees","hip","hips","shoulder","shoulders",
            "wrist","wrists","ankle","ankles","finger","fingers",
            "joint","joints","hand","hands","foot","feet",
            "elbow","elbows","lower back","upper back","neck",
        ]}},
    ]},
]


def build_spacy_pipeline(model: str = "en_core_sci_lg"):
    """
    Build and return a spaCy NLP pipeline with:
      - scispaCy base model (en_core_sci_lg or en_ner_bc5cdr_md)
      - Custom EntityRuler for duration/severity/location
    """
    try:
        import spacy
    except ImportError:
        raise ImportError("spacy is required: pip install spacy")

    try:
        nlp = spacy.load(model)
        logger.info(f"Loaded spaCy model: {model}")
    except OSError:
        logger.warning(
            f"Model '{model}' not found. "
            f"Install with: pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/"
            f"releases/v0.5.4/{model}-0.5.4.tar.gz"
        )
        # Fall back to a blank English pipeline
        import spacy
        nlp = spacy.blank("en")

    # Add EntityRuler before the existing NER component
    ruler_name = "entity_ruler"
    if ruler_name not in nlp.pipe_names:
        ruler = nlp.add_pipe("entity_ruler", before="ner" if "ner" in nlp.pipe_names else "last")
        ruler.add_patterns(DURATION_PATTERNS + SEVERITY_PATTERNS + BODY_LOCATION_PATTERNS)

    return nlp


NER_AZURE_SYSTEM_PROMPT = (
    "You are a clinical NER system. Extract named entities from the text.\n"
    "For each entity, return a JSON array of objects with:\n"
    '- "text": the exact span from the input\n'
    '- "label": one of DISEASE, CHEMICAL, DURATION, SEVERITY, LOCATION\n\n'
    "Rules:\n"
    "- DISEASE: conditions, diagnoses, disease names\n"
    "- CHEMICAL: drugs, medications, supplements\n"
    "- DURATION: time periods (e.g., 'for 3 months', 'since January')\n"
    "- SEVERITY: qualifiers (mild, moderate, severe, chronic, acute, etc.)\n"
    "- LOCATION: body parts, anatomical locations\n"
    "Return ONLY a JSON array. No other text."
)


def _extract_entities_azure(text: str) -> list[dict]:
    """Extract entities using Azure OpenAI instead of scispaCy."""
    import json as _json

    from nlp.shared.azure_client import get_azure_nlp_client

    client = get_azure_nlp_client()
    raw = client.chat(
        deployment="nano",
        messages=[
            {"role": "system", "content": NER_AZURE_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0,
        max_tokens=800,
    )
    if not raw:
        return []

    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        items = _json.loads(raw)
    except (_json.JSONDecodeError, ValueError):
        logger.warning("Azure NER returned non-JSON: %s", raw[:200])
        return []

    entities = []
    for item in items:
        ent_text = item.get("text", "")
        label = item.get("label", "")
        if not ent_text or not label:
            continue
        start = text.find(ent_text)
        end = start + len(ent_text) if start >= 0 else -1
        entities.append({"text": ent_text, "label": label, "start": start, "end": end})
    return entities


def extract_entities(text: str, nlp=None) -> list[dict]:
    """
    Extract named entities from text.

    Returns a list of dicts:
      {text, label, start, end}
    Where label is one of: DISEASE, CHEMICAL, DURATION, SEVERITY, LOCATION, etc.

    Uses Azure OpenAI when AURA_NLP_BACKEND=azure, otherwise local scispaCy.
    """
    from nlp.shared.azure_client import get_nlp_backend

    if get_nlp_backend("ner") == "azure":
        return _extract_entities_azure(text)

    if nlp is None:
        nlp = _get_default_pipeline()

    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        entities.append({
            "text":  ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end":   ent.end_char,
        })
    return entities


# ── Fine-tuning (run offline, GPU recommended) ───────────────────────────────

def finetune_ner(
    output_dir: str = "models/ner_bc5cdr",
    train_epochs: int = 5,
):
    """
    Fine-tune scispaCy NER on BC5CDR + NCBI Disease datasets.

    Streams data directly from HuggingFace (no download required).
    Requires a GPU for practical training speed.

    Args:
        output_dir: Where to save the fine-tuned model
        train_epochs: Number of training epochs
    """
    try:
        from datasets import load_dataset
        import spacy
        from spacy.tokens import DocBin
        from spacy.training import Example
    except ImportError as e:
        raise ImportError("datasets and spacy required for fine-tuning") from e

    logger.info("Loading BC5CDR from HuggingFace...")
    bc5cdr = load_dataset("bigbio/bc5cdr", name="bc5cdr_bigbio_ner", trust_remote_code=True)

    logger.info("Loading NCBI Disease from HuggingFace...")
    ncbi = load_dataset("bigbio/ncbi_disease", name="ncbi_disease_bigbio_ner", trust_remote_code=True)

    nlp = build_spacy_pipeline("en_core_sci_lg")

    def hf_to_spacy_examples(dataset_split):
        """Convert HuggingFace NER dataset to spaCy training examples."""
        examples = []
        for item in dataset_split:
            tokens = item["tokens"]
            text   = " ".join(tokens)
            doc    = nlp.make_doc(text)
            ents   = []
            offset = 0
            for i, token in enumerate(tokens):
                entity_type = item["ner_tags"][i] if "ner_tags" in item else None
                offset += len(token) + 1  # +1 for space
            # Use entity spans if available
            if "entities" in item:
                for entity in item["entities"]:
                    start = entity.get("offsets", [[0]])[0][0]
                    end   = entity.get("offsets", [[0, 0]])[0][1]
                    label = entity.get("type", "DISEASE")
                    ents.append((start, end, label))
            doc.ents = spacy.util.filter_spans([doc.char_span(s, e, l) for s, e, l in ents if doc.char_span(s, e, l)])
            examples.append(Example.from_dict(doc, {"entities": [(e.start_char, e.end_char, e.label_) for e in doc.ents]}))
        return examples

    train_data = (
        hf_to_spacy_examples(bc5cdr["train"]) +
        hf_to_spacy_examples(ncbi["train"])
    )

    # Disable other pipes during training
    other_pipes = [p for p in nlp.pipe_names if p != "ner"]
    with nlp.disable_pipes(*other_pipes):
        optimizer = nlp.begin_training()
        import random
        for epoch in range(train_epochs):
            random.shuffle(train_data)
            losses: dict = {}
            for batch in spacy.util.minibatch(train_data, size=32):
                nlp.update(batch, sgd=optimizer, losses=losses)
            logger.info(f"Epoch {epoch+1}/{train_epochs} — NER loss: {losses.get('ner', 0):.4f}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(out)
    logger.info(f"Fine-tuned NER model saved to {out}")


# ── Singleton pipeline ────────────────────────────────────────────────────────

_pipeline = None

def _get_default_pipeline():
    global _pipeline
    if _pipeline is None:
        # Try fine-tuned model first
        ft_path = Path("models/ner_bc5cdr")
        if ft_path.exists():
            import spacy
            _pipeline = spacy.load(str(ft_path))
            logger.info("Loaded fine-tuned NER model")
        else:
            _pipeline = build_spacy_pipeline("en_core_sci_lg")
    return _pipeline
