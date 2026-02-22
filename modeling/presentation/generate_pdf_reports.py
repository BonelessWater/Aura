#!/usr/bin/env python3
"""
AuRA Clinical Report Generator
Generates one physician-facing PDF per demo case JSON file.

Usage:
    conda run -n aura python modeling/presentation/generate_pdf_reports.py
"""

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable
)

# ── Palette ───────────────────────────────────────────────────────────────────────
C_BLACK    = colors.black
C_WHITE    = colors.white
C_GRAY     = HexColor("#555555")
C_RULE     = HexColor("#999999")
C_TBL_RULE = HexColor("#AAAAAA")

CATEGORY_LABELS = {
    "healthy":          "Healthy / No Autoimmune Pattern",
    "systemic":         "Systemic Autoimmune",
    "endocrine":        "Endocrine Autoimmune",
    "gastrointestinal": "Gastrointestinal Autoimmune",
}

CBC_KEYS = ["wbc", "rbc", "hemoglobin", "hematocrit",
            "platelet_count", "mcv", "mch", "rdw"]
INFLAM_KEYS = ["esr", "crp"]

LAB_FULL = {
    "wbc":            "White Blood Cell Count (WBC)",
    "rbc":            "Red Blood Cell Count (RBC)",
    "hemoglobin":     "Hemoglobin",
    "hematocrit":     "Hematocrit",
    "platelet_count": "Platelet Count",
    "mcv":            "Mean Corpuscular Volume (MCV)",
    "mch":            "Mean Corpuscular Hemoglobin (MCH)",
    "rdw":            "Red Cell Distribution Width (RDW)",
    "esr":            "Erythrocyte Sedimentation Rate (ESR)",
    "crp":            "C-Reactive Protein (CRP)",
}

LAB_SHORT = {
    "wbc":            "WBC",
    "rbc":            "RBC",
    "hemoglobin":     "Hemoglobin",
    "hematocrit":     "Hematocrit",
    "platelet_count": "Platelet Count",
    "mcv":            "MCV",
    "mch":            "MCH",
    "rdw":            "RDW",
    "esr":            "ESR",
    "crp":            "CRP",
}

AUTOAB_MARKERS = [
    ("ana_status",  "ANA"),
    ("anti_dsdna",  "Anti-dsDNA"),
    ("hla_b27",     "HLA-B27"),
    ("anti_sm",     "Anti-Sm"),
    ("anti_ro",     "Anti-Ro/SSA"),
    ("anti_la",     "Anti-La/SSB"),
    ("rf_status",   "RF (Rheumatoid Factor)"),
    ("anti_ccp",    "Anti-CCP"),
    ("c3",          "Complement C3"),
    ("c4",          "Complement C4"),
]

AUTOAB_UNITS = {
    "rf_status":  " IU/mL",
    "c3":         " mg/dL",
    "c4":         " mg/dL",
    "anti_dsdna": " IU/mL",
    "anti_ccp":   " U/mL",
}


