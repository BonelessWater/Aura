# Aura Data Lake: Team Reference Guide

All data lives in Databricks Unity Catalog under `workspace.aura`. You can query it from any notebook, SQL warehouse, or the Databricks CLI.

**Warehouse ID:** `a3f84fea6e440a44` (Serverless Starter Warehouse)

---

## Quick Start

```sql
-- In any Databricks notebook or SQL editor:
SELECT * FROM workspace.aura.core_matrix LIMIT 10;
```

```python
# In a Databricks Python notebook:
df = spark.table("workspace.aura.core_matrix")
df.display()
```

```python
# From local Python (via parquet files in data/processed/):
import pandas as pd
cm = pd.read_parquet("data/processed/tier1/core_matrix.parquet")
```

---

## Architecture Overview

The data lake uses a three-tier architecture:

```
workspace.aura
  Tier 1 (Core)       -- One unified patient feature matrix
  Tier 2 (Extensions) -- Specialized panels joined via patient_id
  Tier 3 (Reference)  -- Lookup tables and baselines
```

| Tier | Table | Rows | Description |
|------|-------|------|-------------|
| 1 | `core_matrix` | 48,094 | Unified patient features (CBC, inflammatory markers, demographics, diagnoses) |
| 2 | `autoantibody_panel` | 12,085 | Autoantibody test results (ANA, anti-dsDNA, HLA-B27, etc.) |
| 2 | `longitudinal_labs` | 19,646 | Time-series lab results from ICU patients |
| 2 | `genetic_risk_scores` | 69,889 | GWAS significant hits from FinnGen R12 + HugeAmp |
| 3 | `healthy_baselines` | 110 | Age/sex-stratified reference ranges from healthy NHANES subjects |
| 3 | `icd_cluster_map` | 111 | ICD-10 to Aura disease cluster mapping |
| 3 | `drug_risk_index` | 597 | Drug molecular descriptors with autoimmunity risk labels |

---

## Tier 1: core_matrix

The main table. Every patient from every source gets one row here.

### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| `patient_id` | string | Unique identifier (format: `{source}_{id}`, NHANES uses SEQN-based IDs) |
| `source` | string | Data origin: `harvard`, `nhanes`, `mimic_demo` |
| `age` | double | Patient age in years |
| `sex` | string | `M` or `F` |
| `diagnosis_raw` | string | Original diagnosis text from the source dataset |
| `diagnosis_icd10` | string | Harmonized ICD-10 code (e.g., `M06.9` for RA) |
| `diagnosis_cluster` | string | Aura disease cluster (see below) |

### Lab Markers (all numeric, double)

| Column | Unit | Description |
|--------|------|-------------|
| `wbc` | 10^3/uL | White blood cell count |
| `rbc` | 10^6/uL | Red blood cell count |
| `hemoglobin` | g/dL | Hemoglobin |
| `hematocrit` | % | Hematocrit |
| `platelet_count` | 10^3/uL | Platelet count |
| `mcv` | fL | Mean corpuscular volume |
| `mch` | pg | Mean corpuscular hemoglobin |
| `rdw` | % | Red cell distribution width |
| `esr` | mm/hr | Erythrocyte sedimentation rate |
| `crp` | mg/L | C-reactive protein |
| `bmi` | kg/m^2 | Body mass index |
| `illness_duration` | months | Duration of autoimmune illness |
| `neutrophil_pct` | % | Neutrophil percentage |
| `lymphocyte_pct` | % | Lymphocyte percentage |

### Z-Score Columns

Every lab marker has a corresponding `{marker}_zscore` column (e.g., `wbc_zscore`, `crp_zscore`). These are IQR-based z-scores computed against age/sex-matched healthy baselines from NHANES. Use these for cross-source comparison.

### Missingness Flags

Every lab marker has a `{marker}_missing` column (0 or 1). A value of 1 means the original value was missing and was imputed. Use these as features in models -- missingness itself can be informative.

### Diagnosis Clusters

| Cluster | Description | Example Conditions |
|---------|-------------|-------------------|
| `healthy` | No autoimmune disease | NHANES healthy controls, Harvard controls |
| `systemic` | Systemic autoimmune | RA, SLE, Sjogren's, Reactive Arthritis |
| `gastrointestinal` | GI autoimmune/inflammatory | Crohn's, UC, Celiac, IBD |
| `neurological` | Neuro autoimmune | MS, Myasthenia Gravis, GBS |
| `dermatological` | Skin autoimmune | Psoriasis, Vitiligo, Pemphigus, Alopecia |
| `endocrine` | Endocrine autoimmune | Hashimoto's, Graves', Type 1 Diabetes |
| `haematological` | Blood/immune | ITP, Autoimmune Hemolytic Anemia |
| `renal` | Kidney autoimmune | Lupus Nephritis, IgA Nephropathy |
| `pulmonary` | Lung autoimmune | Sarcoidosis, Pulmonary Fibrosis |
| `ophthalmic` | Eye autoimmune | Uveitis, Scleritis |
| `other_autoimmune` | Other/rare | Mixed Connective Tissue Disease, etc. |

