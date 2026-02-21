"""
Aura Data Wrangling Pipeline
Implements the Three-Tier Data Lake architecture from data_wrangling_plan.md.

Tier 1: Core Matrix (unified patient-level features)
Tier 2: Extension Tables (autoantibody panel, GI markers, longitudinal labs)
Tier 3: Reference Lookups (healthy baselines, ICD cluster map, drug risk index)

Outputs Parquet files for Databricks upload.
"""
import logging
import os
import sys

import numpy as np
import pandas as pd
from sklearn.impute import KNNImputer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
TIER1_DIR = os.path.join(BASE_DIR, "data", "processed", "tier1")
TIER2_DIR = os.path.join(BASE_DIR, "data", "processed", "tier2")
TIER3_DIR = os.path.join(BASE_DIR, "data", "processed", "tier3")

# ── ICD-10 Diagnosis Mapping ──────────────────────────────────────────────────
# Canonical mapping: keys are title-case disease names.
# map_diagnosis() normalises input before lookup so duplicates for case
# variants are not needed.
_DISEASE_TO_ICD10_CANONICAL = {
    # -- Rheumatic / Systemic connective-tissue ---
    "Rheumatoid Arthritis": "M06.9",
    "Ankylosing Spondylitis": "M45",
    "Sjogren Syndrome": "M35.0",
    "Sjögren Syndrome": "M35.0",
    "Sjögren's Syndrome": "M35.0",
    "Psoriatic Arthritis": "M07.3",
    "Systemic Lupus Erythematosus": "M32.9",
    "SLE": "M32.9",
    "Reactive Arthritis": "M02.9",
    "Vasculitis": "M31.9",
    "Dermatomyositis": "M33.9",
    "Polymyositis": "M33.2",
    "Scleroderma": "M34.9",
    "Scleroderma (Systemic Sclerosis)": "M34.9",
    "Mixed Connective Tissue Disease": "M35.1",
    "Undifferentiated Connective Tissue Disease (UCTD)": "M35.9",
    "Antiphospholipid Syndrome": "D68.61",
    "Behçet's Disease": "M35.2",
    "Sarcoidosis": "D86.9",
    "Morphea": "L94.0",
    "Discoid Lupus Erythematosus": "L93.0",
    "Lupus Nephritis": "M32.14",
    "Lupus Vasculitis": "M32.8",
    "Rheumatic Heart Disease": "I09.9",
    "Rheumatoid Lung Disease": "J99.0",
    "Rheumatoid Vasculitis": "M05.2",
    "Polymyalgia Rheumatica": "M35.3",
    "Myositis": "M60.9",
    "Inclusion Body Myositis": "G72.41",
    # -- Vasculitis subtypes ---
    "Giant Cell Arteritis": "M31.6",
    "Takayasu's Arteritis": "M31.4",
    "Polyarteritis Nodosa (PAN)": "M30.0",
    "Granulomatosis With Polyangiitis (GPA)": "M31.3",
    "Eosinophilic Granulomatosis With Polyangiitis (EGPA)": "M30.1",
    "Microscopic Polyangiitis (MPA)": "M31.7",
    "IgA Vasculitis (IgAV)": "D69.0",
    "Leukocytoclastic Vasculitis": "M31.0",
    "Urticarial Vasculitis": "L95.1",
    "Kawasaki Disease": "M30.3",
    "Cogan Syndrome": "H16.32",
    # -- GI ---
    "Crohn's Disease": "K50.9",
    "Crohn Disease": "K50.9",
    "Ulcerative Colitis": "K51.9",
    "Celiac Disease": "K90.0",
    "IBD": "K52.9",
    "Inflammatory Bowel Disease": "K52.9",
    "Autoimmune Hepatitis": "K75.4",
    "Autoimmune Pancreatitis": "K86.1",
    "Autoimmune Enteropathy": "K52.29",
    "Primary Sclerosing Cholangitis": "K83.0",
    "Pernicious Anemia": "D51.0",
    # -- Endocrine ---
    "Hashimoto's Thyroiditis": "E06.3",
    "Hashimoto's Encephalopathy": "E06.3",
    "Ord's Thyroiditis": "E06.3",
    "Graves' Disease": "E05.0",
    "Graves' Ophthalmopathy": "E05.0",
    "Type 1 Diabetes": "E10",
    "Diabetes Mellitus Type 1": "E10",
    "Addison's Disease": "E27.1",
    "Autoimmune Polyendocrine Syndrome Type 1 (APS1)": "E31.0",
    "Autoimmune Polyendocrine Syndrome Type 2 (APS2)": "E31.0",
    "Autoimmune Polyendocrine Syndrome Type 3 (APS3)": "E31.0",
    "Premature Ovarian Failure": "E28.31",
    "Autoimmune Oophoritis": "E28.39",
    "Autoimmune Orchitis": "N45.4",
    # -- Neurological ---
    "Multiple Sclerosis": "G35",
    "Myasthenia Gravis": "G70.0",
    "Guillain-Barré Syndrome": "G61.0",
    "Guillain-Barre Syndrome": "G61.0",
    "Neuromyelitis Optica": "G36.0",
    "Neuromyelitis Optica (Devic's Disease)/NMOSD": "G36.0",
    "Chronic Inflammatory Demyelinating Polyneuropathy": "G61.81",
    "Acute Disseminated Encephalomyelitis": "G04.0",
    "Transverse Myelitis": "G37.3",
    "Stiff-Person Syndrome": "G25.82",
    "Lambert-Eaton Myasthenic Syndrome": "G73.1",
    "Lambert–Eaton Myasthenic Syndrome": "G73.1",
    "Neuromyotonia": "G71.19",
    "Anti-NMDA Receptor Encephalitis": "G04.81",
    "Autoimmune Encephalitis": "G04.81",
    "Acute Motor Axonal Neuropathy": "G61.0",
    "Balo Concentric Sclerosis": "G37.5",
    "Bickerstaff's Encephalitis": "G04.81",
    "Idiopathic Inflammatory Demyelinating Diseases": "G37.9",
    "Optic Neuritis": "H46.9",
    "Opsoclonus Myoclonus Syndrome": "G25.3",
    "Paraneoplastic Cerebellar Degeneration": "G13.1",
    "Restless Legs Syndrome": "G25.81",
    "Susac's Syndrome": "I67.7",
    "Sydenham's Chorea": "I02.9",
    "Tolosa-Hunt Syndrome": "G44.89",
    "Tolosa–Hunt Syndrome": "G44.89",
    # -- Dermatological ---
    "Psoriasis": "L40.9",
    "Vitiligo": "L80",
    "Alopecia Areata": "L63.9",
    "Lichen Planus": "L43.9",
    "Lichen Sclerosus": "L90.0",
    "Pemphigus Vulgaris": "L10.0",
    "Bullous Pemphigoid": "L12.0",
    "Cicatricial Pemphigoid": "L12.1",
    "Gestational Pemphigoid": "O26.4",
    "Dermatitis Herpetiformis": "L13.0",
    "Epidermolysis Bullosa Acquisita": "L12.3",
    "Linear IgA Disease": "L13.8",
    "Erythema Nodosum": "L52",
    "Hidradenitis Suppurativa": "L73.2",
    "Autoimmune Progesterone Dermatitis": "L30.8",
    "Autoimmune Urticaria": "L50.1",
    "Autoimmune Angioedema": "D84.1",
    # -- Haematological ---
    "Autoimmune Hemolytic Anemia": "D59.1",
    "Immune Thrombocytopenia": "D69.3",
    "Thrombotic Thrombocytopenic Purpura": "M31.1",
    "Paroxysmal Nocturnal Hemoglobinuria": "D59.5",
    "Goodpasture Syndrome": "M31.0",
    # -- Renal ---
    "IgA Nephropathy": "N02.8",
    "Membranous Nephropathy": "N04.2",
    "Interstitial Nephritis": "N12",
    # -- Pulmonary ---
    "Idiopathic Pulmonary Fibrosis": "J84.112",
    "Interstitial Lung Disease": "J84.9",
    "Pulmonary Alveolar Proteinosis": "J84.01",
    # -- Ophthalmic ---
    "Autoimmune Uveitis": "H20.9",
    "Autoimmune Retinopathy": "H35.9",
    "Intermediate Uveitis": "H20.9",
    "Sympathetic Ophthalmia": "H44.1",
    "Scleritis": "H15.0",
    "Mooren's Ulcer": "H16.0",
    "Ligneous Conjunctivitis": "H10.51",
    # -- Other ---
    "Endometriosis": "N80.9",
    "Fibromyalgia": "M79.7",
    "Interstitial Cystitis": "N30.10",
    # -- Healthy ---
    "Normal": "Z00.0",
    "Healthy": "Z00.0",
    "Control": "Z00.0",
}

# Build a case-insensitive lookup from the canonical dictionary
DISEASE_TO_ICD10 = {}
for _key, _val in _DISEASE_TO_ICD10_CANONICAL.items():
    DISEASE_TO_ICD10[_key] = _val
    DISEASE_TO_ICD10[_key.lower()] = _val
    DISEASE_TO_ICD10[_key.title()] = _val

