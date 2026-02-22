#!/usr/bin/env python3
"""
Aura Clinical AI Report Generator
Generates one clinical-style PDF per demo case JSON file.

Usage:
    conda run -n aura python modeling/presentation/generate_pdf_reports.py
"""

import json
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)

# ── Color Palette ────────────────────────────────────────────────────────────────
C_NAVY        = HexColor("#1B3A5C")
C_NAVY_LIGHT  = HexColor("#2D5F8F")
C_HEALTHY     = HexColor("#16A34A")
C_SYSTEMIC    = HexColor("#DC2626")
C_ENDOCRINE   = HexColor("#D97706")
C_GI          = HexColor("#7C3AED")
C_GRAY_BG     = HexColor("#F3F4F6")
C_GRAY_TEXT   = HexColor("#6B7280")
C_HIGH_BG     = HexColor("#FEE2E2")
C_LOW_BG      = HexColor("#DBEAFE")
C_MISSING_BG  = HexColor("#E5E7EB")
C_BORDER      = HexColor("#D1D5DB")
C_REC_BG      = HexColor("#EFF6FF")
C_WHITE       = colors.white
C_BLACK       = colors.black

CATEGORY_COLORS = {
    "healthy":         C_HEALTHY,
    "systemic":        C_SYSTEMIC,
    "endocrine":       C_ENDOCRINE,
    "gastrointestinal": C_GI,
}
CATEGORY_LABELS = {
    "healthy":         "Healthy",
    "systemic":        "Systemic Autoimmune",
    "endocrine":       "Endocrine Autoimmune",
    "gastrointestinal": "Gastrointestinal",
}

LAB_MARKERS = [
    ("wbc",           "WBC",        "White Blood Cell Count"),
    ("rbc",           "RBC",        "Red Blood Cell Count"),
    ("hemoglobin",    "Hemoglobin", "Hemoglobin"),
    ("hematocrit",    "Hematocrit", "Hematocrit"),
    ("platelet_count","Platelets",  "Platelet Count"),
    ("mcv",           "MCV",        "Mean Corpuscular Volume"),
    ("mch",           "MCH",        "Mean Corpuscular Hemoglobin"),
    ("rdw",           "RDW",        "Red Cell Distribution Width"),
    ("esr",           "ESR",        "Erythrocyte Sedimentation Rate"),
    ("crp",           "CRP",        "C-Reactive Protein"),
]

AUTOAB_MARKERS = [
    ("ana_status",  "ANA",          "Antinuclear Antibodies"),
    ("anti_dsdna",  "Anti-dsDNA",   "Anti-double stranded DNA"),
    ("hla_b27",     "HLA-B27",      "Human Leukocyte Antigen B27"),
    ("anti_sm",     "Anti-Sm",      "Anti-Smith"),
    ("anti_ro",     "Anti-Ro/SSA",  "Anti-Ro"),
    ("anti_la",     "Anti-La/SSB",  "Anti-La"),
    ("rf_status",   "RF",           "Rheumatoid Factor"),
    ("anti_ccp",    "Anti-CCP",     "Anti-Cyclic Citrullinated Peptide"),
    ("c3",          "C3",           "Complement C3"),
    ("c4",          "C4",           "Complement C4"),
]

AUTOAB_UNITS = {
    "rf_status": " IU/mL",
    "c3":        " mg/dL",
    "c4":        " mg/dL",
    "ana_status": "",
    "anti_dsdna": " IU/mL",
    "anti_ccp":   " U/mL",
}


