# Aura Presentation: Story Arc

## The 5-Act Narrative

---

## Act 1: The Problem (60 seconds)

### Opening Hook
> "Imagine waiting 5 years to find out why you're exhausted, in pain, and your doctors keep saying it's stress."

### Key Points
- **4-7 years**: Average diagnostic delay for autoimmune diseases
- **10% of population**: Affected by autoimmune conditions
- **Women disproportionately affected**: 80% of autoimmune patients
- **The Diagnostic Odyssey**: Patients see 4+ doctors before diagnosis
- **Irreversible damage**: Delayed diagnosis leads to organ damage

### Transition
> "What if we could help clinicians recognize these patterns earlier?"

---

## Act 2: The Signal (60 seconds)

### Key Points
- **Hidden patterns exist** in routine lab work
- **CBC + inflammatory markers** contain diagnostic signals
- **Z-score normalization** reveals deviations from healthy baselines
- **Missingness is informative**: Which tests are ordered matters

### Data Highlights
- 88,742 patients analyzed
- 11 disease clusters identified
- 44 features extracted
- Z-scores computed against age/sex-matched healthy controls

### Visual
Show correlation heatmap or z-score distributions by cluster

### Transition
> "We built a hierarchical model to surface these signals."

---

## Act 3: The Proof (90 seconds)

### Architecture
```
Patient Labs → Category Classifier → Disease Cluster
                     ↓
              (Systemic / GI / Endocrine / Healthy)
```

### Results

| Metric | Value |
|--------|-------|
| **Test AUC** | **0.9797** |
| Train AUC | 0.9816 |
| Validation AUC | 0.9800 |

### Key Points
- **Hierarchical approach**: Mirrors clinical thinking
- **XGBoost classifier**: Robust, fast, interpretable
- **Strong generalization**: Consistent across train/val/test

### Visual
Show ROC curves or confusion matrix

### Transition
> "But performance alone isn't enough. We need to explain why."

---

## Act 4: The Trust (60 seconds)

### Explainability
- **Every prediction explained** via SHAP values
- **Natural language summaries** for clinicians
- **Feature importance** rankings transparent

### Example Explanation
> "Patient flagged for Systemic evaluation (93% confidence) due to:
> - Elevated ESR relative to normal
> - Pattern of ordered inflammatory tests
> - Age and symptom profile consistent with autoimmune"

### Fairness
- **Subgroup analysis** by sex, age
- **No significant disparities** detected
- **Calibrated confidence** scores

### Transition
> "Let's see this in action with real cases."

---

## Act 5: The Impact (90 seconds)

### Demo Cases

| Case | Patient | Prediction | Confidence |
|------|---------|------------|------------|
| 1 | 30F | Systemic ✓ | 92.9% |
| 2 | 67M | GI ✓ | 95.4% |
| 3 | 46F | Systemic ✓ | 61.1% |
| 4 | 29F | Healthy ✓ | 100% |

### Live Demo
Walk through one case with full explanation

### Impact Statement
> "If deployed in primary care, Aura could reduce diagnostic delay from years to weeks."

### Clinical Value
- **Augments physician judgment** (doesn't replace)
- **Routes to correct specialist** faster
- **Prevents irreversible damage** through early intervention
- **Reduces patient suffering** during diagnostic odyssey

---

## Closing (30 seconds)

### Summary
1. **The Problem**: 4-7 year diagnostic delay causes suffering
2. **The Signal**: Patterns exist in routine labs
3. **The Proof**: AUC 0.9797 with hierarchical classification
4. **The Trust**: Every prediction explainable and fair
5. **The Impact**: Earlier diagnosis, better outcomes

### Call to Action
> "Aura makes doctors the heroes by giving them the tools to recognize autoimmune patterns earlier."

### Final Slide
- **Test AUC: 0.9797**
- **88,742 patients**
- **4 disease clusters**
- **Fully explainable**

---

## Timing Summary

| Act | Duration | Cumulative |
|-----|----------|------------|
| 1. Problem | 60s | 1:00 |
| 2. Signal | 60s | 2:00 |
| 3. Proof | 90s | 3:30 |
| 4. Trust | 60s | 4:30 |
| 5. Impact | 90s | 6:00 |
| Close | 30s | 6:30 |

**Total: ~6.5 minutes** (with buffer for demo)

---

## Q&A Prep

### Anticipated Questions

1. **"What about rare autoimmune diseases?"**
   > "Our hierarchical approach routes to the correct specialist cluster first. Disease-specific classification is Stage 2."

2. **"How do you handle missing data?"**
   > "Missingness flags are features. Which tests clinicians order is itself diagnostic signal."

3. **"What's the false positive rate?"**
   > "At 90% specificity, we achieve X% sensitivity. The tool flags for further evaluation, not diagnosis."

4. **"How would this integrate with EHRs?"**
   > "The model takes standard lab values. Integration is a FHIR API call away."

5. **"What about bias?"**
   > "We audited across sex and age groups. No significant disparities detected."