ICD10_TO_CLUSTER = {
    # -- Systemic / connective-tissue ---
    "M06.9": "systemic", "M45": "systemic", "M35.0": "systemic",
    "M07.3": "systemic", "M32.9": "systemic", "M02.9": "systemic",
    "M31.9": "systemic", "M33.9": "systemic", "M33.2": "systemic",
    "M34.9": "systemic", "M35.1": "systemic", "M35.9": "systemic",
    "D68.61": "systemic", "M35.2": "systemic", "D86.9": "systemic",
    "M35.3": "systemic", "M60.9": "systemic", "G72.41": "systemic",
    "M05.2": "systemic", "I09.9": "systemic", "J99.0": "systemic",
    "L94.0": "systemic", "L93.0": "systemic",
    "M32.14": "systemic", "M32.8": "systemic",
    # -- Vasculitis subtypes ---
    "M31.6": "systemic", "M31.4": "systemic", "M30.0": "systemic",
    "M31.3": "systemic", "M30.1": "systemic", "M31.7": "systemic",
    "D69.0": "systemic", "M31.0": "systemic", "L95.1": "systemic",
    "M30.3": "systemic", "H16.32": "systemic",
    # -- GI ---
    "K50.9": "gastrointestinal", "K51.9": "gastrointestinal",
    "K90.0": "gastrointestinal", "K52.9": "gastrointestinal",
    "K75.4": "gastrointestinal", "K86.1": "gastrointestinal",
    "K52.29": "gastrointestinal", "K83.0": "gastrointestinal",
    "D51.0": "gastrointestinal",
    # -- Endocrine ---
    "E06.3": "endocrine", "E05.0": "endocrine",
    "E10": "endocrine", "E27.1": "endocrine",
    "E31.0": "endocrine", "E28.31": "endocrine",
    "E28.39": "endocrine", "N45.4": "endocrine",
    # -- Neurological ---
    "G35": "neurological", "G70.0": "neurological", "G61.0": "neurological",
    "G36.0": "neurological", "G61.81": "neurological", "G04.0": "neurological",
    "G37.3": "neurological", "G25.82": "neurological", "G73.1": "neurological",
    "G71.19": "neurological", "G04.81": "neurological", "G37.5": "neurological",
    "G37.9": "neurological", "H46.9": "neurological", "G25.3": "neurological",
    "G13.1": "neurological", "G25.81": "neurological", "I67.7": "neurological",
    "I02.9": "neurological", "G44.89": "neurological",
    # -- Dermatological ---
    "L40.9": "dermatological", "L80": "dermatological", "L63.9": "dermatological",
    "L43.9": "dermatological", "L90.0": "dermatological", "L10.0": "dermatological",
    "L12.0": "dermatological", "L12.1": "dermatological", "O26.4": "dermatological",
    "L13.0": "dermatological", "L12.3": "dermatological", "L13.8": "dermatological",
    "L52": "dermatological", "L73.2": "dermatological", "L30.8": "dermatological",
    "L50.1": "dermatological", "D84.1": "dermatological",
    # -- Haematological ---
    "D59.1": "haematological", "D69.3": "haematological",
    "M31.1": "haematological", "D59.5": "haematological",
    # -- Renal ---
    "N02.8": "renal", "N04.2": "renal", "N12": "renal",
    # -- Pulmonary ---
    "J84.112": "pulmonary", "J84.9": "pulmonary", "J84.01": "pulmonary",
    # -- Ophthalmic ---
    "H20.9": "ophthalmic", "H35.9": "ophthalmic",
    "H44.1": "ophthalmic", "H15.0": "ophthalmic",
    "H16.0": "ophthalmic", "H10.51": "ophthalmic",
    # -- Other ---
    "N80.9": "other_autoimmune", "M79.7": "other_autoimmune",
    "N30.10": "other_autoimmune",
    # -- Healthy ---
    "Z00.0": "healthy",
}

# ── ICD-9 to ICD-10 crosswalk for common MIMIC codes ──────────────────────────
ICD9_TO_ICD10 = {
    "7140": "M06.9",   # RA
    "7100": "M32.9",   # SLE
    "7101": "M34.9",   # Scleroderma
    "7104": "M33.2",   # Polymyositis
    "7103": "M33.9",   # Dermatomyositis
    "7200": "M45",     # Ankylosing spondylitis
    "5550": "K50.9",   # Crohn's
    "5560": "K51.9",   # UC
    "5790": "K90.0",   # Celiac
    "2455": "E06.3",   # Hashimoto's
    "2420": "E05.0",   # Graves'
    "2500": "E10",     # Diabetes type 1 (unspecified in ICD-9)
    "25001": "E10",
    "3409": "G35",     # MS
    "3580": "G70.0",   # Myasthenia gravis
    "3570": "G61.0",   # Guillain-Barre
    "2554": "E27.1",   # Addison's
    "6960": "L40.9",   # Psoriasis
    "6960": "L40.9",
    "6961": "M07.3",   # Psoriatic arthropathy
    "4460": "M30.0",   # Polyarteritis nodosa
    "4464": "M30.3",   # Kawasaki
    # Common general ICD-9 codes for MIMIC context
    "41401": "I25.10",  # Coronary atherosclerosis
    "4280": "I50.9",    # CHF
    "25000": "E11.9",   # DM type 2
    "25002": "E11.65",  # DM type 2 with hyperglycemia
    "4019": "I10",      # Essential HTN
    "5849": "N17.9",    # Acute kidney failure
    "2724": "E78.5",    # Hyperlipidemia
    "2768": "E87.6",    # Hypokalemia
    "27800": "E66.9",   # Obesity
    "99592": "R65.20",  # Severe sepsis
    "0388": "A41.9",    # Septicemia
    "4829": "J18.9",    # Pneumonia
    "51881": "J96.0",   # Acute resp failure
}


def map_sex(val):
    """Normalize sex values to M/F."""
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip().lower()
    if val_str in ("male", "m", "1", "1.0"):
        return "M"
    if val_str in ("female", "f", "2", "2.0"):
        return "F"
    return np.nan


def map_diagnosis(val):
    """Map raw diagnosis string to ICD-10 (case-insensitive)."""
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip()
    # Try exact match first, then lowercase, then title-case
    result = DISEASE_TO_ICD10.get(val_str)
    if result is not None:
        return result
    result = DISEASE_TO_ICD10.get(val_str.lower())
    if result is not None:
        return result
    result = DISEASE_TO_ICD10.get(val_str.title())
    if result is not None:
        return result
    return np.nan


def map_categorical_to_binary(val):
    """Convert Positive/Negative string values to 1/0."""
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip().lower()
    if val_str in ("positive", "pos", "yes", "+", "1", "1.0"):
        return 1.0
    if val_str in ("negative", "neg", "no", "-", "0", "0.0"):
        return 0.0
    # If already numeric, return as-is
    try:
        return float(val)
    except (ValueError, TypeError):
        return np.nan


def detect_and_convert_units(series, marker, source_name):
    """
    Detect mismatched units and convert to canonical units.

    Canonical units:
        CRP: mg/L
        Hemoglobin: g/dL
        WBC: 10^3/uL
        Platelet: 10^3/uL
        Glucose: mg/dL
        BUN: mg/dL
    """
    vals = series.dropna()
    if len(vals) < 10:
        return series

    median_val = vals.median()

    if marker == "wbc":
        # Canonical: 10^3/uL (typical range 4-11).
        # If median > 500, likely in cells/uL (thousands), divide by 1000.
        if median_val > 500:
            logger.info("  [UNIT FIX] %s WBC median=%.0f, converting cells/uL -> 10^3/uL",
                        source_name, median_val)
            return series / 1000.0

    elif marker == "crp":
        # Canonical: mg/L (typical range 0.1-10 healthy, up to 200 acute).
        # If values are all < 3 and median < 1, might be mg/dL (divide by 10
        # is wrong direction). Harvard CRP range 0.1-30 is plausible mg/L.
        # Only flag if we see evidence of mg/dL (values ~100x too small).
        pass  # Harvard and others appear to be already in mg/L

    elif marker == "hemoglobin":
        # Canonical: g/dL (typical range 10-17).
        # If median > 100, likely g/L, divide by 10.
        if median_val > 50:
            logger.info("  [UNIT FIX] %s hemoglobin median=%.0f, converting g/L -> g/dL",
                        source_name, median_val)
            return series / 10.0

    elif marker == "platelet_count":
        # Canonical: 10^3/uL (typical 150-400).
        # If median > 50000, likely in cells/uL.
        if median_val > 50000:
            logger.info("  [UNIT FIX] %s platelet median=%.0f, converting cells/uL -> 10^3/uL",
                        source_name, median_val)
            return series / 1000.0

    return series


# ==============================================================================
# SOURCE WRANGLERS
# ==============================================================================