# ── Style Factory ────────────────────────────────────────────────────────────────
def get_styles():
    s = {}
    s["title"] = ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=22,
        textColor=C_WHITE, leading=26,
    )
    s["subtitle"] = ParagraphStyle(
        "subtitle", fontName="Helvetica", fontSize=8,
        textColor=HexColor("#93C5FD"), leading=12,
    )
    s["header_right"] = ParagraphStyle(
        "header_right", fontName="Helvetica", fontSize=9,
        textColor=C_WHITE, alignment=TA_RIGHT, leading=13,
    )
    s["section_title"] = ParagraphStyle(
        "section_title", fontName="Helvetica-Bold", fontSize=10,
        textColor=C_NAVY, spaceBefore=4, spaceAfter=4,
        borderPad=2,
    )
    s["body"] = ParagraphStyle(
        "body", fontName="Helvetica", fontSize=9,
        textColor=C_BLACK, leading=13,
    )
    s["body_bold"] = ParagraphStyle(
        "body_bold", fontName="Helvetica-Bold", fontSize=9,
        textColor=C_BLACK, leading=13,
    )
    s["label"] = ParagraphStyle(
        "label", fontName="Helvetica", fontSize=7,
        textColor=C_GRAY_TEXT, leading=10,
    )
    s["value"] = ParagraphStyle(
        "value", fontName="Helvetica-Bold", fontSize=9,
        textColor=C_BLACK, leading=12,
    )
    s["badge"] = ParagraphStyle(
        "badge", fontName="Helvetica-Bold", fontSize=11,
        textColor=C_WHITE, alignment=TA_CENTER, leading=14,
    )
    s["disclaimer"] = ParagraphStyle(
        "disclaimer", fontName="Helvetica-Oblique", fontSize=6.5,
        textColor=C_GRAY_TEXT, alignment=TA_CENTER, leading=9,
    )
    s["recommended"] = ParagraphStyle(
        "recommended", fontName="Helvetica-Bold", fontSize=9,
        textColor=C_NAVY, leading=13,
    )
    s["th"] = ParagraphStyle(
        "th", fontName="Helvetica-Bold", fontSize=8,
        textColor=C_WHITE, alignment=TA_CENTER, leading=11,
    )
    s["th_left"] = ParagraphStyle(
        "th_left", fontName="Helvetica-Bold", fontSize=8,
        textColor=C_WHITE, alignment=TA_LEFT, leading=11,
    )
    s["td"] = ParagraphStyle(
        "td", fontName="Helvetica", fontSize=8,
        textColor=C_BLACK, alignment=TA_CENTER, leading=11,
    )
    s["td_left"] = ParagraphStyle(
        "td_left", fontName="Helvetica", fontSize=8,
        textColor=C_BLACK, alignment=TA_LEFT, leading=11,
    )
    s["td_muted"] = ParagraphStyle(
        "td_muted", fontName="Helvetica-Oblique", fontSize=8,
        textColor=C_GRAY_TEXT, alignment=TA_CENTER, leading=11,
    )
    s["correct_yes"] = ParagraphStyle(
        "correct_yes", fontName="Helvetica-Bold", fontSize=9,
        textColor=C_HEALTHY, leading=13,
    )
    s["correct_no"] = ParagraphStyle(
        "correct_no", fontName="Helvetica-Bold", fontSize=9,
        textColor=C_SYSTEMIC, leading=13,
    )
    return s


# ── Helpers ──────────────────────────────────────────────────────────────────────
def fmt_autoab(val, key):
    if val is None:
        return "Not Tested"
    if val == 0.0:
        return "Negative"
    if val == 1.0:
        return "Positive"
    unit = AUTOAB_UNITS.get(key, "")
    return f"{val:.1f}{unit}" if isinstance(val, float) else str(val)


def _kv_cell(label_text, value_text, styles, width):
    """Two-row inner table: label on top, value below."""
    inner = Table(
        [[Paragraph(label_text, styles["label"])],
         [Paragraph(str(value_text), styles["value"])]],
        colWidths=[width - 14],
    )
    inner.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return inner


