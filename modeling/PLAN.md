# Aura Modeling & Prediction Plan

## Executive Summary

This document outlines the implementation plan for Aura's **Hierarchical Dual-Scorer** prediction system. The goal is to build a clinically-meaningful triage engine that:

1. **Category Classifier**: Routes patients to the correct disease cluster (Systemic, Gastrointestinal, Endocrine)
2. **Disease Classifier**: Identifies specific conditions within each cluster

The modeling work is structured as a **narrative arc** for compelling hackathon presentation.

---

## Architecture: Hierarchical Dual-Scorer

```
Patient Features (Labs + Symptoms + Demographics)
                    │
                    ▼
    ┌───────────────────────────────┐
    │   STAGE 1: Category Classifier │
    │   (Systemic vs GI vs Endocrine) │
    │                               │
    │   Output: Category Confidence │
    │   e.g., "92% Systemic"        │
    └───────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    ┌───────┐   ┌───────┐   ┌───────┐
    │Systemic│   │  GI   │   │Endocr.│
    │Clf     │   │ Clf   │   │ Clf   │
    └───────┘   └───────┘   └───────┘
        │           │           │
        ▼           ▼           ▼
    SLE, RA,    IBD, Celiac,  Hashimoto's,
    Sjögren's   Crohn's       Graves'

    Output: Disease Confidence
    e.g., "65% SLE"
```

### Why Hierarchical?

1. **Clinical alignment**: Mirrors how rheumatologists/gastroenterologists/endocrinologists think
2. **Better calibration**: Confidence scores are more meaningful within clusters
3. **Modularity**: Can improve cluster-specific models independently
4. **Explainability**: Two-stage reasoning is easier to communicate

---

## Narrative Arc (Presentation Structure)

The notebooks and analysis follow this story structure:

### Act 1: "The Problem" (EDA)
> "Patients wait 4-7 years for diagnosis. Let's see this in the data."

- Diagnostic delay distributions
- Symptom overlap visualizations
- The "diagnostic odyssey" in numbers

### Act 2: "The Signal" (Feature Engineering)
> "Hidden patterns exist. Here's how we surface them."

- Lab trend analysis (slopes over time)
- Inflammatory marker persistence
- Symptom clustering
- Cross-system correlation heatmaps

### Act 3: "The Proof" (Modeling)
> "The model works. Here's the evidence."

- Baseline (Logistic Regression) → establishes interpretability
- Advanced (XGBoost/LightGBM) → demonstrates performance
- Hierarchical architecture validation
- ROC curves, precision-recall, calibration plots

### Act 4: "The Trust" (Explainability + Fairness)
> "We can explain every prediction. The model is fair."

- SHAP analysis (global + local)
- Feature importance rankings
- Subgroup performance audits (sex, age, race)
- Calibration by subgroup

### Act 5: "The Impact" (Case Studies)
> "Real patients, real stories, real earlier diagnoses."

- 3-5 curated cases demonstrating:
  - Clear true positive (model catches early)
  - High category confidence, uncertain disease
  - Edge case with good explanation
- Time-to-diagnosis simulation

---

## Data Strategy

### Priority Datasets (Phase 1 - Hackathon Core)

| Dataset | Records | Use Case | Priority |
|---------|---------|----------|----------|
| Harvard Dataverse (Rheumatic) | 12,085 | Systemic cluster training | **P0** |
| Kaggle Autoimmune | 12,500 | CBC features + outcomes | **P0** |
| Kaggle GI Disease | 30,560 | GI cluster training | **P0** |
| Flaredown Patient-Reported | 1,700+ | Real-world symptoms | **P1** |
| NHANES | Large | Population baselines | **P1** |

### Enhancement Datasets (Phase 2 - Post-MVP)

| Dataset | Use Case |
|---------|----------|
| ADEx Transcriptomics | Gene expression signatures |
| ImmPort 10KIP | Healthy reference thresholds |
| HugeAmp GWAS | Genetic risk scores |
| GMrepo Microbiome | Gut-immune axis features |

### Feature Categories

```
DEMOGRAPHIC
├── Age, Sex, Ethnicity
└── Geographic region (for environmental factors)

LABORATORY (Core)
├── CBC: RBC, WBC, Hemoglobin, Hematocrit, MCV, MCH
├── Inflammatory: CRP, ESR
├── Autoantibodies: ANA, RF, Anti-CCP, Anti-dsDNA
├── Complement: C3, C4
└── Specific: Fecal Calprotectin (GI), TSH (Endocrine)

TEMPORAL
├── Lab value slopes (Δ over time)
├── Visit frequency
├── Time since first symptoms
└── Flare-remission patterns

SYMPTOM-DERIVED
├── Symptom count by system
├── Symptom co-occurrence clusters
└── Severity scores (if available)
```

---

## Model Specifications

### Stage 1: Category Classifier

**Task**: 3-class classification (Systemic, GI, Endocrine)

**Models to evaluate**:
- Logistic Regression (multinomial) - baseline
- XGBoost - primary
- LightGBM - alternative