def wrangle_harvard():
    """
    Harvard Dataverse: Rheumatic and Autoimmune Disease Dataset
    Returns: (core_df, autoantibody_extension_df)
    """
    logger.info("Wrangling Harvard Dataverse...")
    filepath = os.path.join(RAW_DIR, "harvard", "Rheumatic and Autoimmune Disease Dataset.xlsx")
    if not os.path.exists(filepath):
        logger.warning("Harvard file not found at %s", filepath)
        return None, None

    df = pd.read_excel(filepath)
    logger.info("Harvard raw: %d rows x %d cols. Columns: %s", len(df), len(df.columns), list(df.columns))

    # Identify columns (they may vary; be flexible)
    col_map = {}
    for c in df.columns:
        cl = c.strip().lower()
        if cl == "age":
            col_map["age"] = c
        elif cl == "sex" or cl == "gender":
            col_map["sex"] = c
        elif cl == "esr":
            col_map["esr"] = c
        elif cl in ("crp", "c-reactive protein"):
            col_map["crp"] = c
        elif cl == "c3":
            col_map["c3"] = c
        elif cl == "c4":
            col_map["c4"] = c
        elif cl in ("rf", "rheumatoid factor"):
            col_map["rf_status"] = c
        elif cl in ("anti-ccp", "anti_ccp", "anticcp"):
            col_map["anti_ccp"] = c
        elif cl in ("ana", "antinuclear antibody"):
            col_map["ana_status"] = c
        elif cl in ("anti-dsdna", "anti_dsdna"):
            col_map["anti_dsdna"] = c
        elif cl in ("hla-b27", "hla_b27"):
            col_map["hla_b27"] = c
        elif cl in ("anti-sm", "anti_sm"):
            col_map["anti_sm"] = c
        elif cl in ("anti-ro", "anti_ro"):
            col_map["anti_ro"] = c
        elif cl in ("anti-la", "anti_la"):
            col_map["anti_la"] = c
        elif cl in ("diagnosis", "disease", "condition", "class", "target"):
            col_map["diagnosis"] = c

    logger.info("Harvard column mapping: %s", col_map)

    # Build core rows
    n = len(df)
    core = pd.DataFrame({
        "patient_id": [f"harvard_{i:05d}" for i in range(n)],
        "source": "harvard",
        "age": pd.to_numeric(df[col_map.get("age", "")], errors="coerce") if "age" in col_map else np.nan,
        "sex": df[col_map.get("sex", "")].apply(map_sex) if "sex" in col_map else np.nan,
        "esr": pd.to_numeric(df[col_map.get("esr", "")], errors="coerce") if "esr" in col_map else np.nan,
        "crp": pd.to_numeric(df[col_map.get("crp", "")], errors="coerce") if "crp" in col_map else np.nan,
    })

    # Map diagnosis
    if "diagnosis" in col_map:
        raw_diag = df[col_map["diagnosis"]]
        core["diagnosis_raw"] = raw_diag.astype(str)
        core["diagnosis_icd10"] = raw_diag.apply(map_diagnosis)
        core["diagnosis_cluster"] = core["diagnosis_icd10"].map(ICD10_TO_CLUSTER)
    else:
        core["diagnosis_raw"] = np.nan
        core["diagnosis_icd10"] = np.nan
        core["diagnosis_cluster"] = np.nan

    # Build autoantibody extension
    # Some columns are numeric (RF, Anti-CCP, C3, C4), others are
    # categorical Positive/Negative (ANA, Anti-dsDNA, HLA-B27, etc.)
    numeric_ab_cols = {"rf_status", "anti_ccp", "c3", "c4"}
    categorical_ab_cols = {"ana_status", "anti_dsdna", "hla_b27",
                           "anti_sm", "anti_ro", "anti_la"}
    all_ab_cols = ["rf_status", "anti_ccp", "ana_status", "anti_dsdna",
                   "hla_b27", "anti_sm", "anti_ro", "anti_la", "c3", "c4"]

    ab_data = {"patient_id": core["patient_id"]}
    for col in all_ab_cols:
        if col in col_map:
            if col in categorical_ab_cols:
                ab_data[col] = df[col_map[col]].apply(map_categorical_to_binary)
            else:
                ab_data[col] = pd.to_numeric(df[col_map[col]], errors="coerce")
        else:
            ab_data[col] = np.nan
    autoantibody_df = pd.DataFrame(ab_data)

    mapped_cols = [c for c in all_ab_cols if c in col_map]
    logger.info("Harvard core: %d rows, autoantibody ext: %d rows, mapped cols: %s",
                len(core), len(autoantibody_df), mapped_cols)
    return core, autoantibody_df


def wrangle_nhanes():
    """
    NHANES: National Health and Nutrition Examination Survey
    Merges CBC + CRP + Demographics + Medical Conditions (MCQ) across 4 cycles.

    MCQ fields used for autoimmune diagnosis labeling:
      MCQ160A = 1 -> Has arthritis
      MCQ195  = 2 -> Rheumatoid Arthritis, 3 -> Psoriatic Arthritis
      MCQ160N = 1 -> Lupus / SLE
      MCQ160M = 1 -> Thyroid problem (mapped to autoimmune thyroiditis)
      MCQ160K = 1 -> Celiac Disease

    Returns: core_df
    """
    logger.info("Wrangling NHANES...")
    nhanes_dir = os.path.join(RAW_DIR, "nhanes")
    cycles = {
        "2011-2012": ("CBC_G.XPT", "HSCRP_G.XPT", "DEMO_G.XPT", "MCQ_G.XPT"),
        "2013-2014": ("CBC_H.XPT", "HSCRP_H.XPT", "DEMO_H.XPT", "MCQ_H.XPT"),
        "2015-2016": ("CBC_I.XPT", "HSCRP_I.XPT", "DEMO_I.XPT", "MCQ_I.XPT"),
        "2017-2018": ("CBC_J.XPT", "HSCRP_J.XPT", "DEMO_J.XPT", "MCQ_J.XPT"),
    }

    # MCQ diagnosis mapping: (mcq_column, mcq_value, diagnosis_raw, icd10, cluster)
    # MCQ195 is only valid when MCQ160A == 1 (arthritis confirmed)
    MCQ_DIAGNOSIS_RULES = [
        # RA: MCQ195 == 2 (Rheumatoid Arthritis)
        ("MCQ195", 2.0, "rheumatoid_arthritis", "M06.9", "systemic"),
        # PsA: MCQ195 == 3 (Psoriatic Arthritis)
        ("MCQ195", 3.0, "psoriatic_arthritis", "M07.3", "systemic"),
        # Lupus: MCQ160N == 1
        ("MCQ160N", 1.0, "lupus", "M32.9", "systemic"),
        # Thyroid: MCQ160M == 1 (autoimmune thyroiditis)
        ("MCQ160M", 1.0, "autoimmune_thyroiditis", "E06.3", "endocrine"),
        # Celiac: MCQ160K == 1
        ("MCQ160K", 1.0, "celiac_disease", "K90.0", "gastrointestinal"),
    ]

    all_frames = []
    for cycle_name, (cbc_file, crp_file, demo_file, mcq_file) in cycles.items():
        logger.info("  Processing NHANES cycle %s...", cycle_name)
        cbc_path = os.path.join(nhanes_dir, cbc_file)
        crp_path = os.path.join(nhanes_dir, crp_file)
        demo_path = os.path.join(nhanes_dir, demo_file)
        mcq_path = os.path.join(nhanes_dir, mcq_file)

        try:
            cbc = pd.read_sas(cbc_path)
        except Exception as e:
            logger.warning("  Skipping CBC %s: %s", cbc_file, e)
            continue

        try:
            demo = pd.read_sas(demo_path)
        except Exception as e:
            logger.warning("  Skipping DEMO %s: %s", demo_file, e)
            continue

        # Merge on SEQN
        merged = cbc.merge(demo[["SEQN", "RIDAGEYR", "RIAGENDR"]], on="SEQN", how="left")

        # Try to add CRP
        try:
            crp = pd.read_sas(crp_path)
            merged = merged.merge(crp[["SEQN", "LBXHSCRP"]], on="SEQN", how="left")
        except Exception as e:
            logger.warning("  CRP file %s failed (%s), skipping CRP for this cycle.", crp_file, e)
            merged["LBXHSCRP"] = np.nan

        # Merge MCQ for autoimmune diagnosis labeling
        try:
            mcq = pd.read_sas(mcq_path)
            mcq_cols = ["SEQN"]
            for col in ["MCQ160A", "MCQ195", "MCQ160N", "MCQ160M", "MCQ160K"]:
                if col in mcq.columns:
                    mcq_cols.append(col)
            merged = merged.merge(mcq[mcq_cols], on="SEQN", how="left")
            logger.info("  Merged MCQ %s: %d rows with MCQ data", mcq_file, merged["MCQ160A"].notna().sum())
        except Exception as e:
            logger.warning("  MCQ file %s failed (%s), all patients labeled healthy.", mcq_file, e)

        merged["cycle"] = cycle_name
        all_frames.append(merged)

    if not all_frames:
        logger.warning("No NHANES data loaded.")
        return None

    nhanes = pd.concat(all_frames, ignore_index=True)
    n = len(nhanes)
    logger.info("NHANES merged: %d rows", n)

    # Assign diagnosis based on MCQ data (priority order: first match wins)
    diagnosis_raw = pd.Series(["population_survey"] * n)
    diagnosis_icd10 = pd.Series(["Z00.0"] * n)
    diagnosis_cluster = pd.Series(["healthy"] * n)

    for mcq_col, mcq_val, diag_raw, icd10, cluster in MCQ_DIAGNOSIS_RULES:
        if mcq_col not in nhanes.columns:
            continue
        mask = (nhanes[mcq_col] == mcq_val) & (diagnosis_raw == "population_survey")
        count = mask.sum()
        if count > 0:
            diagnosis_raw[mask] = diag_raw
            diagnosis_icd10[mask] = icd10
            diagnosis_cluster[mask] = cluster
            logger.info("  MCQ labeled %d patients as %s (%s)", count, diag_raw, icd10)

    # Map to unified schema
    core = pd.DataFrame({
        "patient_id": [f"nhanes_{int(seqn):05d}" for seqn in nhanes["SEQN"]],
        "source": "nhanes",
        "age": pd.to_numeric(nhanes.get("RIDAGEYR"), errors="coerce"),
        "sex": nhanes.get("RIAGENDR", pd.Series(dtype=float)).apply(map_sex),
        "crp": pd.to_numeric(nhanes.get("LBXHSCRP"), errors="coerce"),
        "wbc": pd.to_numeric(nhanes.get("LBXWBCSI"), errors="coerce"),
        "rbc": pd.to_numeric(nhanes.get("LBXRBCSI"), errors="coerce"),
        "hemoglobin": pd.to_numeric(nhanes.get("LBXHGB"), errors="coerce"),
        "hematocrit": pd.to_numeric(nhanes.get("LBXHCT"), errors="coerce"),
        "mcv": pd.to_numeric(nhanes.get("LBXMCVSI"), errors="coerce"),
        "mch": pd.to_numeric(nhanes.get("LBXMC"), errors="coerce"),
        "rdw": pd.to_numeric(nhanes.get("LBXRDW"), errors="coerce"),
        "platelet_count": pd.to_numeric(nhanes.get("LBXPLTSI"), errors="coerce"),
        "diagnosis_raw": diagnosis_raw.values,
        "diagnosis_icd10": diagnosis_icd10.values,
        "diagnosis_cluster": diagnosis_cluster.values,
    })

    # Derive lymphocyte and neutrophil percentages if available
    for pct_col, raw_col in [("lymphocyte_pct", "LBDLYMNO"), ("neutrophil_pct", "LBDNENO")]:
        if raw_col in nhanes.columns:
            wbc = pd.to_numeric(nhanes.get("LBXWBCSI"), errors="coerce")
            count = pd.to_numeric(nhanes.get(raw_col), errors="coerce")
            core[pct_col] = np.where(wbc > 0, (count / wbc) * 100, np.nan)
        else:
            core[pct_col] = np.nan

    autoimmune_count = (core["diagnosis_cluster"] != "healthy").sum()
    logger.info("NHANES core: %d rows (%d autoimmune, %d healthy)",
                len(core), autoimmune_count, len(core) - autoimmune_count)
    return core


