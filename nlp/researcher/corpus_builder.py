"""
Corpus Builder — The Researcher, Step 1.

Parses PMC .tar.gz archives (containing .nxml PubMed XML) into 256-token
sliding-window chunks (32-token overlap, sentence-boundary aware), and tags
each chunk with cluster signals.

Supports both:
  - .tar.gz archives (each contains a .nxml file) — standard PMC OA format
  - plain .txt files — legacy fallback

Usage (in Databricks notebook):
    from nlp.researcher.corpus_builder import iter_chunks
    from pathlib import Path

    files = sorted(Path("/Volumes/workspace/aura/pubmed_oa/articles").glob("*.tar.gz"))
    for chunk in iter_chunks(files=files):
        ...  # chunk dict: chunk_id, doi, journal, year, section, cluster_tag, text, pmc_id
"""

from __future__ import annotations

import hashlib
import logging
import re
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

PMC_DIR = Path(__file__).parents[2] / ".claude" / "data" / "pmc_autoimmune_oa" / "articles"

# Cluster keyword signals for chunk tagging
CLUSTER_KEYWORDS: dict[str, list[str]] = {
    "Systemic": [
        "lupus", "rheumatoid", "sjogren", "ankylosing", "psoriatic",
        "autoimmune", "antinuclear", "anti-dsDNA", "complement", "ANA",
        "NLR", "ESR", "CRP", "anti-CCP", "HLA-B27",
    ],
    "Gastrointestinal": [
        "inflammatory bowel", "crohn", "ulcerative colitis", "IBD",
        "calprotectin", "intestinal", "colonoscopy", "endoscopy",
        "celiac", "gluten", "microbiome",
    ],
    "Endocrine": [
        "hashimoto", "graves", "thyroid", "hypothyroid", "hyperthyroid",
        "diabetes", "adrenal", "cortisol", "insulin", "TSH", "T3", "T4",
    ],
}

CHUNK_TOKENS   = 256
OVERLAP_TOKENS = 32


# ── Text utilities ────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    return text.split()


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n{2,}", text) if s.strip()]


def _chunk_text(text: str) -> list[str]:
    sentences = _split_sentences(text)
    chunks:  list[str] = []
    current: list[str] = []
    cur_len  = 0

    for sent in sentences:
        words = _tokenize(sent)
        if cur_len + len(words) > CHUNK_TOKENS and current:
            chunks.append(" ".join(current))
            overlap = current[-OVERLAP_TOKENS:]
            current = overlap + words
            cur_len = len(current)
        else:
            current.extend(words)
            cur_len += len(words)

    if current:
        chunks.append(" ".join(current))
    return chunks