**Key metrics**:
- Macro-averaged AUC
- Per-class sensitivity (critical: don't miss any category)
- Calibration (Brier score)

### Stage 2: Disease Classifiers (per cluster)

**Systemic Cluster**:
- Classes: SLE, RA, Sjögren's, PsA, AS, Reactive Arthritis, Control
- Key features: ANA, Anti-dsDNA, RF, Anti-CCP, HLA-B27

**GI Cluster**:
- Classes: IBD (Crohn's/UC), Celiac, Functional GI, Control
- Key features: Fecal Calprotectin, CRP, ESR, symptom patterns

**Endocrine Cluster** (if time permits):
- Classes: Hashimoto's, Graves', T1D, Control
- Key features: TSH, TPO antibodies, glucose patterns

---

## Explainability Requirements

### Global Explanations
- Feature importance rankings (per model)
- SHAP summary plots
- Partial dependence plots for top features

### Local Explanations (per prediction)
- SHAP waterfall plots
- Natural language explanation generation:
  > "This patient was flagged for Systemic autoimmune evaluation (92% confidence) due to:
  > - Elevated ANA titer (1:320)
  > - Persistent CRP elevation over 3 visits
  > - Joint pain + fatigue symptom combination"

### Case-Level Documentation
- For demo cases: full explanation narratives
- Visual patient journey timelines

---

## Bias Audit Plan

### Subgroups to evaluate
- **Sex**: Female vs Male (autoimmune diseases disproportionately affect women)
- **Age**: <30, 30-50, >50
- **Race/Ethnicity**: Where available in data

### Metrics by subgroup
- AUC
- Sensitivity at fixed specificity (0.90)
- Calibration slope
- False negative rate (critical for screening)

### Mitigation strategies
- Stratified cross-validation
- Subgroup-aware threshold tuning
- Report performance gaps transparently

---

## File Structure

```
modeling/
├── README.md                    # This overview
├── PLAN.md                      # This document
│
├── data/
│   ├── raw/                     # Original downloads (gitignored)
│   ├── processed/               # Cleaned, merged
│   ├── features/                # Engineered feature sets
│   └── splits/                  # Train/val/test (reproducible seeds)
│
├── notebooks/
│   ├── 01_data_exploration.ipynb      # Act 1: The Problem
│   ├── 02_feature_engineering.ipynb   # Act 2: The Signal
│   ├── 03_baseline_models.ipynb       # Act 3: The Proof (Part 1)
│   ├── 04_advanced_models.ipynb       # Act 3: The Proof (Part 2)
│   ├── 05_explainability.ipynb        # Act 4: The Trust (Part 1)
│   ├── 06_bias_audit.ipynb            # Act 4: The Trust (Part 2)
│   └── 07_case_studies.ipynb          # Act 5: The Impact
│
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loaders.py                 # Dataset-specific loaders
│   │   ├── preprocessing.py           # Cleaning, normalization
│   │   └── feature_engineering.py     # Feature creation
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── category_classifier.py     # Stage 1
│   │   ├── disease_classifier.py      # Stage 2
│   │   ├── dual_scorer.py             # Combined pipeline
│   │   └── baselines.py               # Interpretable models
│   │
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── metrics.py                 # AUC, sensitivity, specificity
│   │   ├── subgroup_analysis.py       # Bias auditing
│   │   └── calibration.py             # Confidence calibration
│   │
│   └── explainability/
│       ├── __init__.py
│       ├── shap_analysis.py
│       ├── feature_importance.py
│       └── case_explanations.py       # Natural language explanations
│
├── experiments/
│   ├── configs/                       # Experiment YAML configs
│   ├── logs/                          # Training logs
│   └── checkpoints/                   # Saved models
│
├── outputs/
│   ├── figures/                       # Publication-ready plots
│   ├── tables/                        # Performance tables
│   └── reports/                       # Generated reports
│
└── presentation/
    ├── demo_cases/                    # Curated demo patients
    ├── story_arc.md                   # Presentation script
    └── key_findings.md                # Judge-ready bullet points
```

---

## Success Criteria

### Technical
- [ ] Category classifier AUC > 0.85
- [ ] Disease classifier AUC > 0.75 (per cluster)
- [ ] Calibration error < 0.1
- [ ] All predictions explainable via SHAP

### Presentation
- [ ] Clear narrative arc from problem to impact
- [ ] 3-5 compelling demo cases prepared
- [ ] Bias audit shows no critical disparities
- [ ] < 5 minute pitch with live demo

### Ethical
- [ ] Framed as "clinical decision support" not "diagnosis"
- [ ] Limitations clearly documented
- [ ] Subgroup performance transparently reported

---

## Timeline (Hackathon Sprint)

| Phase | Focus | Deliverables |
|-------|-------|--------------|
| 1 | Data acquisition + EDA | Notebooks 01, cleaned data |
| 2 | Feature engineering | Notebook 02, feature sets |
| 3 | Baseline models | Notebook 03, initial results |
| 4 | Advanced models | Notebook 04, best models |
| 5 | Explainability | Notebook 05, SHAP analysis |
| 6 | Bias audit | Notebook 06, fairness report |
| 7 | Case studies + demo | Notebook 07, demo cases |
| 8 | Polish + presentation | Final pitch materials |

---

## Dependencies

```
# Core
pandas>=2.0
numpy>=1.24
scikit-learn>=1.3

# Modeling
xgboost>=2.0
lightgbm>=4.0

# Explainability
shap>=0.43

# Visualization
matplotlib>=3.7
seaborn>=0.12
plotly>=5.15

# Data loading
openpyxl  # Excel files
kaggle    # Kaggle API

# Notebooks
jupyterlab>=4.0
```

---

## Contact

**Modeling Lead**: [Your name]
**Last Updated**: 2026-02-21