def wrangle_mimic_demo():
    """
    MIMIC-IV Clinical Database Demo
    Returns: (core_df, longitudinal_lab_series_df)
    """
    logger.info("Wrangling MIMIC-IV Demo...")
    demo_dir = os.path.join(RAW_DIR, "mimic_demo", "mimic-iv-clinical-database-demo-2.2", "hosp")
    if not os.path.exists(demo_dir):
        logger.warning("MIMIC Demo directory not found at %s", demo_dir)
        return None, None

    try:
        # Note: In the demo, subject_id is the primary identifier
        patients = pd.read_csv(os.path.join(demo_dir, "patients.csv.gz"))
        labs = pd.read_csv(os.path.join(demo_dir, "labevents.csv.gz"))
        diagnoses = pd.read_csv(os.path.join(demo_dir, "diagnoses_icd.csv.gz"))
    except Exception as e:
        logger.error("Failed to read MIMIC files: %s", e)
        return None, None

    # Map lab items found in d_labitems earlier
    item_map = {
        50889: "crp",
        51288: "esr",
        51300: "wbc",
        51279: "rbc",
        51222: "hemoglobin",
        51221: "hematocrit",
        51250: "mcv",
        51248: "mch",
        51277: "rdw",
        51265: "platelet_count"
    }

    # Filter labs to items of interest
    target_labs = labs[labs["itemid"].isin(item_map.keys())].copy()
    target_labs["column_name"] = target_labs["itemid"].map(item_map)

    # Tier 2: Longitudinal Lab Series
    longitudinal = target_labs[["subject_id", "charttime", "column_name", "valuenum", "valueuom"]].copy()
    longitudinal.rename(columns={
        "subject_id": "patient_id",
        "charttime": "event_timestamp",
        "valuenum": "lab_value",
        "valueuom": "lab_unit",
        "column_name": "lab_item"
    }, inplace=True)
    longitudinal["patient_id"] = "mimic_" + longitudinal["patient_id"].astype(str)
    longitudinal["source"] = "mimic_demo"

    # Tier 1: Core Matrix (patient snapshots - using Median value of all labs per patient)
    p_labs = target_labs.groupby(["subject_id", "column_name"])["valuenum"].median().unstack().reset_index()

    # Merge with patients for age/sex
    core = p_labs.merge(patients[["subject_id", "gender", "anchor_age"]], on="subject_id", how="left")
    core.rename(columns={"gender": "sex", "anchor_age": "age"}, inplace=True)
    core["patient_id"] = "mimic_" + core["subject_id"].astype(str)
    core["source"] = "mimic_demo"
    core["sex"] = core["sex"].apply(map_sex)

    # Add primary diagnosis from diagnoses_icd
    p_diag = diagnoses.sort_values(["subject_id", "seq_num"]).groupby("subject_id").first().reset_index()
    core = core.merge(p_diag[["subject_id", "icd_code", "icd_version"]], on="subject_id", how="left")
    core.rename(columns={"icd_code": "diagnosis_raw"}, inplace=True)

    # Map ICD-9 codes to ICD-10 using crosswalk, keep ICD-10 codes as-is
    def _mimic_to_icd10(row):
        raw = row.get("diagnosis_raw")
        version = row.get("icd_version")
        if pd.isna(raw):
            return np.nan
        raw = str(raw).strip()
        if version == 9 or (isinstance(version, float) and version == 9.0):
            return ICD9_TO_ICD10.get(raw, np.nan)
        # ICD-10: try direct lookup in cluster map
        return raw if raw in ICD10_TO_CLUSTER else np.nan

    core["diagnosis_icd10"] = core.apply(_mimic_to_icd10, axis=1)
    core["diagnosis_cluster"] = core["diagnosis_icd10"].map(ICD10_TO_CLUSTER)
    core.drop(columns=["subject_id", "icd_version"], inplace=True)

    mapped_count = core["diagnosis_icd10"].notna().sum()
    logger.info("MIMIC diagnosis mapped: %d/%d", mapped_count, len(core))

    logger.info("MIMIC core: %d rows, longitudinal events: %d", len(core), len(longitudinal))
    return core, longitudinal


def wrangle_uci_drug():
    """
    UCI Drug-Induced Autoimmunity Prediction.
    The Label column indicates whether a compound is associated with
    drug-induced autoimmunity (1) or not (0).
    We rename it to autoimmunity_risk_score and keep SMILES as drug_name.
    Returns: drug_risk_df (Tier 3 reference)
    """
    logger.info("Wrangling UCI Drug-Induced Autoimmunity...")
    uci_dir = os.path.join(RAW_DIR, "uci_drug")

    train_path = os.path.join(uci_dir, "DIA_trainingset_RDKit_descriptors.csv")
    test_path = os.path.join(uci_dir, "DIA_testset_RDKit_descriptors.csv")

    frames = []
    for path, split in [(train_path, "train"), (test_path, "test")]:
        if os.path.exists(path):
            df = pd.read_csv(path)
            df["split"] = split
            frames.append(df)
            logger.info("  UCI %s: %d rows x %d cols", split, len(df), len(df.columns))

    if not frames:
        logger.warning("No UCI drug files found.")
        return None

    drug_df = pd.concat(frames, ignore_index=True)

    # Rename for clarity: Label -> autoimmunity_risk_score, SMILES -> drug_name
    if "Label" in drug_df.columns:
        drug_df.rename(columns={"Label": "autoimmunity_risk_score"}, inplace=True)
    if "SMILES" in drug_df.columns:
        drug_df.rename(columns={"SMILES": "drug_name"}, inplace=True)

    logger.info("UCI Drug total: %d rows, risk-positive: %d",
                len(drug_df),
                (drug_df.get("autoimmunity_risk_score", pd.Series()) == 1).sum())
    return drug_df


# ── ImmPort Study Configuration ──────────────────────────────────────────────
# Each study needs: diagnosis_raw, diagnosis_icd10 so we can label patients.
# Lab name mapping is standardised across ImmPort; study-specific overrides
# are merged into the global map below.