# ── Styles — Times New Roman, all left-aligned ───────────────────────────────────
def get_styles():
    s = {}

    s["notice_head"] = ParagraphStyle(
        "notice_head", fontName="Times-Bold", fontSize=9,
        textColor=C_BLACK, leading=13, alignment=TA_LEFT, spaceAfter=3,
    )
    s["notice_body"] = ParagraphStyle(
        "notice_body", fontName="Times-Italic", fontSize=8.5,
        textColor=C_BLACK, leading=13, alignment=TA_LEFT,
    )
    s["section"] = ParagraphStyle(
        "section", fontName="Times-Bold", fontSize=9,
        textColor=C_BLACK, leading=13, spaceBefore=10,
        spaceAfter=1, alignment=TA_LEFT,
    )
    s["body"] = ParagraphStyle(
        "body", fontName="Times-Roman", fontSize=9,
        textColor=C_BLACK, leading=13, spaceAfter=1, alignment=TA_LEFT,
    )
    s["body_bold"] = ParagraphStyle(
        "body_bold", fontName="Times-Bold", fontSize=9,
        textColor=C_BLACK, leading=13, spaceAfter=1, alignment=TA_LEFT,
    )
    s["kv_label"] = ParagraphStyle(
        "kv_label", fontName="Times-Bold", fontSize=9,
        textColor=C_BLACK, leading=13, alignment=TA_LEFT,
    )
    s["kv_value"] = ParagraphStyle(
        "kv_value", fontName="Times-Roman", fontSize=9,
        textColor=C_BLACK, leading=13, alignment=TA_LEFT,
    )
    s["sub_group"] = ParagraphStyle(
        "sub_group", fontName="Times-Bold", fontSize=9,
        textColor=C_BLACK, leading=13, alignment=TA_LEFT, spaceAfter=1,
    )
    s["marker"] = ParagraphStyle(
        "marker", fontName="Times-Roman", fontSize=9,
        textColor=C_BLACK, leading=13, alignment=TA_LEFT, leftIndent=16,
    )
    s["marker_muted"] = ParagraphStyle(
        "marker_muted", fontName="Times-Italic", fontSize=9,
        textColor=C_GRAY, leading=13, alignment=TA_LEFT, leftIndent=16,
    )
    s["ordered"] = ParagraphStyle(
        "ordered", fontName="Times-Roman", fontSize=9,
        textColor=C_BLACK, leading=13, alignment=TA_LEFT,
    )
    s["not_ordered"] = ParagraphStyle(
        "not_ordered", fontName="Times-Italic", fontSize=9,
        textColor=C_GRAY, leading=13, alignment=TA_LEFT,
    )
    s["th"] = ParagraphStyle(
        "th", fontName="Times-Bold", fontSize=8.5,
        textColor=C_BLACK, leading=11, alignment=TA_LEFT,
    )
    s["td"] = ParagraphStyle(
        "td", fontName="Times-Roman", fontSize=8.5,
        textColor=C_BLACK, leading=12, alignment=TA_LEFT,
    )
    s["td_bold"] = ParagraphStyle(
        "td_bold", fontName="Times-Bold", fontSize=8.5,
        textColor=C_BLACK, leading=12, alignment=TA_LEFT,
    )
    s["td_muted"] = ParagraphStyle(
        "td_muted", fontName="Times-Italic", fontSize=8.5,
        textColor=C_GRAY, leading=12, alignment=TA_LEFT,
    )
    return s


def _rule(W):
    return HRFlowable(width=W, thickness=0.5, color=C_RULE,
                      spaceBefore=2, spaceAfter=5)


def _kv_ts():
    return TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
    ])


def fmt_autoab(val, key):
    if val is None:
        return "Not tested"
    if val == 0.0:
        return "Negative"
    if val == 1.0:
        return "Positive"
    unit = AUTOAB_UNITS.get(key, "")
    return f"{val:.1f}{unit}"


# ── Section Builders ──────────────────────────────────────────────────────────────
def build_disclaimer(styles):
    return [
        Paragraph("NOTICE TO PHYSICIAN", styles["notice_head"]),
        Paragraph(
            "This report is produced by the AuRA statistical modeling platform and is intended "
            "solely as an informational reference for use by a licensed medical professional. "
            "It does not constitute a diagnosis, clinical opinion, or medical advice. All "
            "findings presented in this document must be independently reviewed and validated "
            "by a qualified physician before any clinical decision is made.",
            styles["notice_body"],
        ),
        Spacer(1, 6),
    ]


def build_patient_section(case, styles, W):
    p   = case["patient"]
    bmi = f"{p['bmi']:.1f}" if p.get("bmi") else "Not recorded"
    LW  = 1.8 * inch
    VW  = W - LW

    rows = [
        ("Patient ID",        p["patient_id"]),
        ("Age",               str(p.get("age", "—"))),
        ("Sex",               p.get("sex", "—")),
        ("BMI",               bmi),
        ("Source Dataset",    p.get("source_dataset", "—")),
        ("Diagnosis on File", f"{p.get('true_diagnosis_raw', '—')}  ({p.get('true_diagnosis_icd10', '—')})"),
    ]

    t = Table(
        [[Paragraph(lbl, styles["kv_label"]), Paragraph(val, styles["kv_value"])]
         for lbl, val in rows],
        colWidths=[LW, VW],
    )
    t.setStyle(_kv_ts())

    return [
        Paragraph("PATIENT INFORMATION", styles["section"]),
        _rule(W),
        t,
    ]


