# Aura — AI-Powered Autoimmune Triage

> *"Your symptoms have a pattern. We find it."*

Aura is a privacy-first, local AI platform that analyzes a patient's lab results and symptom history, identifies likely autoimmune disease patterns, and produces a structured clinical report the patient can hand directly to their doctor — cutting years off the diagnostic odyssey.

---

## The Problem

Autoimmune diseases are among the most misdiagnosed and delayed-diagnosed conditions in modern medicine.

- **50+ million Americans** live with an autoimmune disease
- The average patient waits **3–5 years** before receiving a correct diagnosis
- They visit an average of **4–6 different doctors** before anyone connects the dots
- During that window they are often told their symptoms are stress, anxiety, or "just getting older"
- Misdiagnosis leads to wrong treatments — sometimes ones that actively worsen autoimmune conditions

The diagnostic delay is not a failure of medicine. It is a failure of **information flow**. Each specialist sees a slice. No one sees the whole pattern.

Aura fixes that.

---

## What Aura Does

Aura takes everything a patient already has — their blood panels, uploaded lab PDFs, symptom descriptions, and medical photos — and runs it through a hierarchical AI pipeline that:

1. **Identifies which disease cluster** the patient's labs and symptoms point toward (systemic autoimmune, gastrointestinal, endocrine, or healthy)
2. **Narrows to a specific likely condition** within that cluster (e.g., Lupus vs. Rheumatoid Arthritis vs. Sjögren's)
3. **Generates a confidence score** for each finding, calibrated against 88,000+ real patient records
4. **Produces two outputs** — a plain-English summary the patient can understand, and a structured clinical SOAP note the doctor can act on immediately

Aura does not diagnose. It triages, patterns, and translates — giving patients the vocabulary and evidence to have a productive first conversation with the right specialist, instead of showing up with a folder of disconnected lab printouts.

---

## Who It Helps

### Patients
- Walk into appointments with a structured, evidence-backed report rather than anecdotal descriptions
- Know which type of specialist to ask for a referral to
- Understand what their own lab values mean relative to healthy baselines and disease patterns
- End the loop of being dismissed — the report speaks the language of medicine

### Primary Care Physicians
- Receive a pre-processed clinical summary that flags autoimmune patterns before the consultation
- Reduce time spent interpreting scattered prior records
- Make smarter referral decisions on the first visit rather than the third

### Specialists
- Patients arrive with the right referral and relevant prior workup already organized
- First appointment can focus on confirmation and treatment planning, not intake from scratch

### Insurance Companies
- Fewer redundant specialist visits and unnecessary diagnostic panels
- Earlier correct diagnosis means treatment starts sooner — reducing long-term claims from disease progression
- One structured AI triage visit replaces 3–4 exploratory specialist visits

### Health Systems & Clinics
- Reduces unnecessary referral chains that clog specialist schedules
- Shortens the average time from first symptom to treatment plan
- Captures clinical value from lab data that would otherwise be siloed

---

## The Economic Case

### Per Patient

| Scenario | Without Aura | With Aura | Saved |
|---|---|---|---|
| Specialist visits to diagnosis | 4–6 visits | 2–3 visits | 2–3 visits |
| Cost per specialist visit | ~$350–$700 | — | — |
| Direct visit savings | — | — | **$700–$2,100 per patient** |
| Diagnostic odyssey duration | 3–5 years | Months | Years of quality life |
| Mismanagement costs (wrong Rx, ER) | $5,000–$20,000 | Reduced significantly | **Est. $3,000–$15,000 per patient** |

### At Scale

| Stakeholder | Annual Opportunity |
|---|---|
| **Patients** | $700–$2,100 in direct visit savings; years earlier treatment |
| **Insurance companies** | ~$3,000–$15,000 per claim in avoided redundant care |
| **US health system** | 50M patients × even 1 visit saved = **$17.5B–$35B annually** |
| **Clinics** | 15–30 min saved per consultation × volume = significant physician capacity freed |

These are conservative estimates. The compounding benefit of catching autoimmune disease 2–3 years earlier — before organ damage, disability, or treatment-resistant progression — dwarfs the direct visit savings.

---

## How Much Time Aura Saves

Our visit simulation (notebook `07_visit_simulation.ipynb`) models patient journeys across progressive clinical information — simulating what the model knows after each visit.

Key findings from 88,742 patient records:
- The model reaches **>80% confidence** at visit 2 for most patients
- Average **1.8 visits saved** before a confident triage decision
- For systemic autoimmune diseases (Lupus, RA, Sjögren's), confident pattern detection occurs ~2 visits earlier than traditional diagnostic timelines
- At $700/visit, the average patient saves **$1,260 in direct costs**

For the average patient spending 3–5 years in the diagnostic odyssey, Aura compresses this to months — not by replacing doctors, but by ensuring every appointment counts.

---

## The Pipeline

```
Patient Input
    │
    ├── Lab PDFs / Blood panels
    ├── Symptom descriptions (free text)
    └── Medical photos (optional)
         │
         ▼
┌─────────────────────────────┐
│  Agent 1: Extractor         │  Parses PDFs → structured JSON
│  + Vision Model             │  Translates images → clinical keywords
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Agent 2: RAG Engine        │  Queries local PubMed vector database
│                             │  Grounds findings in peer-reviewed literature
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│  Agent 3: Hierarchical Dual-Scorer                  │
│                                                     │
│  Stage 1 — Category Classifier (XGBoost)            │
│    Trained on 88,742 patients                       │
│    Output: probability over 4 clusters              │
│      → Healthy / Systemic / GI / Endocrine          │
│    Test AUC: ~0.90                                  │
│                                                     │
│  Stage 2 — Disease Classifier (per cluster)         │
│    Systemic:      SLE, RA, Sjögren's, PsA, AS       │
│    GI:            IBD, Celiac, Functional GI        │
│    Endocrine:     Hashimoto's, Graves', T1D         │
│    Output: specific disease + confidence score      │
│    Systemic AUC: >0.92                              │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Agent 4: Translator        │  Drafts plain-English patient summary
│                             │  Drafts clinical SOAP note with DOI citations
└──────────────┬──────────────┘
               │
         ┌─────┴─────┐
         ▼           ▼
   Patient View   Doctor View
   Plain English  Clinical SOAP Note
   + Next Steps   + Literature Grounding
                  + Referral Recommendation
```

### Data Foundation

The model is trained on a curated, three-tier dataset architecture:

| Tier | Contents | Size |
|---|---|---|
| **Tier 1** — Core Matrix | CBC, inflammatory markers, demographics, diagnoses | 88,742 patients |
| **Tier 2** — Enrichment | Autoantibody panels, longitudinal labs (MIMIC-IV), GWAS hits (FinnGen R12) | 12,085 + 19,646 + 67,869 records |
| **Tier 3** — Reference | Age/sex-stratified healthy baselines, ICD-10 cluster map, drug risk index | 110 + 111 + 597 records |

### Feature Engineering

Raw lab values are transformed into clinically meaningful signals:
- **Z-scores** against age/sex-matched healthy baselines (not population averages)
- **Inflammatory ratios** — CRP/ESR ratio, neutrophil-lymphocyte ratio (NLR), platelet-lymphocyte ratio (PLR)
- **Anemia pattern flags** — microcytic, macrocytic, normocytic
- **Autoantibody composite scores** — lupus panel, RA panel, complement consumption
- **Missingness flags** — which labs are absent is itself a clinical signal

### Model Comparison (Test Set)

| Model | AUC | Class Imbalance Handling |
|---|---|---|
| Logistic Regression | ~0.87 | `balanced` |
| XGBoost | ~0.90 | None (powers Dual-Scorer) |
| LightGBM | see output | `balanced` |
| Random Forest | see output | `balanced_subsample` |
| CatBoost | see output | `auto_class_weights` |

---

## Privacy & Design Philosophy

Aura is built **local-first**. No patient data leaves the device. The vector database, model inference, and report generation all run on the user's machine. This is non-negotiable for medical AI.

The UI is designed to communicate appropriate uncertainty:
- Confidence scores are always shown — never hidden
- A permanent disclaimer distinguishes pattern matching from clinical diagnosis
- Medical terms surface plain-English tooltips on hover
- The SOAP note output is clearly framed as AI-assisted, not AI-decided

---

## Repository Structure

```
aura/
├── modeling/                  # ML pipeline (see modeling/README.md)
│   ├── notebooks/             # Jupyter notebooks (numbered narrative arc)
│   ├── src/                   # Production Python modules
│   │   ├── data/              # Loaders, preprocessing, feature engineering
│   │   └── models/            # CategoryClassifier, DiseaseClassifier, DualScorer
│   ├── data/processed/        # Tiered parquet datasets
│   └── outputs/               # Figures, trained models
├── scripts/                   # Data fetch utilities
├── dataspec.md                # Full dataset specifications
└── requirements.txt
```

---

## Getting Started

```bash
# Clone and install
git clone https://github.com/your-org/aura
pip install -r requirements.txt

# Run the modeling pipeline (in order)
jupyter lab modeling/notebooks/

# Notebooks:
# 01_data_exploration     — understand the patient population
# 02_feature_engineering  — build clinically meaningful features
# 03_baseline_models      — logistic regression baseline
# 04_advanced_models      — XGBoost, LightGBM, Random Forest, CatBoost shootout
# 05_explainability       — SHAP values, feature attribution
# 06_bias_audit           — fairness across age, sex, demographics
# 07_visit_simulation     — confidence over time, cost savings analysis
```

---

## Design Language

**Colors:** `#0A0D14` background · `#7B61FF` violet (trust) · `#3ECFCF` teal (precision) · `#F4A261` amber (urgency)

**Typography:** `Clash Display` headings · `Inter` body · `JetBrains Mono` scores

**Animation:** Three-layer background — aurora mesh gradient, Brownian particle field, mouse-tracking radial glow

---

*Aura does not replace physicians. It gives patients the tools to be heard, and gives doctors the signal to act on.*
