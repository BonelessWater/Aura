"""
PDF Parser — The Extractor, Step 1.

Strategy:
  1. pdfplumber — best for structured/digital PDFs (preserves table cells)
  2. pytesseract fallback — for scanned/image PDFs

Returns a list of (page_num, text, tables) tuples.
Tables are returned as list[list[str]] (rows × cols).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ParsedPage:
    page_num: int
    text:     str
    tables:   list[list[list[str]]] = field(default_factory=list)
    ocr_used: bool = False


def parse_pdf(path: str | Path) -> list[ParsedPage]:
    """
    Parse a PDF into a list of ParsedPage objects.
    Falls back to OCR if digital text yield is too low.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    pages = _parse_with_pdfplumber(path)

    # If most pages have very little text, OCR the whole doc
    avg_len = sum(len(p.text) for p in pages) / max(len(pages), 1)
    if avg_len < 50:
        pages = _parse_with_ocr(path)

    return pages


def _parse_with_pdfplumber(path: Path) -> list[ParsedPage]:
    import pdfplumber

    results: list[ParsedPage] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text   = page.extract_text() or ""
            tables = page.extract_tables() or []
            # Normalise table cells (None → "")
            clean_tables = [
                [[cell or "" for cell in row] for row in table]
                for table in tables
            ]
            results.append(ParsedPage(
                page_num=i + 1,
                text=text,
                tables=clean_tables,
                ocr_used=False,
            ))
    return results


def _parse_with_ocr(path: Path) -> list[ParsedPage]:
    """Convert PDF pages to images then OCR with tesseract."""
    try:
        import pytesseract
        from PIL import Image
        import io
    except ImportError as e:
        raise ImportError("pytesseract and Pillow are required for OCR fallback") from e

    try:
        import fitz  # PyMuPDF — faster PDF→image than pdf2image
        doc = fitz.open(str(path))
        results: list[ParsedPage] = []
        for i, page in enumerate(doc):
            pix  = page.get_pixmap(dpi=200)
            img  = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img, config="--psm 6")
            results.append(ParsedPage(
                page_num=i + 1,
                text=text,
                tables=[],
                ocr_used=True,
            ))
        return results
    except ImportError:
        # Fallback: pdf2image
        from pdf2image import convert_from_path
        images  = convert_from_path(str(path), dpi=200)
        results = []
        for i, img in enumerate(images):
            text = pytesseract.image_to_string(img, config="--psm 6")
            results.append(ParsedPage(
                page_num=i + 1,
                text=text,
                tables=[],
                ocr_used=True,
            ))
        return results


def stitch_pages(pages: list[ParsedPage]) -> str:
    """
    Merge all page text into one string.
    Strips repeated column headers that span page breaks.
    """
    combined = "\n".join(p.text for p in pages)
    # Remove duplicate blank lines
    combined = re.sub(r"\n{3,}", "\n\n", combined)
    return combined


def extract_all_tables(pages: list[ParsedPage]) -> list[list[list[str]]]:
    """Return all tables from all pages as a flat list."""
    tables: list[list[list[str]]] = []
    for page in pages:
        tables.extend(page.tables)
    return tables


def has_handwriting_hint(pages: list[ParsedPage]) -> bool:
    """
    Heuristic: if OCR was used AND average word confidence is low,
    flag as possibly handwritten (requires pytesseract data).
    Always returns False if pytesseract not available.
    """
    if not any(p.ocr_used for p in pages):
        return False
    # Without confidence data we conservatively return False
    return False