### Source Breakdown

| Source | Rows | Clusters | What It Provides |
|--------|------|----------|-----------------|
| `nhanes` | 35,909 | healthy (31,102), systemic (2,063), endocrine (1,943), gastrointestinal (801) | Population baseline CBC + demographics + MCQ-derived autoimmune diagnoses (US nationally representative) |
| `harvard` | 12,085 | systemic (10,481), healthy (1,604) | Autoantibody panels + CBC for rheumatic diseases |
| `mimic_demo` | 100 | (unlabeled) | ICU patient labs from MIMIC-IV demo |

---

## Tier 2: autoantibody_panel

Autoantibody and complement test results. Join to `core_matrix` on `patient_id`. Only available for the Harvard dataset (12,085 rows).

| Column | Type | Values | Description |
|--------|------|--------|-------------|
| `patient_id` | string | | Join key to core_matrix |
| `ana_status` | double | 0.0 / 1.0 | Antinuclear Antibody (Negative/Positive) |
| `anti_dsdna` | double | 0.0 / 1.0 | Anti-double-stranded DNA |
| `hla_b27` | double | 0.0 / 1.0 | HLA-B27 antigen |
| `anti_sm` | double | 0.0 / 1.0 | Anti-Smith antibody |
| `anti_ro` | double | 0.0 / 1.0 | Anti-Ro/SSA antibody |
| `anti_la` | double | 0.0 / 1.0 | Anti-La/SSB antibody |
| `rf_status` | double | 0.0 / 1.0 | Rheumatoid Factor |
| `anti_ccp` | double | 0.0 / 1.0 | Anti-CCP antibody |
| `c3` | double | mg/dL | Complement C3 level |
| `c4` | double | mg/dL | Complement C4 level |

```sql
-- Example: Get all SLE patients with positive ANA
SELECT cm.patient_id, cm.age, cm.sex, ab.ana_status, ab.anti_dsdna, ab.c3, ab.c4
FROM workspace.aura.core_matrix cm
JOIN workspace.aura.autoantibody_panel ab ON cm.patient_id = ab.patient_id
WHERE cm.diagnosis_cluster = 'systemic'
  AND ab.ana_status = 1.0;
```

---

## Tier 2: longitudinal_labs

Time-series lab results from MIMIC-IV Demo ICU patients (19,646 observations). Each row is one lab measurement at one point in time.

| Column | Type | Description |
|--------|------|-------------|
| `patient_id` | string | Join key |
| `event_timestamp` | string | When the lab was drawn |
| `lab_item` | string | Lab test name (wbc, rbc, hemoglobin, hematocrit, platelet_count, mcv, mch, rdw, esr, crp) |
| `lab_value` | double | Measured value |
| `lab_unit` | string | Unit of measurement |
| `source` | string | Always `mimic_demo` |

```sql
-- Example: Track WBC over time for a patient
SELECT patient_id, event_timestamp, lab_value
FROM workspace.aura.longitudinal_labs
WHERE patient_id = 'mimic_demo_1' AND lab_item = 'wbc'
ORDER BY event_timestamp;
```

---

## Tier 2: genetic_risk_scores

GWAS significant hits from FinnGen R12 and HugeAmp autoimmune association data (69,889 total variants). Each row is one variant associated with one autoimmune endpoint.

| Column | Type | Description |
|--------|------|-------------|
| `source` | string | `finngen_r12` or `hugeamp` |
| `variant_id` | string | rsID (e.g., `rs2258734`) or chr:pos identifier |
| `gene` | string | Nearest gene |
| `chrom` | string | Chromosome |
| `pos` | bigint | Genomic position |
| `ref` / `alt` | string | Reference and alternate alleles |
| `pvalue` | double | GWAS p-value |
| `beta` | double | Effect size |
| `se` | double | Standard error |
| `af` | double | Allele frequency |
| `finngen_endpoint` | string | FinnGen phenotype code (empty for HugeAmp) |
| `diagnosis_cluster` | string | Aura cluster mapping |
| `diagnosis_icd10` | string | ICD-10 code |

### Source Breakdown