# ── Section Builders ─────────────────────────────────────────────────────────────
def build_header(case, styles, W):
    meta = case["meta"]
    gen_str = ""
    try:
        dt = datetime.fromisoformat(meta["generated_at"].replace("Z", "+00:00"))
        gen_str = dt.strftime("%B %d, %Y  %H:%M UTC")
    except Exception:
        gen_str = meta.get("generated_at", "")

    left = [Paragraph("AURA", styles["title"]),
            Paragraph(meta.get("model", ""), styles["subtitle"])]
    right = [Paragraph("Clinical AI Report", styles["header_right"]),
             Paragraph(gen_str, styles["header_right"])]

    t = Table([[left, right]], colWidths=[W * 0.6, W * 0.4])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_NAVY),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (0,  -1), 16),
        ("RIGHTPADDING",  (-1, 0), (-1, -1), 16),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return t


def build_patient_section(case, styles, W):
    p = case["patient"]
    bmi = f"{p['bmi']:.1f}" if p.get("bmi") else "N/A"
    col_w = W / 4

    rows_data = [
        [("PATIENT ID",      p["patient_id"]),
         ("AGE",             p.get("age", "—")),
         ("SEX",             p.get("sex", "—")),
         ("BMI",             bmi)],
        [("SOURCE DATASET",  p.get("source_dataset", "—")),
         ("TRUE DIAGNOSIS",  p.get("true_diagnosis_raw", "—")),
         ("ICD-10",          p.get("true_diagnosis_icd10", "—")),
         ("CATEGORY",        p.get("true_diagnosis_cluster", "—").capitalize())],
    ]

    table_rows = []
    for row in rows_data:
        table_rows.append([_kv_cell(lbl, val, styles, col_w) for lbl, val in row])

    t = Table(table_rows, colWidths=[col_w] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_GRAY_BG),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def build_prediction_section(case, styles, W):
    pred = case["prediction"]
    cat  = pred["predicted_category"]
    cat_color = CATEGORY_COLORS.get(cat, C_NAVY)
    cat_label = CATEGORY_LABELS.get(cat, cat.capitalize())
    conf_pct  = f"{pred['category_confidence'] * 100:.1f}%"
    tier      = case["clinical_interpretation"].get("confidence_tier", "")
    correct   = case.get("correct", None)

    # ── Badge row ──
    badge_t = Table(
        [[Paragraph(cat_label.upper(), styles["badge"])]],
        colWidths=[W * 0.40],
    )
    badge_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), cat_color),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ]))

    correct_style = styles["correct_yes"] if correct else styles["correct_no"]
    correct_text  = "✓  CORRECT" if correct else "✗  INCORRECT"

    top_row = Table(
        [[badge_t,
          Paragraph(f"Confidence: <b>{conf_pct}</b>  ·  {tier}", styles["body"]),
          Paragraph(correct_text, correct_style)]],
        colWidths=[W * 0.42, W * 0.35, W * 0.23],
    )
    top_row.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # ── Category probabilities ──
    probs  = pred.get("category_probabilities", {})
    p_data = [[Paragraph("CATEGORY", styles["th_left"]),
               Paragraph("PROBABILITY", styles["th"])]]
    for cn, pv in sorted(probs.items(), key=lambda x: -x[1]):
        p_data.append([
            Paragraph(CATEGORY_LABELS.get(cn, cn.capitalize()), styles["td_left"]),
            Paragraph(f"{pv * 100:.1f}%", styles["td"]),
        ])
    prob_t = Table(p_data, colWidths=[W * 0.38, W * 0.16])
    ts_rows = [
        ("BACKGROUND",    (0, 0), (-1, 0), C_NAVY),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.25, C_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i, (cn, _) in enumerate(sorted(probs.items(), key=lambda x: -x[1]), 1):
        bg = C_GRAY_BG if i % 2 == 0 else C_WHITE
        ts_rows.append(("BACKGROUND", (0, i), (-1, i), bg))
    prob_t.setStyle(TableStyle(ts_rows))

    flowables = [
        Paragraph("SECTION 2: PREDICTION", styles["section_title"]),
        top_row,
        Spacer(1, 6),
        prob_t,
    ]

    if pred.get("predicted_disease"):
        dis_conf = pred.get("disease_confidence", 0)
        flowables += [
            Spacer(1, 5),
            Paragraph(
                f"<b>Predicted Disease:</b>  {pred['predicted_disease']} &nbsp;&nbsp;"
                f"<b>Disease Confidence:</b>  {dis_conf * 100:.1f}%",
                styles["body"],
            ),
        ]
    return flowables


def build_lab_panel(case, styles, W):
    lab = case.get("lab_panel", {})
    headers  = ["MARKER", "VALUE", "UNIT", "REF RANGE", "FLAG", "Z-SCORE"]
    col_widths = [W * 0.22, W * 0.09, W * 0.13, W * 0.18, W * 0.09, W * 0.14]

    data = [[Paragraph(h, styles["th"]) for h in headers]]
    ts = [
        ("BACKGROUND",    (0, 0), (-1, 0), C_NAVY),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.25, C_BORDER),
    ]
    # Left-align the first column header
    data[0][0] = Paragraph(headers[0], styles["th_left"])

    for i, (key, short, _) in enumerate(LAB_MARKERS, 1):
        m    = lab.get(key, {})
        flag = m.get("flag", "MISSING")
        val  = m.get("value")
        ordered = m.get("was_ordered", False)

        if flag == "MISSING" or not ordered:
            row = [
                Paragraph(short,     styles["td_muted"]),
                Paragraph("—",       styles["td_muted"]),
                Paragraph(m.get("unit", ""), styles["td_muted"]),
                Paragraph("—",       styles["td_muted"]),
                Paragraph("MISSING", styles["td_muted"]),
                Paragraph("—",       styles["td_muted"]),
            ]
            ts.append(("BACKGROUND", (0, i), (-1, i), C_MISSING_BG))
        else:
            val_s    = f"{val:.2f}".rstrip("0").rstrip(".") if isinstance(val, float) else str(val or "—")
            ref_low  = m.get("reference_low")
            ref_high = m.get("reference_high")
            ref_s    = (f"{ref_low}–{ref_high}"
                        if ref_low is not None and ref_high is not None else "—")
            z        = m.get("zscore")
            z_s      = f"{z:.2f}" if z is not None else "—"

            row = [
                Paragraph(short,   styles["td_left"]),
                Paragraph(val_s,   styles["td"]),
                Paragraph(m.get("unit", ""), styles["td"]),
                Paragraph(ref_s,   styles["td"]),
                Paragraph(flag,    styles["td"]),
                Paragraph(z_s,     styles["td"]),
            ]
            if flag == "H":
                ts.append(("BACKGROUND", (0, i), (-1, i), C_HIGH_BG))
            elif flag == "L":
                ts.append(("BACKGROUND", (0, i), (-1, i), C_LOW_BG))
            else:
                bg = C_GRAY_BG if i % 2 == 0 else C_WHITE
                ts.append(("BACKGROUND", (0, i), (-1, i), bg))

        data.append(row)

    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle(ts))
    return t