def build_tests_section(case, styles, W):
    lab   = case.get("lab_panel", {})
    panel = case.get("autoantibody_panel")
    LW    = W * 0.65
    RW    = W - LW

    out = [
        Paragraph("TESTS CONDUCTED", styles["section"]),
        _rule(W),
        Paragraph(
            "The following laboratory markers were included in this assessment. "
            "Markers listed as \"Not ordered\" were not available for this patient "
            "and were excluded from the statistical model input.",
            styles["body"],
        ),
        Spacer(1, 6),
    ]

    def marker_row(key):
        m       = lab.get(key, {})
        ordered = m.get("was_ordered", False)
        return [
            Paragraph(LAB_FULL[key], styles["marker"] if ordered else styles["marker_muted"]),
            Paragraph("Ordered" if ordered else "Not ordered",
                      styles["ordered"] if ordered else styles["not_ordered"]),
        ]

    def group_table(heading, keys):
        rows = [[Paragraph(heading, styles["sub_group"]), Paragraph("", styles["body"])]]
        rows += [marker_row(k) for k in keys]
        t = Table(rows, colWidths=[LW, RW])
        t.setStyle(_kv_ts())
        return t

    out.append(group_table("Complete Blood Count (CBC)", CBC_KEYS))
    out.append(Spacer(1, 4))
    out.append(group_table("Inflammatory Markers", INFLAM_KEYS))
    out.append(Spacer(1, 4))

    # Autoantibody availability note
    ab_note = ("An autoantibody panel was included. Results are in Section 5."
               if panel is not None
               else "No autoantibody data was available for this patient.")
    ab_style = styles["marker"] if panel is not None else styles["marker_muted"]
    ab_t = Table(
        [[Paragraph("Autoantibody Panel", styles["sub_group"]), Paragraph("", styles["body"])],
         [Paragraph(ab_note, ab_style),                         Paragraph("", styles["body"])]],
        colWidths=[LW, RW],
    )
    ab_t.setStyle(_kv_ts())
    out.append(ab_t)

    return out


def build_model_section(case, styles, W):
    pred  = case["prediction"]
    cat   = pred["predicted_category"]
    label = CATEGORY_LABELS.get(cat, cat.capitalize())
    conf  = f"{pred['category_confidence'] * 100:.1f}%"
    tier  = case["clinical_interpretation"].get("confidence_tier", "")
    probs = pred.get("category_probabilities", {})
    LW    = 1.8 * inch
    VW    = W - LW

    out = [
        Paragraph("STATISTICAL MODEL OUTPUT", styles["section"]),
        _rule(W),
    ]

    # Primary KV block
    kv_rows = [
        ("Model",             case["meta"].get("model", "AuRA Hierarchical Dual-Scorer v1.0")),
        ("Confidence Tier",   tier),
        ("",                  ""),
        ("Estimated Category",   label),
        ("Category Confidence",  conf),
    ]
    if pred.get("predicted_disease"):
        kv_rows += [
            ("", ""),
            ("Estimated Disease",         pred["predicted_disease"]),
            ("Disease Model Confidence",  f"{pred.get('disease_confidence', 0) * 100:.1f}%"),
        ]

    kv_data = []
    for lbl, val in kv_rows:
        if lbl == "":
            kv_data.append([Paragraph("", styles["kv_label"]),
                            Paragraph("", styles["kv_value"])])
        else:
            kv_data.append([Paragraph(lbl, styles["kv_label"]),
                            Paragraph(val, styles["kv_value"])])

    kv_t = Table(kv_data, colWidths=[LW, VW])
    kv_t.setStyle(_kv_ts())
    out.append(kv_t)
    out.append(Spacer(1, 6))

    # Probability distribution
    out.append(Paragraph("Category Probability Distribution:", styles["body_bold"]))
    out.append(Spacer(1, 2))

    prob_rows = []
    for cn, pv in sorted(probs.items(), key=lambda x: -x[1]):
        cn_label = CATEGORY_LABELS.get(cn, cn.capitalize())
        is_top   = cn == cat
        cell_s   = styles["kv_label"] if is_top else styles["kv_value"]
        prob_rows.append([Paragraph(cn_label,         cell_s),
                          Paragraph(f"{pv * 100:.1f}%", cell_s)])

    prob_ts = TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
    ])
    prob_t = Table(prob_rows, colWidths=[LW, VW])
    prob_t.setStyle(prob_ts)
    out.append(prob_t)

    return out


