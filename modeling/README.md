# Aura Modeling & Prediction

This directory contains the machine learning pipeline for Aura's autoimmune disease triage system.

## Quick Links

| Document | Purpose |
|----------|---------|
| [PLAN.md](PLAN.md) | Full implementation plan with architecture and narrative arc |
| [agents.md](agents.md) | Context document for AI agents working on this component |
| [../dataspec.md](../dataspec.md) | Data source specifications |

## Architecture

**Hierarchical Dual-Scorer**:
1. **Stage 1**: Category Classifier (Systemic vs GI vs Endocrine)
2. **Stage 2**: Disease Classifier (specific diseases within each cluster)

## Directory Structure

```
modeling/
├── data/
│   ├── raw/           # Original datasets (gitignored)
│   ├── processed/     # Cleaned, merged data
│   ├── features/      # Engineered feature sets
│   └── splits/        # Train/val/test splits
│
├── notebooks/         # Jupyter notebooks (numbered by narrative act)
├── src/               # Production-ready Python modules
├── experiments/       # Model training artifacts
├── outputs/           # Figures, tables, reports
└── presentation/      # Demo and pitch materials
```

## Narrative Arc (Notebooks)

| Notebook | Act | Story |
|----------|-----|-------|
| 01_data_exploration | The Problem | Diagnostic delays in the data |
| 02_feature_engineering | The Signal | Hidden patterns revealed |
| 03_baseline_models | The Proof (1) | Interpretable models work |
| 04_advanced_models | The Proof (2) | Advanced models excel |
| 05_explainability | The Trust (1) | Every prediction explained |
| 06_bias_audit | The Trust (2) | Fair across demographics |
| 07_case_studies | The Impact | Real patient stories |

## Getting Started

```bash
# Install dependencies
pip install -r ../requirements.txt

# Download datasets (see dataspec.md for details)
kaggle datasets download -d abdullahragheb/all-autoimmune-disorder-10k

# Run notebooks in order
jupyter lab notebooks/
```

## Key Metrics

Target performance:
- Category Classifier AUC: > 0.85
- Disease Classifier AUC: > 0.75
- Calibration Error: < 0.1
