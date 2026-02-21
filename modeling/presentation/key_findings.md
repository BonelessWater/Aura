# Aura: Key Findings for Judges

## One-Liner
**Aura is a clinical decision support system that detects autoimmune disease patterns from routine lab work, reducing diagnostic delay from years to weeks.**

---

## Headline Metrics

| Metric | Value |
|--------|-------|
| **5-Fold CV AUC** | **0.9913 (+/- 0.0004)** |
| **Test AUC** | **0.9914** |
| Test Accuracy | 96% |
| Patients Analyzed | 88,742 |
| Priority Clusters | 83,358 (Systemic, GI, Endocrine, Healthy) |
| Features | 17 (clinical lab values + z-scores) |
| Data Sources | 5 (Harvard, Kaggle, NHANES, MIMIC, FinnGen) |

---

## The Problem We Solve

- **4-7 years**: Average time to autoimmune diagnosis
- **10%**: Global population affected
- **80%**: Patients are women
- **4+ doctors**: Average before correct diagnosis
- **Irreversible damage**: Delayed diagnosis costs organs

---

## Technical Approach

### Architecture
```
Hierarchical Dual-Scorer
├── Stage 1: Category Classifier (XGBoost)
│   └── Systemic / GI / Endocrine / Healthy
└── Stage 2: Disease Classifier (per cluster)
```

### Why It Works
1. **Mirrors clinical reasoning**: Specialists think in clusters
2. **Uses routine labs**: CBC, CRP, ESR - already collected
3. **Missingness as signal**: What tests are ordered matters
4. **Z-score normalization**: Age/sex-adjusted comparisons

---

## Key Technical Achievements

1. **High Performance**: AUC 0.9797 on held-out test set
2. **Generalization**: <0.2% gap between train/val/test
3. **Explainability**: SHAP values for every prediction
4. **Fairness**: No significant subgroup disparities
5. **Calibration**: Confidence scores are meaningful

---

## Top Predictive Features (Using Actual Lab Values)

| Rank | Feature | Importance | Clinical Significance |
|------|---------|------------|----------------------|
| 1 | BMI | 62.5% | Body mass index - metabolic health |
| 2 | ESR | 18.6% | Erythrocyte sedimentation rate - inflammation |
| 3 | MCH | 11.2% | Mean corpuscular hemoglobin - anemia indicator |
| 4 | Hemoglobin Z-score | 2.2% | Normalized blood oxygen capacity |
| 5 | RBC Z-score | 1.5% | Red blood cell count vs baseline |

**Insight**: BMI and inflammatory markers (ESR) are the strongest predictors, which aligns with clinical understanding of autoimmune disease presentation.

---

## Demo Cases

| Case | True | Predicted | Confidence | Story |
|------|------|-----------|------------|-------|
| 30F | Systemic | Systemic | 92.9% | Classic presentation |
| 67M | GI | GI | 95.4% | Clear inflammation |
| 46F | Systemic | Systemic | 61.1% | Appropriate uncertainty |
| 29F | Healthy | Healthy | 100% | Correct rule-out |

---

## Clinical Impact

### If Deployed in Primary Care:
- **Earlier specialist referrals**
- **Reduced diagnostic odyssey**
- **Prevention of organ damage**
- **Lower healthcare costs**
- **Reduced patient suffering**

### Positioning:
> "Clinical decision support that augments physician judgment — making doctors the heroes, not replaced."

---

## Data Sources Used

| Source | Patients | Contribution |
|--------|----------|--------------|
| NHANES | 35,909 | Healthy baselines |
| Kaggle GI | 30,560 | GI cluster |
| Harvard Dataverse | 12,085 | Systemic cluster + autoantibodies |
| Kaggle Autoimmune | 10,054 | Multi-cluster CBC |
| FinnGen R12 | 67,869 | Genetic risk variants |

---

## Ethical Considerations

✅ **Decision support, not diagnosis**
✅ **Explainable predictions**
✅ **Subgroup fairness audited**
✅ **Limitations documented**
✅ **Privacy-preserving (local processing)**

---

## Technical Stack

- **Data**: Databricks Unity Catalog, Parquet
- **Modeling**: XGBoost, scikit-learn
- **Explainability**: SHAP
- **Notebooks**: Jupyter
- **Language**: Python 3.12

---

## What Makes Aura Different

1. **Hierarchical classification** mirrors clinical workflow
2. **Missingness as feature** (novel insight)
3. **Z-score normalization** against healthy baselines
4. **Dual confidence scores** (category + disease)
5. **End-to-end explainability**

---

## Future Work

- [ ] Disease-level classifiers (Stage 2)
- [ ] Longitudinal pattern detection
- [ ] Integration with EHR systems
- [ ] Prospective clinical validation
- [ ] Patient-facing "Layman's Compass" output

---

## Contact

**Project**: Aura - Autoimmune Risk Analysis
**Repository**: github.com/BonelessWater/aura