IMMPORT_STUDIES = {
    "SDY824": {
        "diagnosis_raw": "Rheumatoid Arthritis",
        "diagnosis_icd10": "M06.9",
    },
    "SDY91": {
        "diagnosis_raw": "Granulomatosis With Polyangiitis (GPA)",
        "diagnosis_icd10": "M31.3",
    },
    "SDY471": {
        "diagnosis_raw": "Multiple Sclerosis",
        "diagnosis_icd10": "G35",
    },
    "SDY473": {
        "diagnosis_raw": "Rheumatoid Arthritis",
        "diagnosis_icd10": "M06.9",
    },
    "SDY474": {
        "diagnosis_raw": "Systemic Lupus Erythematosus",
        "diagnosis_icd10": "M32.9",
    },
    "SDY547": {
        "diagnosis_raw": "Multiple Sclerosis",
        "diagnosis_icd10": "G35",
    },
    "SDY568": {
        "diagnosis_raw": "Type 1 Diabetes",
        "diagnosis_icd10": "E10",
    },
    "SDY569": {
        "diagnosis_raw": "Type 1 Diabetes",
        "diagnosis_icd10": "E10",
    },
    "SDY655": {
        "diagnosis_raw": "Pemphigus Vulgaris",
        "diagnosis_icd10": "L10.0",
    },
    "SDY661": {
        "diagnosis_raw": "Multiple Sclerosis",
        "diagnosis_icd10": "G35",
    },
    "SDY823": {
        "diagnosis_raw": "Sjogren Syndrome",
        "diagnosis_icd10": "M35.0",
    },
    "SDY961": {
        "diagnosis_raw": "Sjogren Syndrome",
        "diagnosis_icd10": "M35.0",
    },
    "SDY3216": {
        "diagnosis_raw": "Scleroderma (Systemic Sclerosis)",
        "diagnosis_icd10": "M34.9",
    },
    "SDY625": {
        "diagnosis_raw": "Systemic Lupus Erythematosus",
        "diagnosis_icd10": "M32.9",
    },
}

# Global lab name -> core_matrix column mapping.
# ImmPort studies use inconsistent names; this covers all variants found.
IMMPORT_LAB_NAME_MAP = {
    # WBC
    "WBC": "wbc",
    "White Blood Cells": "wbc",
    "Leukocytes": "wbc",
    # RBC
    "RBC": "rbc",
    "Erythrocytes": "rbc",
    # Hemoglobin
    "Hemoglobin": "hemoglobin",
    "HGB": "hemoglobin",
    # Hematocrit
    "Hematocrit": "hematocrit",
    # Platelets
    "Platelet Count": "platelet_count",
    "PLATELET COUNT": "platelet_count",
    "Platelets": "platelet_count",
    "PLATELET": "platelet_count",
    "Platelet": "platelet_count",
    # MCV
    "MCV": "mcv",
    "Ery. Mean Corpuscular Volume": "mcv",
    "Mean corpuscular volume": "mcv",
    # MCH
    "MCH": "mch",
    "Ery. Mean Corpuscular Hemoglobin": "mch",
    # RDW
    "RDW": "rdw",
    "Erythrocytes Distribution Width": "rdw",
    # CRP
    "C-Reactive Protein": "crp",
    "CRP": "crp",
    "C Reactive Protein": "crp",
    # ESR
    "Erythrocyte Sedimentation Rate": "esr",
    "WESR": "esr",
    "Sedimentation Rate": "esr",
    # Neutrophils
    "Neutrophils": "neutrophil_pct",
    "SEGMENTED NEUTROPHILS": "neutrophil_pct",
    "Neutrophils/Leukocytes": "neutrophil_pct",
    # Lymphocytes
    "Lymphocytes": "lymphocyte_pct",
    "Lymphs": "lymphocyte_pct",
    "Lymphocytes/Leukocytes": "lymphocyte_pct",
}

# Autoantibody lab names -> tier 2 column mapping
IMMPORT_AB_NAME_MAP = {
    "Antinuclear Antibodies": "ana_status",
    "Anti-Double Stranded DNA": "anti_dsdna",
    "Rheumatoid Factor": "rf_status",
    "RF": "rf_status",
    "Cyclic Citrullinated Peptide Antibody": "anti_ccp",
    "Complement C3": "c3",
    "Complement C4": "c4",
    "SS-A Antibody": "anti_ro",
    "SSA": "anti_ro",
    "SS-B Antibody": "anti_la",
    "SSB": "anti_la",
    "Anti-SS-A": "anti_ro",
    "Anti-SS-B": "anti_la",
    "Anti-Smith": "anti_sm",
    "Anti-RNP": "anti_rnp",
}


def _find_immport_tab_dir(study_id):
    """Locate the Tab/ directory for an ImmPort study under data/raw/immport/."""
    import glob as globmod
    base = os.path.join(RAW_DIR, "immport")
    patterns = [
        os.path.join(base, f"{study_id}_Tab", f"{study_id}-DR*_Tab", "Tab"),
        os.path.join(base, f"{study_id}-DR*_Tab", f"{study_id}-DR*_Tab", "Tab"),
        os.path.join(base, f"{study_id}-DR*_Tab", "Tab"),
    ]
    for pat in patterns:
        matches = globmod.glob(pat)
        if matches:
            return matches[0]
    return None