| Source | Hits | Description |
|--------|------|-------------|
| `finngen_r12` | 67,869 | Genome-wide significant hits (p < 5e-8) from FinnGen R12 summary stats |
| `hugeamp` | 2,020 | Curated autoimmune GWAS associations from HugeAmp (Broad/UCSD) |

### FinnGen Endpoints

| Endpoint | Condition | Cluster | Hits |
|----------|-----------|---------|------|
| `M13_RHEUMA` | Rheumatoid Arthritis | rheumatological | 24,981 |
| `L12_PSORIASIS` | Psoriasis | dermatological | 21,622 |
| `K11_IBD_STRICT` | Inflammatory Bowel Disease | gastrointestinal | 10,595 |
| `SLE_FG` | Systemic Lupus Erythematosus | rheumatological | 9,509 |
| `E4_THYROIDITAUTOIM` | Autoimmune Thyroiditis | endocrine | 1,162 |

### HugeAmp Clusters

| Cluster | Hits | Conditions |
|---------|------|------------|
| gastrointestinal | 512 | Crohn's, UC, IBD, Celiac |
| rheumatological | 472 | RA, SLE |
| dermatological | 415 | Psoriasis, Vitiligo |
| endocrine | 396 | T1D, Graves', LADA, Addison's |
| neurological | 225 | Multiple Sclerosis |

```sql
-- Example: Top genes associated with RA
SELECT gene, COUNT(*) as variants, MIN(pvalue) as best_pvalue
FROM workspace.aura.genetic_risk_scores
WHERE finngen_endpoint = 'M13_RHEUMA'
GROUP BY gene
ORDER BY best_pvalue
LIMIT 20;
```

---

## Tier 3: healthy_baselines

Age/sex-stratified reference ranges for lab markers, computed from NHANES healthy subjects (CRP <= 10 mg/L filter applied). Use these to compute z-scores or flag abnormal values.

| Column | Type | Description |
|--------|------|-------------|
| `marker` | string | Lab marker name (wbc, rbc, hemoglobin, etc.) |
| `age_bucket` | string | `0-17`, `18-30`, `31-45`, `46-60`, `61+` |
| `sex` | string | `M` or `F` |
| `count` | bigint | Number of subjects in this stratum |
| `p5` - `p95` | double | 5th, 25th, 50th (median), 75th, 95th percentiles |

```sql
-- Example: Normal WBC range for males 31-45
SELECT * FROM workspace.aura.healthy_baselines
WHERE marker = 'wbc' AND age_bucket = '31-45' AND sex = 'M';
```

---

## Tier 3: icd_cluster_map

Lookup table mapping ICD-10 codes to Aura disease clusters (111 rows).

| Column | Type | Description |
|--------|------|-------------|
| `icd10_code` | string | ICD-10 code |
| `icd10_description` | string | Human-readable name |
| `aura_cluster` | string | Aura cluster assignment |

---

## Tier 3: drug_risk_index

Molecular descriptors for 597 drugs with autoimmunity risk labels. From the UCI Drug-Induced Autoimmunity Prediction dataset.

| Column | Type | Description |
|--------|------|-------------|
| `Label` | bigint | 0 = no autoimmunity risk, 1 = autoimmunity risk |
| `SMILES` | string | Drug molecular structure (SMILES notation) |
| `split` | string | `train` or `test` (original dataset split) |
| *(195 columns)* | double/bigint | Physicochemical descriptors (MolWt, MolLogP, TPSA, HBond donors/acceptors, ring counts, fragment counts, etc.) |

---

## Common Query Patterns

### 1. Compare autoimmune vs healthy CBC

```sql
SELECT
  diagnosis_cluster,
  AVG(wbc) as avg_wbc,
  AVG(crp) as avg_crp,
  AVG(esr) as avg_esr,
  AVG(hemoglobin) as avg_hgb,
  COUNT(*) as n
FROM workspace.aura.core_matrix
WHERE diagnosis_cluster IN ('healthy', 'systemic', 'gastrointestinal')
GROUP BY diagnosis_cluster;
```

### 2. Find patients with abnormal z-scores

```sql
-- Patients with WBC or CRP z-scores > 2 (potential autoimmune flare)
SELECT patient_id, source, diagnosis_cluster,
       wbc, wbc_zscore, crp, crp_zscore
FROM workspace.aura.core_matrix
WHERE ABS(wbc_zscore) > 2 OR ABS(crp_zscore) > 2
ORDER BY ABS(crp_zscore) DESC
LIMIT 100;
```

### 3. Build a training dataset for classification