def build_autoab_section(case, styles, W):
    panel = case.get("autoantibody_panel")
    if panel is None:
        return []

    col_w = W / 2
    data  = [[Paragraph("MARKER",  styles["th_left"]),
              Paragraph("RESULT",  styles["th"])]]
    ts = [
        ("BACKGROUND",    (0, 0), (-1, 0), C_NAVY),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.25, C_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]

    for i, (key, short, _) in enumerate(AUTOAB_MARKERS, 1):
        val     = panel.get(key)
        val_str = fmt_autoab(val, key)
        muted   = val is None
        bg      = HexColor("#F9FAFB") if muted else (C_GRAY_BG if i % 2 == 0 else C_WHITE)
        ts.append(("BACKGROUND", (0, i), (-1, i), bg))
        data.append([
            Paragraph(short,   styles["td_left"]),
            Paragraph(val_str, styles["td_muted"] if muted else styles["td"]),
        ])

    t = Table(data, colWidths=[col_w, col_w])
    t.setStyle(TableStyle(ts))
    return [Paragraph("SECTION 4: AUTOANTIBODY PANEL", styles["section_title"]), t]


def build_interpretation_section(case, styles, W):
    interp   = case.get("clinical_interpretation", {})
    summary  = interp.get("summary", "")
    friendly = interp.get("patient_friendly", "")
    rec      = interp.get("recommended_action", "")

    summary_t = Table(
        [[Paragraph(summary, styles["body"])]],
        colWidths=[W],
    )
    summary_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_GRAY_BG),
        ("BOX",           (0, 0), (-1, -1), 0.75, C_BORDER),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    rec_t = Table(
        [[Paragraph(f"Recommended Action: {rec}", styles["recommended"])]],
        colWidths=[W],
    )
    rec_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_REC_BG),
        ("BOX",           (0, 0), (-1, -1), 1.5, C_NAVY),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    return [
        Paragraph("SECTION 5: CLINICAL INTERPRETATION", styles["section_title"]),
        Paragraph("<b>Summary</b>", styles["body_bold"]),
        Spacer(1, 3),
        summary_t,
        Spacer(1, 8),
        Paragraph("<b>Patient-Friendly Explanation</b>", styles["body_bold"]),
        Spacer(1, 3),
        Paragraph(friendly, styles["body"]),
        Spacer(1, 10),
        rec_t,
    ]