def wrangle_immport_study(study_id, config):
    """
    Generic ImmPort study wrangler.

    Reads the ImmPort Tab export for a single study and produces:
      - core_df: patient-level baseline snapshot for core_matrix
      - autoantibody_df: autoantibody extension rows (may be None)
      - longitudinal_df: all-timepoint lab records (Tier 2)

    Uses the earliest available visit (screening or day-0) as baseline.
    """
    logger.info("Wrangling ImmPort %s...", study_id)
    sdy_dir = _find_immport_tab_dir(study_id)
    if sdy_dir is None:
        logger.warning("  %s: Tab directory not found, skipping", study_id)
        return None, None, None

    # -- Load tables --
    try:
        subjects = pd.read_csv(os.path.join(sdy_dir, "subject.txt"), sep="\t")
        lab_tests = pd.read_csv(os.path.join(sdy_dir, "lab_test.txt"), sep="\t")
        biosamples = pd.read_csv(os.path.join(sdy_dir, "biosample.txt"), sep="\t")
        arm_subj = pd.read_csv(os.path.join(sdy_dir, "arm_2_subject.txt"), sep="\t")
    except Exception as e:
        logger.error("  %s: Failed to read tables: %s", study_id, e)
        return None, None, None

    # Assessments are optional (some studies lack them)
    assess_path = os.path.join(sdy_dir, "assessment_component.txt")
    if os.path.exists(assess_path):
        try:
            assessments = pd.read_csv(assess_path, sep="\t")
        except Exception as e:
            logger.warning("  %s: Failed to read assessments: %s", study_id, e)
            assessments = pd.DataFrame()
    else:
        assessments = pd.DataFrame()

    logger.info("  %s loaded: %d subjects, %d lab_tests, %d biosamples",
                study_id, len(subjects), len(lab_tests), len(biosamples))

    source_key = f"immport_{study_id.lower()}"

    # -- Subject demographics --
    subj_age = arm_subj.groupby("SUBJECT_ACCESSION")["MIN_SUBJECT_AGE_IN_YEARS"].first()

    # Fallback age from assessments
    if not assessments.empty and "AGE_AT_ONSET_REPORTED" in assessments.columns:
        assess_age = assessments.groupby("SUBJECT_ACCESSION")["AGE_AT_ONSET_REPORTED"].first()
        assess_age = pd.to_numeric(assess_age, errors="coerce")
    else:
        assess_age = pd.Series(dtype=float)

    subj_demo = subjects[["SUBJECT_ACCESSION", "GENDER"]].copy()
    subj_demo["age"] = subj_demo["SUBJECT_ACCESSION"].map(subj_age)
    missing_age = subj_demo["age"].isna()
    if missing_age.any() and not assess_age.empty:
        subj_demo.loc[missing_age, "age"] = (
            subj_demo.loc[missing_age, "SUBJECT_ACCESSION"].map(assess_age)
        )
    subj_demo["sex"] = subj_demo["GENDER"].apply(map_sex)
    logger.info("  %s demographics: %d subjects, %d with age, %d with sex",
                study_id, len(subj_demo),
                subj_demo["age"].notna().sum(), subj_demo["sex"].notna().sum())

    # -- Link lab_tests -> biosample -> subject --
    bs_cols = ["BIOSAMPLE_ACCESSION", "SUBJECT_ACCESSION",
               "PLANNED_VISIT_ACCESSION", "STUDY_TIME_COLLECTED"]
    bs_lookup = biosamples[[c for c in bs_cols if c in biosamples.columns]].copy()
    labs = lab_tests.merge(bs_lookup, on="BIOSAMPLE_ACCESSION", how="left")

    # -- Select baseline visit (earliest timepoint) --
    if "STUDY_TIME_COLLECTED" in labs.columns:
        labs["STUDY_TIME_COLLECTED"] = pd.to_numeric(
            labs["STUDY_TIME_COLLECTED"], errors="coerce"
        )
        # Find the earliest visit per subject (screening/baseline)
        subj_min_time = labs.groupby("SUBJECT_ACCESSION")["STUDY_TIME_COLLECTED"].min()
        labs["_is_baseline"] = labs.apply(
            lambda r: r["STUDY_TIME_COLLECTED"] == subj_min_time.get(r["SUBJECT_ACCESSION"]),
            axis=1,
        )
        baseline_labs = labs[labs["_is_baseline"]].copy()
    else:
        baseline_labs = labs.copy()

    # Deduplicate: keep first occurrence per subject+test
    baseline_labs = baseline_labs.drop_duplicates(
        subset=["SUBJECT_ACCESSION", "NAME_REPORTED"], keep="first"
    )
    logger.info("  %s baseline labs: %d records", study_id, len(baseline_labs))

    # -- Pivot core lab tests to wide format --
    core_lab_rows = baseline_labs[
        baseline_labs["NAME_REPORTED"].isin(IMMPORT_LAB_NAME_MAP)
    ].copy()
    core_lab_rows["column"] = core_lab_rows["NAME_REPORTED"].map(IMMPORT_LAB_NAME_MAP)
    core_lab_rows["value"] = pd.to_numeric(
        core_lab_rows["RESULT_VALUE_PREFERRED"], errors="coerce"
    )
    # If multiple lab names map to the same column, keep first
    core_lab_rows = core_lab_rows.drop_duplicates(
        subset=["SUBJECT_ACCESSION", "column"], keep="first"
    )

    if core_lab_rows.empty:
        logger.warning("  %s: no matching core labs, skipping", study_id)
        return None, None, None

    core_wide = core_lab_rows.pivot_table(
        index="SUBJECT_ACCESSION", columns="column",
        values="value", aggfunc="first",
    ).reset_index()

    # -- Pivot autoantibody tests --
    ab_rows = baseline_labs[
        baseline_labs["NAME_REPORTED"].isin(IMMPORT_AB_NAME_MAP)
    ].copy()
    autoantibody_df = None
    if not ab_rows.empty:
        ab_rows["column"] = ab_rows["NAME_REPORTED"].map(IMMPORT_AB_NAME_MAP)
        # Numeric columns (c3, c4) stay numeric; binary columns get converted
        binary_ab = {"ana_status", "anti_dsdna", "rf_status", "anti_ccp",
                     "anti_ro", "anti_la", "hla_b27", "anti_sm"}
        ab_rows["value"] = ab_rows.apply(
            lambda r: (map_categorical_to_binary(r["RESULT_VALUE_PREFERRED"])
                       if r["column"] in binary_ab
                       else pd.to_numeric(r["RESULT_VALUE_PREFERRED"], errors="coerce")),
            axis=1,
        )
        ab_rows = ab_rows.drop_duplicates(
            subset=["SUBJECT_ACCESSION", "column"], keep="first"
        )
        ab_wide = ab_rows.pivot_table(
            index="SUBJECT_ACCESSION", columns="column",
            values="value", aggfunc="first",
        ).reset_index()

        ab_ext = subj_demo[["SUBJECT_ACCESSION"]].merge(
            ab_wide, on="SUBJECT_ACCESSION", how="inner"
        )
        ab_ext["patient_id"] = (
            source_key + "_" + ab_ext["SUBJECT_ACCESSION"].str.replace("SUB", "")
        )
        ab_ext.drop(columns=["SUBJECT_ACCESSION"], inplace=True)
        if len(ab_ext) > 0:
            autoantibody_df = ab_ext
            logger.info("  %s autoantibody extension: %d rows", study_id, len(ab_ext))

    # -- Build core_matrix rows --
    core = subj_demo[["SUBJECT_ACCESSION", "age", "sex"]].merge(
        core_wide, on="SUBJECT_ACCESSION", how="left"
    )
    core["patient_id"] = source_key + "_" + core["SUBJECT_ACCESSION"].str.replace("SUB", "")
    core["source"] = source_key
    core["diagnosis_raw"] = config["diagnosis_raw"]
    core["diagnosis_icd10"] = config["diagnosis_icd10"]
    core["diagnosis_cluster"] = ICD10_TO_CLUSTER.get(config["diagnosis_icd10"], "other_autoimmune")
    core.drop(columns=["SUBJECT_ACCESSION"], inplace=True)

    # Unit detection/conversion (source-level median-based)
    for marker in ["wbc", "hemoglobin", "platelet_count"]:
        if marker in core.columns:
            core[marker] = detect_and_convert_units(core[marker], marker, source_key)

    # Per-value unit correction for individual outliers that slip past
    # median-based detection (e.g. mixed-unit studies where most values
    # are correct but a few are in different units)
    if "wbc" in core.columns:
        mask = core["wbc"] > 100
        if mask.any():
            logger.info("  %s: fixing %d WBC values > 100 (cells/uL -> 10^3/uL)",
                        source_key, mask.sum())
            core.loc[mask, "wbc"] = core.loc[mask, "wbc"] / 1000.0
    if "hemoglobin" in core.columns:
        mask = core["hemoglobin"] > 30
        if mask.any():
            logger.info("  %s: fixing %d hemoglobin values > 30 (g/L -> g/dL)",
                        source_key, mask.sum())
            core.loc[mask, "hemoglobin"] = core.loc[mask, "hemoglobin"] / 10.0
    if "platelet_count" in core.columns:
        mask = core["platelet_count"] > 5000
        if mask.any():
            logger.info("  %s: fixing %d platelet values > 5000 (cells/uL -> 10^3/uL)",
                        source_key, mask.sum())
            core.loc[mask, "platelet_count"] = core.loc[mask, "platelet_count"] / 1000.0

    logger.info("  %s core: %d rows", study_id, len(core))
    for col in ["wbc", "rbc", "hemoglobin", "hematocrit", "platelet_count",
                "mcv", "mch", "rdw", "crp", "esr", "neutrophil_pct", "lymphocyte_pct"]:
        if col in core.columns:
            n_valid = core[col].notna().sum()
            logger.info("    %s: %d/%d non-null", col, n_valid, len(core))

    # -- Build Tier 2 longitudinal labs (all timepoints) --
    all_core_labs = labs[labs["NAME_REPORTED"].isin(IMMPORT_LAB_NAME_MAP)].copy()
    all_core_labs["lab_item"] = all_core_labs["NAME_REPORTED"].map(IMMPORT_LAB_NAME_MAP)
    all_core_labs["lab_value"] = pd.to_numeric(
        all_core_labs["RESULT_VALUE_PREFERRED"], errors="coerce"
    )
    long_cols = {
        "SUBJECT_ACCESSION": "SUBJECT_ACCESSION",
        "lab_item": "lab_item",
        "lab_value": "lab_value",
    }
    longitudinal = all_core_labs[list(long_cols.keys())].copy()
    if "STUDY_TIME_COLLECTED" in all_core_labs.columns:
        longitudinal["study_day"] = all_core_labs["STUDY_TIME_COLLECTED"]
    if "RESULT_UNIT_PREFERRED" in all_core_labs.columns:
        longitudinal["lab_unit"] = all_core_labs["RESULT_UNIT_PREFERRED"]
    longitudinal["patient_id"] = (
        source_key + "_" + longitudinal["SUBJECT_ACCESSION"].str.replace("SUB", "")
    )
    longitudinal["source"] = source_key
    longitudinal.drop(columns=["SUBJECT_ACCESSION"], inplace=True)

    logger.info("  %s longitudinal: %d records", study_id, len(longitudinal))
    return core, autoantibody_df, longitudinal


def wrangle_all_immport():
    """
    Wrangle all configured ImmPort studies.
    Returns: (combined_core, combined_autoantibody, combined_longitudinal)
    """
    core_frames = []
    ab_frames = []
    long_frames = []

    for study_id, config in IMMPORT_STUDIES.items():
        core, ab, longitudinal = wrangle_immport_study(study_id, config)
        if core is not None:
            core_frames.append(core)
        if ab is not None:
            ab_frames.append(ab)
        if longitudinal is not None:
            long_frames.append(longitudinal)

    combined_core = None
    if core_frames:
        combined_core = pd.concat(core_frames, ignore_index=True)
        logger.info("ImmPort total core rows: %d from %d studies",
                    len(combined_core), len(core_frames))

    combined_ab = None
    if ab_frames:
        combined_ab = pd.concat(ab_frames, ignore_index=True)
        logger.info("ImmPort total autoantibody rows: %d", len(combined_ab))

    combined_long = None
    if long_frames:
        combined_long = pd.concat(long_frames, ignore_index=True)
        logger.info("ImmPort total longitudinal rows: %d", len(combined_long))

    return combined_core, combined_ab, combined_long


def build_healthy_baselines(core_matrix):
    """
    Build Tier 3 healthy baseline reference ranges from NHANES data.
    Computes percentile distributions stratified by age bucket and sex.
    Filters out likely sick individuals using CRP > 10 mg/L as a proxy
    for acute inflammation (no chronic-condition questionnaire available).
    """
    logger.info("Building healthy baseline reference ranges...")

    # Filter to NHANES rows (population survey, no specific autoimmune diagnosis)
    baseline = core_matrix[core_matrix["source"] == "nhanes"].copy()
    if baseline.empty:
        logger.warning("No NHANES data for baselines.")
        return None

    # Exclude participants with CRP > 10 mg/L (likely acute inflammation)
    pre_filter = len(baseline)
    if "crp" in baseline.columns:
        baseline = baseline[(baseline["crp"].isna()) | (baseline["crp"] <= 10.0)]
    logger.info("Healthy baseline filter: %d -> %d rows (excluded CRP > 10 mg/L)",
                pre_filter, len(baseline))

    # Create age buckets
    bins = [0, 18, 30, 45, 60, 120]
    labels = ["0-17", "18-30", "31-45", "46-60", "61+"]
    baseline["age_bucket"] = pd.cut(baseline["age"], bins=bins, labels=labels, right=True)

    lab_markers = ["crp", "wbc", "rbc", "hemoglobin", "hematocrit", "mcv", "mch",
                   "rdw", "platelet_count", "lymphocyte_pct", "neutrophil_pct"]

    rows = []
    for marker in lab_markers:
        if marker not in baseline.columns:
            continue
        for age_bucket in labels:
            for sex in ["M", "F"]:
                subset = baseline[(baseline["age_bucket"] == age_bucket) & (baseline["sex"] == sex)]
                vals = subset[marker].dropna()
                if len(vals) < 10:
                    continue
                rows.append({
                    "marker": marker,
                    "age_bucket": age_bucket,
                    "sex": sex,
                    "count": len(vals),
                    "p5": vals.quantile(0.05),
                    "p25": vals.quantile(0.25),
                    "p50": vals.quantile(0.50),
                    "p75": vals.quantile(0.75),
                    "p95": vals.quantile(0.95),
                })

    ref_df = pd.DataFrame(rows)
    logger.info("Healthy baselines: %d reference rows across %d markers", len(ref_df), len(lab_markers))
    return ref_df