```sql
-- Binary classification: autoimmune vs healthy
SELECT
  wbc, rbc, hemoglobin, hematocrit, platelet_count,
  mcv, mch, rdw, esr, crp, age, sex, bmi,
  wbc_zscore, crp_zscore, hemoglobin_zscore,
  esr_missing, crp_missing, wbc_missing,
  CASE WHEN diagnosis_cluster = 'healthy' THEN 0 ELSE 1 END AS label
FROM workspace.aura.core_matrix
WHERE diagnosis_cluster IS NOT NULL;
```

### 4. Multi-class cluster prediction

```sql
-- Predict which autoimmune cluster
SELECT
  wbc, rbc, hemoglobin, platelet_count, esr, crp,
  wbc_zscore, crp_zscore, hemoglobin_zscore,
  diagnosis_cluster AS label
FROM workspace.aura.core_matrix
WHERE diagnosis_cluster IS NOT NULL
  AND diagnosis_cluster != 'healthy';
```

### 5. Enrich with autoantibody data

```sql
SELECT
  cm.diagnosis_cluster,
  AVG(ab.ana_status) as pct_ana_positive,
  AVG(ab.anti_dsdna) as pct_anti_dsdna_positive,
  AVG(ab.c3) as avg_c3,
  COUNT(*) as n
FROM workspace.aura.core_matrix cm
JOIN workspace.aura.autoantibody_panel ab ON cm.patient_id = ab.patient_id
GROUP BY cm.diagnosis_cluster;
```

### 6. Genetic loci for a specific condition

```sql
-- Top genes for IBD with strongest effect sizes
SELECT gene, variant_id, pvalue, beta, af
FROM workspace.aura.genetic_risk_scores
WHERE finngen_endpoint = 'K11_IBD_STRICT'
ORDER BY ABS(beta) DESC
LIMIT 50;
```

---

## File Locations

### Databricks Volume
```
/Volumes/workspace/aura/aura_data/
  tier1_core_matrix.parquet
  tier2_autoantibody_panel.parquet
  tier2_gi_markers.parquet
  tier2_longitudinal_labs.parquet
  tier2_genetic_risk_scores.parquet
  tier3_healthy_baselines.parquet
  tier3_icd_cluster_map.parquet
  tier3_drug_risk_index.parquet
  raw/
    nhanes/           -- NHANES SAS transport files (CBC, DEMO, HSCRP, MCQ)
    finngen/          -- FinnGen R12 summary stats (.gz)
    gwas/             -- HugeAmp GWAS associations
    (+ 20 additional raw source directories staged for future wrangling)
```

### Local Repository
```
data/
  raw/                -- Raw downloaded files
  processed/
    tier1/core_matrix.parquet
    tier2/autoantibody_panel.parquet
    tier2/longitudinal_labs.parquet
    tier3/healthy_baselines.parquet
    tier3/icd_cluster_map.parquet
    tier3/drug_risk_index.parquet
```

---

## Data Provenance

| Source | License | Rows | How Obtained |
|--------|---------|------|-------------|
| Harvard Dataverse (DOI: 10.7910/DVN/VM4OR3) | CC BY | 12,085 | Direct download via API |
| NHANES 2011-2018 (CDC) | Public Domain | 35,909 | Direct download (.XPT) -- CBC, DEMO, HSCRP, MCQ files |
| MIMIC-IV Demo (PhysioNet) | PhysioNet Credentialed | 100 | Direct download |
| UCI Drug Autoimmunity (ID: 1104) | Open Access | 597 | Direct download / ucimlrepo |
| FinnGen R12 (University of Helsinki) | FinnGen DUA | 67,869 hits | Google Cloud Storage |
| HugeAmp (Broad/UCSD) | Open Access | 2,020 hits | GraphQL API (autoimmune phenotypes) |

---

## Important Notes

- **Z-scores** are IQR-based (not standard deviation), making them robust to outliers
- **Missingness flags** (`{col}_missing = 1`) indicate imputed values -- always include these as features
- **Units are harmonized**: WBC is always 10^3/uL, hemoglobin is g/dL, platelets are 10^3/uL
- **NHANES autoimmune labels** are derived from MCQ (Medical Conditions Questionnaire) self-reported diagnoses, not clinical confirmation. MCQ fields used: MCQ160A/MCQ195 (arthritis type), MCQ160N (lupus), MCQ160M (thyroid), MCQ160K (celiac)
- **MIMIC data** has only 100 rows (demo subset) -- primarily useful for longitudinal patterns, not statistical power
- **genetic_risk_scores** contains raw GWAS hits from two sources (FinnGen + HugeAmp), not polygenic risk scores -- you would need to compute PRS separately