def _tag_cluster(text: str) -> Optional[str]:
    text_lower = text.lower()
    scores = {
        cluster: sum(1 for kw in keywords if kw.lower() in text_lower)
        for cluster, keywords in CLUSTER_KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def _chunk_id(doi: Optional[str], filename: str, idx: int) -> str:
    return hashlib.md5(f"{doi or filename}_{idx}".encode()).hexdigest()


# ── NXML parser ───────────────────────────────────────────────────────────────

# NXML uses a default namespace in some versions — strip it for clean tag matching
_NS_RE = re.compile(r"\{[^}]+\}")


def _strip_ns(tag: str) -> str:
    return _NS_RE.sub("", tag)


def _iter_text(element) -> str:
    """Recursively extract all inner text from an XML element."""
    parts = []
    if element.text:
        parts.append(element.text.strip())
    for child in element:
        parts.append(_iter_text(child))
        if child.tail:
            parts.append(child.tail.strip())
    return " ".join(p for p in parts if p)


def parse_nxml(nxml_bytes: bytes) -> dict:
    """
    Parse a PubMed Central NXML file and return a dict with:
      doi, pmc_id, journal, year, title, abstract, body_text
    Returns empty dict on parse failure.
    """
    try:
        root = ET.fromstring(nxml_bytes)
    except ET.ParseError as e:
        logger.warning(f"NXML parse error: {e}")
        return {}

    result: dict = {
        "doi": None, "pmc_id": None, "journal": None,
        "year": None, "title": None, "abstract": "", "body_text": "",
    }

    # ── Metadata ──────────────────────────────────────────────────────────────
    for elem in root.iter():
        tag = _strip_ns(elem.tag)

        if tag == "article-id":
            id_type = elem.get("pub-id-type", "")
            if id_type == "doi" and not result["doi"]:
                result["doi"] = (elem.text or "").strip()
            elif id_type == "pmc" and not result["pmc_id"]:
                result["pmc_id"] = (elem.text or "").strip()

        elif tag == "journal-title" and not result["journal"]:
            result["journal"] = (elem.text or "").strip()

        elif tag == "article-title" and not result["title"]:
            result["title"] = _iter_text(elem)

        elif tag == "year" and not result["year"]:
            try:
                result["year"] = int(elem.text or "")
            except (ValueError, TypeError):
                pass

    # ── Abstract ──────────────────────────────────────────────────────────────
    for abstract in root.iter():
        if _strip_ns(abstract.tag) == "abstract":
            result["abstract"] = _iter_text(abstract)
            break

    # ── Body text ─────────────────────────────────────────────────────────────
    body_parts = []
    for body in root.iter():
        if _strip_ns(body.tag) == "body":
            for elem in body.iter():
                if _strip_ns(elem.tag) in ("p", "title"):
                    text = _iter_text(elem).strip()
                    if text:
                        body_parts.append(text)
            break

    result["body_text"] = " ".join(body_parts)
    return result


# ── Article iterators ─────────────────────────────────────────────────────────

def _iter_from_tar(tar_path: Path) -> Iterator[dict]:
    """Yield chunk dicts from a single .tar.gz PMC archive."""
    try:
        with tarfile.open(tar_path, "r:gz") as tf:
            nxml_member = next(
                (m for m in tf.getmembers() if m.name.endswith(".nxml")), None
            )
            if not nxml_member:
                logger.warning(f"No .nxml in {tar_path.name}")
                return

            nxml_bytes = tf.extractfile(nxml_member).read()

    except Exception as e:
        logger.warning(f"Could not read {tar_path.name}: {e}")
        return

    meta = parse_nxml(nxml_bytes)
    if not meta:
        return

    # Combine abstract + body for chunking
    full_text = " ".join(filter(None, [meta.get("abstract"), meta.get("body_text")]))
    if not full_text.strip():
        return

    doi      = meta.get("doi")
    pmc_id   = meta.get("pmc_id") or tar_path.stem
    journal  = meta.get("journal")
    year     = meta.get("year")
    filename = tar_path.name

    for i, chunk_text in enumerate(_chunk_text(full_text)):
        yield {
            "chunk_id":    _chunk_id(doi, filename, i),
            "doi":         doi,
            "journal":     journal,
            "year":        year,
            "section":     "abstract" if i == 0 else f"body_{i}",
            "cluster_tag": _tag_cluster(chunk_text),
            "text":        chunk_text,
            "pmc_id":      pmc_id,
        }


def _iter_from_txt(txt_path: Path) -> Iterator[dict]:
    """Legacy: yield chunk dicts from a plain .txt file."""
    try:
        text = txt_path.read_text(errors="replace")
    except Exception as e:
        logger.warning(f"Could not read {txt_path}: {e}")
        return

    doi_m = re.search(r"doi:\s*(10\.\S+)", text, re.IGNORECASE)
    doi   = doi_m.group(1).rstrip(".),") if doi_m else None

    for i, chunk_text in enumerate(_chunk_text(text)):
        yield {
            "chunk_id":    _chunk_id(doi, txt_path.name, i),
            "doi":         doi,
            "journal":     None,
            "year":        None,
            "section":     f"chunk_{i}",
            "cluster_tag": _tag_cluster(chunk_text),
            "text":        chunk_text,
            "pmc_id":      txt_path.stem,
        }


def iter_chunks(
    files:   Optional[list[Path]] = None,
    pmc_dir: Optional[Path]       = None,
) -> Iterator[dict]:
    """
    Iterate over PMC article files, yielding chunk dicts.

    Args:
        files:   explicit list of file paths to process (preferred — lets caller
                 control ordering and resume filtering)
        pmc_dir: directory to glob for *.tar.gz and *.txt files (used when
                 `files` is not provided; defaults to local PMC_DIR)

    Each yielded dict has keys:
        chunk_id, doi, journal, year, section, cluster_tag, text, pmc_id
    """
    if files is None:
        root = pmc_dir or PMC_DIR
        files = sorted(root.glob("**/*.tar.gz")) + sorted(root.glob("**/*.txt"))
        logger.info(f"Found {len(files)} files in {root}")

    for path in files:
        if path.suffix == ".gz":
            yield from _iter_from_tar(path)
        else:
            yield from _iter_from_txt(path)