def build_icd_cluster_map():
    """Build Tier 3 ICD-10 to Aura Cluster mapping table."""
    rows = []
    seen = set()
    for icd_code, cluster in ICD10_TO_CLUSTER.items():
        if icd_code in seen:
            continue
        seen.add(icd_code)
        # Reverse lookup for description (use canonical dict to avoid dupes)
        desc = [k for k, v in _DISEASE_TO_ICD10_CANONICAL.items() if v == icd_code]
        desc_str = desc[0] if desc else icd_code
        rows.append({
            "icd10_code": icd_code,
            "icd10_description": desc_str,
            "aura_cluster": cluster,
        })
    return pd.DataFrame(rows)


def compute_zscores(core_matrix, baselines):
    """
    Add Z-score columns for each lab marker, normalized against
    age/sex-stratified healthy baselines.
    """
    if baselines is None or baselines.empty:
        logger.warning("No baselines available, skipping Z-score computation.")
        return core_matrix

    logger.info("Computing Z-scores against healthy baselines...")
    bins = [0, 18, 30, 45, 60, 120]
    labels = ["0-17", "18-30", "31-45", "46-60", "61+"]
    core_matrix["age_bucket"] = pd.cut(core_matrix["age"], bins=bins, labels=labels, right=True)

    lab_markers = ["crp", "wbc", "rbc", "hemoglobin", "hematocrit", "mcv", "mch",
                   "rdw", "platelet_count"]

    for marker in lab_markers:
        if marker not in core_matrix.columns:
            continue
        zscore_col = f"{marker}_zscore"
        core_matrix[zscore_col] = np.nan

        for _, ref_row in baselines[baselines["marker"] == marker].iterrows():
            mask = (
                (core_matrix["age_bucket"] == ref_row["age_bucket"])
                & (core_matrix["sex"] == ref_row["sex"])
            )
            iqr = ref_row["p75"] - ref_row["p25"]
            if iqr > 0:
                core_matrix.loc[mask, zscore_col] = (
                    (core_matrix.loc[mask, marker] - ref_row["p50"]) / iqr
                )

    core_matrix.drop(columns=["age_bucket"], inplace=True, errors="ignore")
    logger.info("Z-scores computed for %d markers.", len(lab_markers))
    return core_matrix