def build_lab_section(case, styles, W):
    lab = case.get("lab_panel", {})
    # Test 30% | Result 12% | Units 15% | Ref Range 23% | Flag 14%
    cws = [W * 0.30, W * 0.12, W * 0.15, W * 0.23, W * 0.14]

    data = [[
        Paragraph("Test",            styles["th"]),
        Paragraph("Result",          styles["th"]),
        Paragraph("Units",           styles["th"]),
        Paragraph("Reference Range", styles["th"]),
        Paragraph("Flag",            styles["th"]),
    ]]
    ts = [
        ("LINEBELOW",     (0, 0), (-1, 0),  0.5,  C_TBL_RULE),
        ("LINEBELOW",     (0, 1), (-1, -1), 0.25, C_TBL_RULE),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
    ]

    for key in CBC_KEYS + INFLAM_KEYS:
        m       = lab.get(key, {})
        flag    = m.get("flag", "MISSING")
        val     = m.get("value")
        ordered = m.get("was_ordered", False)
        short   = LAB_SHORT[key]

        if not ordered or flag == "MISSING":
            data.append([
                Paragraph(short,               styles["td_muted"]),
                Paragraph("—",                 styles["td_muted"]),
                Paragraph(m.get("unit", ""),   styles["td_muted"]),
                Paragraph("—",                 styles["td_muted"]),
                Paragraph("Not ordered",       styles["td_muted"]),
            ])
        else:
            abnormal = flag in ("H", "L")
            val_s    = (f"{val:.2f}".rstrip("0").rstrip(".")
                        if isinstance(val, float) else str(val or "—"))
            rl, rh   = m.get("reference_low"), m.get("reference_high")
            ref_s    = f"{rl} – {rh}" if rl is not None and rh is not None else "—"
            td_v     = styles["td_bold"] if abnormal else styles["td"]

            data.append([
                Paragraph(short,                        styles["td"]),
                Paragraph(val_s,                        td_v),
                Paragraph(m.get("unit", ""),            styles["td"]),
                Paragraph(ref_s,                        styles["td"]),
                Paragraph(flag if abnormal else "",     td_v),
            ])

    t = Table(data, colWidths=cws)
    t.setStyle(TableStyle(ts))
    return [
        Paragraph("LABORATORY RESULTS", styles["section"]),
        _rule(W),
        t,
    ]


def build_autoab_section(case, styles, W):
    panel = case.get("autoantibody_panel")
    if panel is None:
        return []

    cws  = [W * 0.50, W * 0.50]
    data = [[Paragraph("Test",   styles["th"]),
             Paragraph("Result", styles["th"])]]
    ts   = [
        ("LINEBELOW",     (0, 0), (-1, 0),  0.5,  C_TBL_RULE),
        ("LINEBELOW",     (0, 1), (-1, -1), 0.25, C_TBL_RULE),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
    ]

    for key, short in AUTOAB_MARKERS:
        val     = panel.get(key)
        val_str = fmt_autoab(val, key)
        data.append([
            Paragraph(short,   styles["td"]),
            Paragraph(val_str, styles["td_muted"] if val is None else styles["td"]),
        ])

    t = Table(data, colWidths=cws)
    t.setStyle(TableStyle(ts))
    return [
        Paragraph("AUTOANTIBODY PANEL", styles["section"]),
        _rule(W),
        t,
    ]


