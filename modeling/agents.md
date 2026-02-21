# Aura Modeling - Agent Context Document

This document provides essential context for AI agents working on the Aura modeling and prediction system.

---

## Project Overview

**Aura** is a clinical decision support system for early autoimmune disease detection. The modeling component implements a **Hierarchical Dual-Scorer** that:

1. **Stage 1 (Category Classifier)**: Classifies patients into disease clusters (Systemic, Gastrointestinal, Endocrine)
2. **Stage 2 (Disease Classifier)**: Identifies specific diseases within the predicted cluster

This is a **hackathon project** - prioritize working demos over perfect code.

---

## Critical Context

### The Human Problem
- Patients wait **4-7 years** for autoimmune diagnosis
- Symptoms are vague, overlapping, and often dismissed
- Women are disproportionately affected
- Early intervention prevents irreversible organ damage
- **Frame this as augmenting physician judgment, not replacing doctors**

### Technical Approach
- **Hierarchical architecture**: Category → Disease (not flat multi-class)
- **Explainability is mandatory**: Every prediction must have SHAP explanations
- **Bias auditing required**: Stratify all metrics by sex, age, race
- **This is decision support, NOT diagnosis**

---

## Key Files

| File | Purpose |
|------|---------|
| `modeling/PLAN.md` | Full implementation plan with narrative arc |
| `dataspec.md` | Data sources and acquisition protocols |
| `narrative.md` | Project mission and user journey |
| `README.md` | System architecture blueprint |

---

## Data Sources (Priority Order)

### P0 - Core Training Data
1. **Harvard Dataverse (Rheumatic)**: 12,085 records - Systemic diseases
   - Features: ESR, CRP, C3, C4, RF, Anti-CCP, ANA, anti-dsDNA, HLA-B27
   - Download: https://doi.org/10.7910/DVN/VM4OR3

2. **Kaggle Autoimmune**: 12,500 records - CBC metrics
   - Features: Age, Gender, RBC, Hemoglobin, Hematocrit, MCV, MCH
   - Command: `kaggle datasets download -d abdullahragheb/all-autoimmune-disorder-10k`

3. **Kaggle GI Disease**: 30,560 records - GI cluster
   - Features: Age, Gender, BMI, CRP/ESR, Fecal Calprotectin
   - Download via Kaggle API or web

### P1 - Enhancement Data
- NHANES: Population baselines
- Flaredown: Patient-reported symptoms
- ImmPort 10KIP: Healthy reference thresholds

---

## Disease Clusters

### Systemic Autoimmune
- **Diseases**: SLE, RA, Sjögren's, PsA, Ankylosing Spondylitis, Reactive Arthritis
- **Key markers**: ANA, Anti-dsDNA, RF, Anti-CCP, HLA-B27, C3/C4
- **Primary data**: Harvard Dataverse