def impute_core_matrix(core_matrix):
    """
    Impute missing values in Tier 1 lab columns per the data wrangling plan:
      - <15% missing within source: median imputation
      - 15-40% missing within source: KNN imputation (k=5, by age/sex/source)
      - >40% missing: leave as NaN (use only in sub-models)

    Adds binary {col}_missing flags BEFORE imputation so the model can
    distinguish real vs imputed values.
    """
    logger.info("Running imputation on core matrix...")

    lab_cols = ["esr", "crp", "wbc", "rbc", "hemoglobin", "hematocrit",
                "mcv", "mch", "rdw", "platelet_count", "bmi", "illness_duration",
                "lymphocyte_pct", "neutrophil_pct"]
    present_labs = [c for c in lab_cols if c in core_matrix.columns]

    # Add missingness indicators BEFORE imputation
    for col in present_labs:
        core_matrix[f"{col}_missing"] = core_matrix[col].isna().astype(int)

    # Impute per-source to avoid cross-source contamination
    for source in core_matrix["source"].unique():
        mask = core_matrix["source"] == source
        source_df = core_matrix.loc[mask]
        n_source = len(source_df)

        median_cols = []
        knn_cols = []
        skip_cols = []

        for col in present_labs:
            miss_pct = source_df[col].isna().sum() / n_source
            if miss_pct == 0:
                continue
            elif miss_pct < 0.15:
                median_cols.append(col)
            elif miss_pct < 0.40:
                knn_cols.append(col)
            else:
                skip_cols.append(col)

        # Median imputation for low-missingness columns
        if median_cols:
            for col in median_cols:
                median_val = source_df[col].median()
                core_matrix.loc[mask, col] = core_matrix.loc[mask, col].fillna(median_val)
            logger.info("  %s: median imputed %d cols: %s", source, len(median_cols), median_cols)

        # KNN imputation for medium-missingness columns
        if knn_cols:
            # Build feature matrix: age + sex_numeric + the knn_cols themselves
            knn_df = source_df[["age"] + knn_cols].copy()
            knn_df["sex_numeric"] = source_df["sex"].map({"M": 0, "F": 1})

            # Only impute if we have enough non-null rows
            non_null_rows = knn_df.dropna(subset=["age", "sex_numeric"]).shape[0]
            if non_null_rows >= 10:
                try:
                    imputer = KNNImputer(n_neighbors=min(5, non_null_rows - 1))
                    imputed = imputer.fit_transform(knn_df)
                    imputed_df = pd.DataFrame(imputed, columns=knn_df.columns, index=knn_df.index)
                    for col in knn_cols:
                        core_matrix.loc[mask, col] = imputed_df[col]
                    logger.info("  %s: KNN imputed %d cols: %s", source, len(knn_cols), knn_cols)
                except Exception as e:
                    logger.warning("  %s: KNN imputation failed (%s), falling back to median",
                                   source, e)
                    for col in knn_cols:
                        median_val = source_df[col].median()
                        if not pd.isna(median_val):
                            core_matrix.loc[mask, col] = core_matrix.loc[mask, col].fillna(median_val)
            else:
                logger.info("  %s: too few rows for KNN (%d), using median for %s",
                            source, non_null_rows, knn_cols)
                for col in knn_cols:
                    median_val = source_df[col].median()
                    if not pd.isna(median_val):
                        core_matrix.loc[mask, col] = core_matrix.loc[mask, col].fillna(median_val)

        if skip_cols:
            logger.info("  %s: skipped (>40%% missing): %s", source, skip_cols)

    return core_matrix


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Aura Data Wrangling Pipeline")
    parser.add_argument("--full", action="store_true",
                        help="Full rebuild (default: incremental)")
    parser.add_argument("--update-nhanes-mcq", action="store_true",
                        help="Update NHANES diagnosis labels from MCQ data only")
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("AURA DATA WRANGLING PIPELINE")
    logger.info("=" * 70)

    for d in [TIER1_DIR, TIER2_DIR, TIER3_DIR]:
        os.makedirs(d, exist_ok=True)

    core_path = os.path.join(TIER1_DIR, "core_matrix.parquet")
    existing_core = None
    existing_sources = set()

    # ── Load existing core_matrix if incremental ──────────────────────────
    if not args.full and os.path.exists(core_path):
        existing_core = pd.read_parquet(core_path)
        existing_sources = set(existing_core["source"].unique())
        logger.info("Incremental mode: existing core_matrix has %d rows, sources: %s",
                     len(existing_core), existing_sources)

    # ── MCQ-only update: patch NHANES diagnosis labels in-place ───────────
    if args.update_nhanes_mcq:
        if existing_core is None:
            logger.error("No existing core_matrix.parquet found. Run --full first.")
            sys.exit(1)

        logger.info("Updating NHANES diagnosis labels from MCQ data...")
        nhanes_dir = os.path.join(RAW_DIR, "nhanes")
        mcq_cycles = {
            "2011-2012": "MCQ_G.XPT", "2013-2014": "MCQ_H.XPT",
            "2015-2016": "MCQ_I.XPT", "2017-2018": "MCQ_J.XPT",
        }
        cbc_cycles = {
            "2011-2012": "CBC_G.XPT", "2013-2014": "CBC_H.XPT",
            "2015-2016": "CBC_I.XPT", "2017-2018": "CBC_J.XPT",
        }

        MCQ_DIAGNOSIS_RULES = [
            ("MCQ195", 2.0, "rheumatoid_arthritis", "M06.9", "systemic"),
            ("MCQ195", 3.0, "psoriatic_arthritis", "M07.3", "systemic"),
            ("MCQ160N", 1.0, "lupus", "M32.9", "systemic"),
            ("MCQ160M", 1.0, "autoimmune_thyroiditis", "E06.3", "endocrine"),
            ("MCQ160K", 1.0, "celiac_disease", "K90.0", "gastrointestinal"),
        ]

        # Build SEQN -> diagnosis lookup from MCQ files
        seqn_to_diag = {}
        for cycle_name in mcq_cycles:
            mcq_path = os.path.join(nhanes_dir, mcq_cycles[cycle_name])
            cbc_path = os.path.join(nhanes_dir, cbc_cycles[cycle_name])
            try:
                mcq = pd.read_sas(mcq_path)
                cbc = pd.read_sas(cbc_path)
            except Exception as e:
                logger.warning("Skipping MCQ/CBC %s: %s", cycle_name, e)
                continue

            cbc_seqns = set(cbc["SEQN"].values)
            for _, row in mcq.iterrows():
                seqn = row["SEQN"]
                if seqn not in cbc_seqns:
                    continue
                for mcq_col, mcq_val, diag_raw, icd10, cluster in MCQ_DIAGNOSIS_RULES:
                    if mcq_col in row.index and row[mcq_col] == mcq_val:
                        if seqn not in seqn_to_diag:
                            seqn_to_diag[seqn] = (diag_raw, icd10, cluster)
                        break

        logger.info("MCQ lookup built: %d autoimmune patients found", len(seqn_to_diag))

        # Match SEQN-based patient_ids in existing core_matrix
        nhanes_mask = existing_core["source"] == "nhanes"
        updated = 0
        for idx in existing_core[nhanes_mask].index:
            pid = existing_core.loc[idx, "patient_id"]
            try:
                seqn = float(pid.replace("nhanes_", ""))
            except ValueError:
                continue
            if seqn in seqn_to_diag:
                diag_raw, icd10, cluster = seqn_to_diag[seqn]
                existing_core.loc[idx, "diagnosis_raw"] = diag_raw
                existing_core.loc[idx, "diagnosis_icd10"] = icd10
                existing_core.loc[idx, "diagnosis_cluster"] = cluster
                updated += 1

        logger.info("Updated %d NHANES rows with autoimmune diagnoses", updated)

        # Recompute z-scores and imputation for updated rows
        baselines_path = os.path.join(TIER3_DIR, "healthy_baselines.parquet")
        if os.path.exists(baselines_path):
            baselines = pd.read_parquet(baselines_path)
        else:
            baselines = build_healthy_baselines(existing_core)
            baselines.to_parquet(baselines_path, index=False)

        existing_core = compute_zscores(existing_core, baselines)
        existing_core = impute_core_matrix(existing_core)
        existing_core.to_parquet(core_path, index=False)
        logger.info("Saved updated core_matrix: %d rows", len(existing_core))
        logger.info("  Diagnosis clusters: %s",
                     existing_core["diagnosis_cluster"].value_counts(dropna=False).to_dict())
        return

    # ── Phase 1: Wrangle each source (skip existing in incremental) ───────
    core_frames = []
    tier2_outputs = {}

    # Harvard
    if "harvard" not in existing_sources:
        harvard_core, harvard_ab = wrangle_harvard()
        if harvard_core is not None:
            core_frames.append(harvard_core)
        if harvard_ab is not None:
            tier2_outputs["autoantibody_panel"] = harvard_ab
    else:
        logger.info("Skipping Harvard (already in core_matrix)")

    # NHANES
    if "nhanes" not in existing_sources:
        nhanes_core = wrangle_nhanes()
        if nhanes_core is not None:
            core_frames.append(nhanes_core)
    else:
        logger.info("Skipping NHANES (already in core_matrix)")

    # MIMIC Demo
    if "mimic_demo" not in existing_sources:
        mimic_core, mimic_labs = wrangle_mimic_demo()
        if mimic_core is not None:
            core_frames.append(mimic_core)
        if mimic_labs is not None:
            tier2_outputs["longitudinal_labs"] = mimic_labs
    else:
        logger.info("Skipping MIMIC Demo (already in core_matrix)")

    # ImmPort studies (all configured studies)
    immport_sources = {f"immport_{sid.lower()}" for sid in IMMPORT_STUDIES}
    new_immport = immport_sources - existing_sources
    if new_immport:
        logger.info("ImmPort: %d new studies to wrangle: %s", len(new_immport), sorted(new_immport))
        immport_core, immport_ab, immport_long = wrangle_all_immport()
        if immport_core is not None:
            # Only keep rows from studies not already in core
            immport_core = immport_core[immport_core["source"].isin(new_immport)]
            if len(immport_core) > 0:
                core_frames.append(immport_core)
        if immport_ab is not None:
            if "autoantibody_panel" in tier2_outputs:
                tier2_outputs["autoantibody_panel"] = pd.concat(
                    [tier2_outputs["autoantibody_panel"], immport_ab], ignore_index=True
                )
            else:
                tier2_outputs["autoantibody_panel"] = immport_ab
        if immport_long is not None:
            if "longitudinal_labs" in tier2_outputs:
                tier2_outputs["longitudinal_labs"] = pd.concat(
                    [tier2_outputs["longitudinal_labs"], immport_long], ignore_index=True
                )
            else:
                tier2_outputs["longitudinal_labs"] = immport_long
    else:
        logger.info("Skipping ImmPort (all %d studies already in core_matrix)",
                    len(IMMPORT_STUDIES))

    # ── Phase 2: Build Core Matrix ────────────────────────────────────────
    if existing_core is not None and core_frames:
        # Incremental: append new sources to existing
        all_cols = set(existing_core.columns)
        for f in core_frames:
            all_cols.update(f.columns)
        for f in core_frames:
            for col in all_cols:
                if col not in f.columns:
                    f[col] = np.nan
        for col in all_cols:
            if col not in existing_core.columns:
                existing_core[col] = np.nan

        core_matrix = pd.concat([existing_core] + core_frames, ignore_index=True)
        logger.info("Incremental: added %d new rows -> %d total",
                     sum(len(f) for f in core_frames), len(core_matrix))
    elif existing_core is not None:
        logger.info("All sources already present. Nothing to wrangle.")
        return
    elif core_frames:
        # Full rebuild
        all_cols = set()
        for f in core_frames:
            all_cols.update(f.columns)
        for f in core_frames:
            for col in all_cols:
                if col not in f.columns:
                    f[col] = np.nan
        core_matrix = pd.concat(core_frames, ignore_index=True)
    else:
        logger.error("No data loaded. Exiting.")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("CORE MATRIX ASSEMBLED: %d rows x %d cols", len(core_matrix), len(core_matrix.columns))

    # ── Phase 3: Build Tier 3 References ──────────────────────────────────
    baselines = build_healthy_baselines(core_matrix)
    icd_map = build_icd_cluster_map()

    # UCI Drug
    drug_path = os.path.join(TIER3_DIR, "drug_risk_index.parquet")
    if not os.path.exists(drug_path) or args.full:
        drug_df = wrangle_uci_drug()
    else:
        drug_df = None
        logger.info("Skipping UCI Drug (already exists)")

    # ── Phase 4: Compute Z-Scores (before imputation, using raw values) ──
    core_matrix = compute_zscores(core_matrix, baselines)

    # ── Phase 5: Imputation + missingness indicators ──────────────────────
    core_matrix = impute_core_matrix(core_matrix)

    # ── Phase 6: Save all tiers as Parquet ────────────────────────────────
    logger.info("=" * 70)
    logger.info("SAVING TO PARQUET...")

    # Tier 1
    core_matrix.to_parquet(core_path, index=False)
    logger.info("  Tier 1 - core_matrix.parquet: %d rows (%s)", len(core_matrix), core_path)

    # Tier 2
    for name, df in tier2_outputs.items():
        path = os.path.join(TIER2_DIR, f"{name}.parquet")
        df.to_parquet(path, index=False)
        logger.info("  Tier 2 - %s.parquet: %d rows", name, len(df))

    # Tier 3
    if baselines is not None:
        path = os.path.join(TIER3_DIR, "healthy_baselines.parquet")
        baselines.to_parquet(path, index=False)
        logger.info("  Tier 3 - healthy_baselines.parquet: %d rows", len(baselines))

    icd_path = os.path.join(TIER3_DIR, "icd_cluster_map.parquet")
    icd_map.to_parquet(icd_path, index=False)
    logger.info("  Tier 3 - icd_cluster_map.parquet: %d rows", len(icd_map))

    if drug_df is not None:
        drug_df.to_parquet(drug_path, index=False)
        logger.info("  Tier 3 - drug_risk_index.parquet: %d rows", len(drug_df))

    # ── Summary ───────────────────────────────────────────────────────────
    logger.info("=" * 70)
    logger.info("PIPELINE COMPLETE")
    logger.info("  Total Core Matrix rows: %d", len(core_matrix))
    logger.info("  Sources: %s", core_matrix["source"].value_counts().to_dict())
    logger.info("  Diagnosis clusters: %s",
                core_matrix["diagnosis_cluster"].value_counts(dropna=False).to_dict())
    lab_cols = ["esr", "crp", "wbc", "rbc", "hemoglobin", "hematocrit",
                "mcv", "mch", "rdw", "platelet_count"]
    for col in lab_cols:
        if col in core_matrix.columns:
            miss = core_matrix[col].isna().sum()
            pct = miss / len(core_matrix) * 100
            logger.info("  %s: %.1f%% still missing after imputation", col, pct)
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