def build_notes_section(case, styles, W):
    interp  = case.get("clinical_interpretation", {})
    summary = interp.get("summary", "")
    rec     = interp.get("recommended_action", "")

    return [
        Paragraph("CLINICAL NOTES", styles["section"]),
        _rule(W),
        Paragraph("Summary", styles["body_bold"]),
        Spacer(1, 2),
        Paragraph(summary, styles["body"]),
        Spacer(1, 8),
        Paragraph("Recommended Action", styles["body_bold"]),
        Spacer(1, 2),
        Paragraph(rec, styles["body"]),
    ]


# ── PDF Assembly ──────────────────────────────────────────────────────────────────
def build_pdf(case, output_path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.80 * inch,
    )
    W          = letter[0] - 1.5 * inch
    styles     = get_styles()
    disclaimer = case["meta"].get("disclaimer", "")
    patient_id = case["patient"]["patient_id"]

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(C_RULE)
        canvas.setLineWidth(0.4)
        canvas.line(0.75 * inch, 0.64 * inch, letter[0] - 0.75 * inch, 0.64 * inch)
        canvas.setFont("Times-Italic", 7)
        canvas.setFillColor(C_GRAY)
        canvas.drawString(0.75 * inch, 0.48 * inch, disclaimer)
        canvas.setFont("Times-Roman", 7)
        canvas.setFillColor(C_BLACK)
        canvas.drawString(0.75 * inch, 0.33 * inch, f"Page {doc.page}")
        canvas.restoreState()

    def _page_header(canvas, doc):
        canvas.saveState()
        # "AuRA" — Times-Bold 11pt
        canvas.setFont("Times-Bold", 11)
        canvas.setFillColor(C_BLACK)
        canvas.drawString(0.75 * inch, letter[1] - 0.36 * inch, "AuRA")
        # Patient ID — same line, right-aligned
        canvas.setFont("Times-Roman", 8)
        canvas.drawRightString(letter[0] - 0.75 * inch, letter[1] - 0.36 * inch,
                               f"Patient: {patient_id}")
        # Subtitle — Times-Roman 8pt gray
        canvas.setFont("Times-Roman", 8)
        canvas.setFillColor(C_GRAY)
        canvas.drawString(0.75 * inch, letter[1] - 0.49 * inch,
                          "Autoimmune Risk Assessment Platform")
        # Rule
        canvas.setStrokeColor(C_RULE)
        canvas.setLineWidth(0.5)
        canvas.line(0.75 * inch, letter[1] - 0.56 * inch,
                    letter[0] - 0.75 * inch, letter[1] - 0.56 * inch)
        canvas.restoreState()
        _footer(canvas, doc)

    story = []

    # Disclaimer (first page only, before sections)
    story.extend(build_disclaimer(styles))
    story.append(_rule(W))

    # Section 1 — Patient Information
    story.extend(build_patient_section(case, styles, W))
    story.append(Spacer(1, 8))

    # Section 2 — Tests Conducted
    story.extend(build_tests_section(case, styles, W))
    story.append(Spacer(1, 8))

    # Section 3 — Statistical Model Output
    story.extend(build_model_section(case, styles, W))
    story.append(Spacer(1, 8))

    # Section 4 — Laboratory Results
    story.extend(build_lab_section(case, styles, W))
    story.append(Spacer(1, 8))

    # Section 5 — Autoantibody Panel (conditional)
    autoab = build_autoab_section(case, styles, W)
    if autoab:
        story.extend(autoab)
        story.append(Spacer(1, 8))

    # Section 6 — Clinical Notes
    story.extend(build_notes_section(case, styles, W))

    doc.build(story, onFirstPage=_page_header, onLaterPages=_page_header)


# ── Entry Point ───────────────────────────────────────────────────────────────────
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

    print(f"\n{'─' * 50}")
    print(f"Generated: {ok}  |  Failed: {fail}")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