# ── PDF Assembly ─────────────────────────────────────────────────────────────────
def build_pdf(case, output_path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.85 * inch,
    )
    W = letter[0] - inch   # usable content width
    styles = get_styles()
    disclaimer = case["meta"].get("disclaimer", "")

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(C_BORDER)
        canvas.setLineWidth(0.5)
        y_line = 0.68 * inch
        canvas.line(0.5 * inch, y_line, letter[0] - 0.5 * inch, y_line)
        canvas.setFont("Helvetica-Oblique", 6.5)
        canvas.setFillColor(C_GRAY_TEXT)
        canvas.drawCentredString(letter[0] / 2, 0.50 * inch, disclaimer)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(
            letter[0] / 2, 0.34 * inch,
            f"Page {doc.page}  ·  Generated by Aura  ·  Not a clinical diagnosis",
        )
        canvas.restoreState()

    story = []

    # Header
    story.append(build_header(case, styles, W))
    story.append(Spacer(1, 10))

    # S1: Patient Demographics
    story.append(Paragraph("SECTION 1: PATIENT DEMOGRAPHICS", styles["section_title"]))
    story.append(build_patient_section(case, styles, W))
    story.append(Spacer(1, 12))

    # S2: Prediction
    story.extend(build_prediction_section(case, styles, W))
    story.append(Spacer(1, 12))

    # S3: Lab Panel
    story.append(Paragraph("SECTION 3: LAB PANEL", styles["section_title"]))
    story.append(build_lab_panel(case, styles, W))
    story.append(Spacer(1, 12))

    # S4: Autoantibody Panel (conditional)
    autoab = build_autoab_section(case, styles, W)
    if autoab:
        story.extend(autoab)
        story.append(Spacer(1, 12))

    # S5: Clinical Interpretation
    story.extend(build_interpretation_section(case, styles, W))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


# ── Entry Point ──────────────────────────────────────────────────────────────────
def main():
    base_dir   = Path(__file__).parent / "demo_cases"
    output_dir = base_dir / "pdfs"
    output_dir.mkdir(exist_ok=True)

    skip = {"case_ids.json", "all_cases_summary.json"}
    case_files = sorted(f for f in base_dir.glob("case_*.json") if f.name not in skip)

    print(f"Found {len(case_files)} case file(s). Writing PDFs to: {output_dir}\n")

    ok = fail = 0
    for cf in case_files:
        with open(cf, "r", encoding="utf-8") as fh:
            case = json.load(fh)

        label    = case["meta"]["case_label"]
        out_path = output_dir / f"{label}.pdf"
        print(f"  {label} … ", end="", flush=True)
        try:
            build_pdf(case, out_path)
            print("✓")
            ok += 1
        except Exception as exc:
            print(f"✗  {exc}")
            fail += 1

    print(f"\n{'─'*50}")
    print(f"Generated: {ok}  |  Failed: {fail}")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