### Gastrointestinal
- **Diseases**: IBD (Crohn's, UC), Celiac, Functional GI disorders
- **Key markers**: Fecal Calprotectin, CRP, ESR
- **Primary data**: Kaggle GI Dataset

### Endocrine (Lower priority for hackathon)
- **Diseases**: Hashimoto's, Graves', Type 1 Diabetes
- **Key markers**: TSH, TPO antibodies, glucose patterns
- **Data**: May need to synthesize or use NHANES

---

## Feature Engineering Requirements

### Lab Trends (Temporal)
```python
# Example: CRP slope over time
def compute_lab_slope(patient_labs, marker='CRP'):
    """Compute rate of change for a lab marker."""
    # Sort by date, fit linear regression
    # Return slope coefficient
```

### Symptom Clustering
- Group symptoms by organ system
- Count co-occurring symptoms
- Flag multi-system involvement

### Inflammatory Persistence
- Duration of elevated CRP/ESR
- Number of visits with inflammation markers

---

## Model Specifications

### Category Classifier (Stage 1)
- **Input**: Demographic + Lab + Symptom features
- **Output**: Probability distribution over [Systemic, GI, Endocrine]
- **Primary model**: XGBoost
- **Baseline**: Logistic Regression (for interpretability)

### Disease Classifier (Stage 2)
- **One model per cluster**
- **Input**: Same features + cluster-specific markers
- **Output**: Probability distribution over diseases in that cluster

### Dual-Scorer Pipeline
```python
class DualScorer:
    def __init__(self, category_model, disease_models):
        self.category_model = category_model
        self.disease_models = disease_models  # dict: cluster -> model

    def predict(self, X):
        # Stage 1: Category prediction
        category_probs = self.category_model.predict_proba(X)
        predicted_category = category_probs.argmax()
        category_confidence = category_probs.max()

        # Stage 2: Disease prediction (within predicted category)
        disease_model = self.disease_models[predicted_category]
        disease_probs = disease_model.predict_proba(X)
        disease_confidence = disease_probs.max()

        return {
            'category': predicted_category,
            'category_confidence': category_confidence,
            'disease': disease_probs.argmax(),
            'disease_confidence': disease_confidence
        }
```

---

## Explainability Requirements

### Every prediction must include:
1. **SHAP values** for top contributing features
2. **Natural language explanation**:
   > "Flagged for Systemic evaluation (92% confidence) due to elevated ANA (1:320), persistent CRP, and joint pain + fatigue combination."

3. **Feature importance plot** (for presentation)

### Libraries
- `shap` for SHAP values
- Custom `case_explanations.py` for natural language generation

---

## Evaluation Metrics

### Primary Metrics
- **AUC-ROC**: Primary performance metric
- **Sensitivity at 90% specificity**: Clinical utility
- **Brier Score**: Calibration quality

### Subgroup Analysis (Required)
```python
def evaluate_subgroups(y_true, y_pred, demographics):
    """Evaluate model performance across demographic subgroups."""
    results = {}
    for group in ['sex', 'age_group', 'race']:
        for value in demographics[group].unique():
            mask = demographics[group] == value
            results[f'{group}_{value}'] = {
                'auc': roc_auc_score(y_true[mask], y_pred[mask]),
                'n': mask.sum()
            }
    return results
```

---

## Notebook Conventions

### Naming
- `01_data_exploration.ipynb` - Act 1: The Problem
- `02_feature_engineering.ipynb` - Act 2: The Signal
- `03_baseline_models.ipynb` - Act 3: The Proof (Part 1)
- `04_advanced_models.ipynb` - Act 3: The Proof (Part 2)
- `05_explainability.ipynb` - Act 4: The Trust (Part 1)
- `06_bias_audit.ipynb` - Act 4: The Trust (Part 2)
- `07_case_studies.ipynb` - Act 5: The Impact

### Structure
Each notebook should have:
1. **Narrative header**: What story are we telling?
2. **Key findings summary**: 3-5 bullet points at the top
3. **Reproducible code**: Seeds set, paths relative
4. **Visualizations**: Publication-ready, labeled axes

---

## Code Style

### Module Organization
```
src/
├── data/           # Data loading and preprocessing
├── models/         # Model definitions
├── evaluation/     # Metrics and analysis
└── explainability/ # SHAP and explanations
```

### Conventions
- Type hints for function signatures
- Docstrings for public functions
- No hardcoded paths (use config or relative)
- Reproducible random seeds

---

## Presentation Requirements

### Demo Cases (3-5 required)
1. **Clear win**: Model catches early what was missed
2. **Nuanced case**: Shows good explainability
3. **Dual-score demo**: High category confidence, uncertain disease
4. **Edge case**: Model handles gracefully

### Key Metrics to Highlight
- Category classifier AUC
- Time-to-diagnosis improvement estimate
- Subgroup fairness results

---

## Common Pitfalls to Avoid

1. **Don't overfit to majority class**: Autoimmune diseases are rare
2. **Don't ignore calibration**: Confidence scores must be meaningful
3. **Don't skip bias audit**: This is healthcare - fairness matters
4. **Don't use diagnosis language**: Always "decision support" or "risk stratification"
5. **Don't forget explainability**: Black box models won't impress healthcare judges

---

## Quick Start for New Agents

```bash
# 1. Navigate to modeling directory
cd modeling

# 2. Check the plan
cat PLAN.md

# 3. Check current task status
# (Use TaskList tool)

# 4. Review data specification
cat ../dataspec.md

# 5. Start with highest priority uncompleted task
```

---

## Contact Points

- **Modeling Lead**: Responsible for prediction architecture
- **Full project context**: See `README.md` and `narrative.md` in project root

---

*Last updated: 2026-02-21*
