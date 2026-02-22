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
| 1 | `patient_reported_outcomes` | 5,025,070 | Daily symptom/treatment/trigger tracking from Flaredown (~1,700 patients) |
| 1 | `pmc_patients` | 250,294 | Clinical case reports from PubMed Central (210K papers, 1986-2024) |
| 2 | `autoantibody_panel` | 12,085 | Autoantibody test results (ANA, anti-dsDNA, HLA-B27, etc.) |
| 2 | `longitudinal_labs` | 19,646 | Time-series lab results from ICU patients |
| 2 | `genetic_risk_scores` | 69,889 | GWAS significant hits from FinnGen R12 + HugeAmp |
| 2 | `gwas_catalog_associations` | 5,617 | NHGRI-EBI curated autoimmune GWAS hits |
| 2 | `hla_frequencies` | 11 | AFND HLA allele-disease associations |
| 2 | `pan_ukbb_sumstats` | 17,212 | Pan-ancestry GWAS summary statistics (T1D) |
| 2 | `immunobase_credible_sets` | 1,388 | Fine-mapped autoimmune GWAS loci |
| 2 | `transcriptomics_signatures` | 667,733 | Gene expression signatures (ADEx + IAAA) |
| 2 | `microbiome_profiles` | 5,544 | Gut microbiome taxonomic profiles (HMP IBDMDB) |
| 3 | `healthy_baselines` | 110 | Age/sex-stratified reference ranges from healthy NHANES subjects |
| 3 | `icd_cluster_map` | 111 | ICD-10 to Aura disease cluster mapping |
| 3 | `drug_risk_index` | 597 | Drug molecular descriptors with autoimmunity risk labels |
| 3 | `open_targets_associations` | 52,471 | Drug-target-disease evidence scores from Open Targets |
| 3 | `ctd_chemical_disease` | 194,096 | Chemical-disease interactions (autoimmune filtered) from CTD |
| 3 | `epa_air_quality_reference` | 25,722 | County-level annual pollutant concentrations (PM2.5, Ozone, NO2, SO2, PM10) |
| 3 | `hpa_protein_expression` | 20,162 | Protein expression atlas with disease involvement (HPA v25) |
| 3 | `mendeley_lipidomics` | 1,612 | Mouse EAE lipidomics model data (MS validation) |

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

## Tier 1: patient_reported_outcomes

Daily symptom, treatment, and trigger tracking from the Flaredown app (5M+ rows, ~1,700 patients). Each row is one trackable entry per patient per day. Not joinable to `core_matrix` by `patient_id` (different patient populations), but joinable by `diagnosis_cluster` for disease-level aggregation.

| Column | Type | Description |
|--------|------|-------------|
| `patient_id` | string | Unique identifier (`flaredown_{user_id}`) |
| `source` | string | Always `flaredown` |
| `date` | timestamp | Check-in date |
| `condition` | string | Patient's primary autoimmune condition |
| `diagnosis_cluster` | string | Aura cluster mapping |
| `symptom` | string | Symptom name (null for treatment/trigger rows) |
| `symptom_severity` | bigint | 0-4 severity scale (null for non-symptom rows) |
| `treatment` | string | Treatment/medication name (null for symptom/trigger rows) |
| `treatment_dose` | string | Dose information |
| `trigger` | string | Food/environmental trigger (null for symptom/treatment rows) |
| `country` | string | Patient country |
| `age` | double | Patient age |
| `sex` | string | Patient sex |

```sql
-- Top symptoms by cluster
SELECT diagnosis_cluster, symptom, COUNT(*) as reports, AVG(symptom_severity) as avg_severity
FROM workspace.aura.patient_reported_outcomes
WHERE symptom IS NOT NULL
GROUP BY diagnosis_cluster, symptom
ORDER BY reports DESC
LIMIT 20;
```

---

## Tier 1: pmc_patients

Clinical case reports from PubMed Central (250,294 patient summaries from 210K papers). Full physician-written clinical narratives with demographics. Not joinable to `core_matrix` by `patient_id` (different patient populations).

| Column | Type | Description |
|--------|------|-------------|
| `patient_id` | string | Unique patient identifier from PMC-Patients |
| `patient_uid` | string | Unique patient UID |
| `pmid` | string | PubMed ID of the source paper |
| `title` | string | Paper title |
| `patient_summary` | string | Full clinical narrative (avg ~2,800 chars) |
| `age_years` | double | Patient age in years (0-120, null if unknown) |
| `sex` | string | `male`, `female` (130K/119K) |
| `pub_date` | timestamp | Publication date (1986-2024) |

```sql
-- Search for autoimmune case reports
SELECT patient_id, title, age_years, sex, pub_date
FROM workspace.aura.pmc_patients
WHERE LOWER(patient_summary) LIKE '%rheumatoid arthritis%'
LIMIT 20;
```

---

## Tier 2: gwas_catalog_associations

NHGRI-EBI GWAS Catalog entries filtered to autoimmune traits (5,617 rows). Curated associations with trait-level p-values and odds ratios.

| Column | Type | Description |
|--------|------|-------------|
| `efo_id` | string | Experimental Factor Ontology ID (e.g., `MONDO_0007915`) |
| `trait` | string | Disease/trait name |
| `pvalue` | double | GWAS p-value |
| `pvalue_mlog` | bigint | -log10(p-value) |
| `risk_allele_frequency` | string | Risk allele frequency |
| `or_beta` | double | Odds ratio or beta coefficient |
| `ci_95` | string | 95% confidence interval |
| `diagnosis_cluster` | string | Aura cluster |
| `diagnosis_icd10` | string | ICD-10 code |
| `source` | string | Always `gwas_catalog` |

---

## Tier 2: hla_frequencies

Allele Frequency Net Database (AFND) HLA allele-disease associations (11 rows). Links HLA alleles to autoimmune disease susceptibility across populations.

| Column | Type | Description |
|--------|------|-------------|
| `allele` | string | HLA allele name |
| `associated_diseases` | string | Disease associations |
| `locus` | string | HLA locus (e.g., A, B, DRB1) |
| `hla_locus` | string | Same as locus |
| `n_populations` | bigint | Number of populations studied |
| `frequencies_found` | boolean | Whether frequency data is available |
| `diagnosis_cluster` | string | Aura cluster |
| `diagnosis_icd10` | string | ICD-10 code |
| `source` | string | Always `afnd` |

---

## Tier 2: pan_ukbb_sumstats

Pan-ancestry UK Biobank GWAS summary statistics for Type 1 Diabetes (17,212 genome-wide significant variants). Includes meta-analysis and ancestry-specific results (AFR, CSA, EUR).

| Column | Type | Description |
|--------|------|-------------|
| `chr` | bigint | Chromosome |
| `pos` | bigint | Genomic position |
| `ref` / `alt` | string | Reference and alternate alleles |
| `beta_meta` | double | Meta-analysis effect size |
| `se_meta` | double | Meta-analysis standard error |
| `neglog10_pval_meta` | double | -log10(p-value) from meta-analysis |
| `af_cases_meta` | double | Allele frequency in cases |
| `af_controls_meta` | double | Allele frequency in controls |
| `beta_AFR` / `beta_CSA` / `beta_EUR` | double | Ancestry-specific betas |
| `neglog10_pval_AFR` / `_CSA` / `_EUR` | double | Ancestry-specific -log10 p-values |
| `phenotype_code` | string | ICD-10 phenotype code (e.g., `E10`) |
| `sex_group` | string | Sex stratification |
| `diagnosis_cluster` | string | Aura cluster |
| `source` | string | Always `pan_ukbb` |

```sql
-- Top Pan-UKBB variants for T1D by significance
SELECT chr, pos, ref, alt, neglog10_pval_meta, beta_meta, af_cases_meta
FROM workspace.aura.pan_ukbb_sumstats
ORDER BY neglog10_pval_meta DESC
LIMIT 20;
```

---

## Tier 2: immunobase_credible_sets

ImmunoBase/GWAS Catalog study metadata filtered to autoimmune diseases (1,388 studies). Contains publication-level data linking GWAS studies to autoimmune traits.

| Column | Type | Description |
|--------|------|-------------|
| `pubmedid` | bigint | PubMed ID |
| `first_author` | string | First author |
| `date` | string | Publication date |
| `journal` | string | Journal name |
| `study` | string | Study title |
| `disease_trait` | string | Disease/trait studied |
| `initial_sample_size` | string | Discovery sample size |
| `replication_sample_size` | string | Replication sample size |
| `association_count` | bigint | Number of associations reported |
| `diagnosis_cluster` | string | Aura cluster |
| `diagnosis_icd10` | string | ICD-10 code |
| `source` | string | Always `immunobase` |

---

## Tier 2: transcriptomics_signatures

Gene expression signatures from autoimmune disease studies (667,733 rows). Aggregated from ADEx (Autoimmune Disease Explorer) and IAAA (Immune Atlas of Autoimmune Arthritis) GEO datasets.

| Column | Type | Description |
|--------|------|-------------|
| `gene_symbol` | string | Gene symbol |
| `mean_expression` | double | Mean expression value |
| `std_expression` | double | Standard deviation |
| `median_expression` | double | Median expression |
| `source` | string | `adex` or `iaaa` |
| `study_id` | string | GEO series ID (e.g., `GSE55235`) |
| `disease` | string | Disease label |
| `diagnosis_cluster` | string | Aura cluster |
| `sample_type` | string | Tissue type |
| `platform` | string | Microarray platform |
| `n_samples` | bigint | Number of samples |

```sql
-- Find differentially expressed genes across autoimmune diseases
SELECT gene_symbol, diagnosis_cluster, AVG(mean_expression) as avg_expr, COUNT(DISTINCT study_id) as n_studies
FROM workspace.aura.transcriptomics_signatures
GROUP BY gene_symbol, diagnosis_cluster
HAVING COUNT(DISTINCT study_id) > 1
ORDER BY avg_expr DESC
LIMIT 50;
```

---

## Tier 2: microbiome_profiles

Gut microbiome taxonomic profiles from HMP IBDMDB (5,544 rows). Species-level relative abundances from IBD and non-IBD subjects.

| Column | Type | Description |
|--------|------|-------------|
| `source` | string | Always `hmp_ibdmdb` |
| `sample_id` | string | Sample identifier |
| `body_site` | string | Sampling site (e.g., stool) |
| `diagnosis` | string | Subject diagnosis (CD, UC, nonIBD) |
| `diagnosis_cluster` | string | Aura cluster |
| `taxon_level` | string | Taxonomic rank (species) |
| `taxon_name` | string | Species name |
| `relative_abundance` | double | Relative abundance (0-1) |
| `sequencing_method` | string | Sequencing technology |

```sql
-- Top microbial species in IBD vs controls
SELECT taxon_name, diagnosis, AVG(relative_abundance) as avg_abundance
FROM workspace.aura.microbiome_profiles
WHERE diagnosis IN ('CD', 'UC', 'nonIBD')
GROUP BY taxon_name, diagnosis
HAVING AVG(relative_abundance) > 0.01
ORDER BY avg_abundance DESC;
```

---

## Tier 3: open_targets_associations

Drug-target-disease evidence from Open Targets Platform (52,471 rows). Multi-source evidence scores linking drug targets to autoimmune diseases.

| Column | Type | Description |
|--------|------|-------------|
| `disease_id` | string | Disease ontology ID |
| `disease_name` | string | Disease name |
| `target_id` | string | Ensembl gene ID |
| `target_symbol` | string | Gene symbol |
| `target_name` | string | Full gene/protein name |
| `overall_score` | double | Aggregate evidence score (0-1) |
| `literature` | double | Literature mining evidence |
| `animal_model` | double | Animal model evidence |
| `genetic_association` | double | Genetic association evidence |
| `known_drug` | double | Known drug evidence |
| `rna_expression` | double | RNA expression evidence |
| `affected_pathway` | double | Pathway analysis evidence |
| `diagnosis_cluster` | string | Aura cluster |
| `source` | string | Always `open_targets` |

```sql
-- Top drug targets for systemic autoimmune diseases
SELECT target_symbol, target_name, disease_name, overall_score, known_drug, genetic_association
FROM workspace.aura.open_targets_associations
WHERE diagnosis_cluster = 'systemic' AND overall_score > 0.5
ORDER BY overall_score DESC
LIMIT 30;
```

---

## Tier 3: ctd_chemical_disease

Chemical-disease interactions from the Comparative Toxicogenomics Database (194,096 rows). Filtered to autoimmune-related diseases. Links environmental chemicals to disease mechanisms.

| Column | Type | Description |
|--------|------|-------------|
| `chemical_name` | string | Chemical name |
| `chemical_id` | string | MeSH ID |
| `cas_rn` | string | CAS Registry Number |
| `disease_name` | string | Disease name |
| `disease_id` | string | MeSH Disease ID |
| `direct_evidence` | string | Evidence type (e.g., `marker/mechanism`) |
| `inference_gene_symbol` | string | Gene mediating the interaction |
| `inference_score` | double | Interaction strength score |
| `omim_ids` | string | OMIM IDs |
| `pubmed_ids` | string | Supporting PubMed IDs |
| `diagnosis_cluster` | string | Aura cluster |
| `source` | string | Always `ctd` |

```sql
-- Top chemicals associated with autoimmune diseases
SELECT chemical_name, disease_name, inference_gene_symbol, inference_score
FROM workspace.aura.ctd_chemical_disease
WHERE direct_evidence IS NOT NULL
ORDER BY inference_score DESC
LIMIT 20;
```

---

## Tier 3: epa_air_quality_reference

County-level annual pollutant concentrations from EPA AQS (25,722 rows). Covers PM2.5, PM10, Ozone, NO2, and SO2 across US counties and years.

| Column | Type | Description |
|--------|------|-------------|
| `year` | string | Monitoring year |
| `state_code` | bigint | FIPS state code |
| `county_code` | bigint | FIPS county code |
| `state_name` | string | State name |
| `county_name` | string | County name |
| `latitude` | double | Monitor latitude |
| `longitude` | double | Monitor longitude |
| `parameter` | string | Pollutant name (PM2.5, Ozone, NO2, SO2, PM10) |
| `arithmetic_mean` | double | Annual mean concentration |
| `first_max_value` | double | Annual maximum |
| `units_of_measure` | string | Measurement units |
| `observation_count` | bigint | Number of observations |
| `source` | string | Always `epa_aqs` |

```sql
-- Average PM2.5 by state
SELECT state_name, year, AVG(arithmetic_mean) as avg_pm25
FROM workspace.aura.epa_air_quality_reference
WHERE parameter = 'PM2.5'
GROUP BY state_name, year
ORDER BY avg_pm25 DESC;
```

---

## Tier 3: hpa_protein_expression

Human Protein Atlas v25 protein expression data filtered to autoimmune-relevant genes (20,162 rows). Includes blood expression, disease involvement, and reliability annotations.

| Column | Type | Description |
|--------|------|-------------|
| `gene` | string | Gene name |
| `ensembl` | string | Ensembl gene ID |
| `uniprot` | string | UniProt ID |
| `protein_class` | string | Protein classification |
| `disease_involvement` | string | Associated diseases |
| `blood_expression_cluster` | string | Blood expression pattern |
| `rna_blood_cell_specificity` | string | Cell-type specificity |
| `rna_blood_cell_specificity_score` | double | Specificity score |
| `blood_concentration_conc_blood_im_pg_l` | double | Blood concentration (immunoassay) |
| `blood_concentration_conc_blood_ms_pg_l` | double | Blood concentration (mass spec) |
| `reliability_ih` | string | Immunohistochemistry reliability |
| `chromosome` | string | Chromosome |
| `diagnosis_cluster` | string | Aura cluster |
| `source` | string | Always `hpa_v25` |

---

## Tier 3: mendeley_lipidomics

Mouse EAE (experimental autoimmune encephalomyelitis) lipidomics data (1,612 rows). Long-format lipid concentrations for EAE model vs control mice. EAE is the standard animal model for Multiple Sclerosis.

| Column | Type | Description |
|--------|------|-------------|
| `ID` | bigint | Sample ID |
| `DRUG` | bigint | Drug treatment (0/1) |
| `EAE` | bigint | EAE induction (0=control, 1=EAE model) |
| `GROUP` | bigint | Experimental group (1-4) |
| `condition` | string | `control` or `eae_model` |
| `diagnosis_cluster` | string | `healthy` or `neurological` |
| `analyte_name` | string | Lipid species name |
| `value` | double | Lipid concentration |
| `analyte_type` | string | Always `lipid` |
| `source` | string | Always `mendeley` |

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

### 7. Symptom-treatment patterns from patient reports

```sql
-- Most common treatments per cluster and their co-reported symptoms
SELECT pro.diagnosis_cluster, pro.treatment, COUNT(*) as uses,
       COUNT(DISTINCT pro.patient_id) as patients
FROM workspace.aura.patient_reported_outcomes pro
WHERE pro.treatment IS NOT NULL
GROUP BY pro.diagnosis_cluster, pro.treatment
ORDER BY uses DESC
LIMIT 30;
```

### 8. Cross-reference drug targets with chemical exposures

```sql
-- Genes that appear in both Open Targets drug targets and CTD chemical interactions
SELECT DISTINCT ot.target_symbol, ot.disease_name, ctd.chemical_name, ctd.inference_score
FROM workspace.aura.open_targets_associations ot
JOIN workspace.aura.ctd_chemical_disease ctd ON ot.target_symbol = ctd.inference_gene_symbol
WHERE ot.overall_score > 0.5 AND ctd.inference_score > 10
ORDER BY ot.overall_score DESC
LIMIT 30;
```

### 9. Microbiome dysbiosis in IBD

```sql
-- Species enriched in Crohn's vs healthy controls
SELECT m1.taxon_name,
       AVG(CASE WHEN m1.diagnosis = 'CD' THEN m1.relative_abundance END) as cd_abundance,
       AVG(CASE WHEN m1.diagnosis = 'nonIBD' THEN m1.relative_abundance END) as control_abundance
FROM workspace.aura.microbiome_profiles m1
GROUP BY m1.taxon_name
HAVING cd_abundance IS NOT NULL AND control_abundance IS NOT NULL
ORDER BY (cd_abundance - control_abundance) DESC
LIMIT 20;
```

---

## File Locations

### Databricks Volume
```
/Volumes/workspace/aura/aura_data/
  tier1_core_matrix.parquet
  tier1_patient_reported_outcomes.parquet
  tier1_pmc_patients.parquet
  tier2_autoantibody_panel.parquet
  tier2_longitudinal_labs.parquet
  tier2_genetic_risk_scores.parquet
  tier2_gwas_catalog_associations.parquet
  tier2_hla_frequencies.parquet
  tier2_pan_ukbb_sumstats.parquet
  tier2_immunobase_credible_sets.parquet
  tier2_transcriptomics_signatures.parquet
  tier2_microbiome_profiles.parquet
  tier3_healthy_baselines.parquet
  tier3_icd_cluster_map.parquet
  tier3_drug_risk_index.parquet
  tier3_open_targets_associations.parquet
  tier3_ctd_chemical_disease.parquet
  tier3_epa_air_quality_reference.parquet
  tier3_hpa_protein_expression.parquet
  tier3_mendeley_lipidomics.parquet
  raw/
    nhanes/           -- NHANES SAS transport files (CBC, DEMO, HSCRP, MCQ)
    finngen/          -- FinnGen R12 summary stats (.gz)
    gwas/             -- HugeAmp GWAS associations
    gwas_catalog/     -- NHGRI-EBI GWAS Catalog (parquet)
    afnd/             -- Allele Frequency Net Database (parquet)
    pan_ukbb/         -- Pan-UK Biobank (bgzipped TSV)
    immunobase/       -- ImmunoBase GWAS studies (TSV)
    adex/             -- ADEx GEO series matrix files
    iaaa/             -- IAAA GEO series matrix file
    hmp/              -- HMP IBDMDB microbiome profiles
    olink/            -- Olink proteomics (xlsx)
    hmdb/             -- HMDB metabolomics (CSV)
    metabolights/     -- MetaboLights (parquet)
    open_targets/     -- Open Targets associations (parquet)
    ctd/              -- CTD chemicals-diseases (TSV.gz)
    epa_aqs/          -- EPA annual monitoring data (CSV/zip)
    hpa/              -- Human Protein Atlas (TSV)
    mendeley/         -- Mendeley mouse lipidomics (CSV)
    flaredown/        -- Flaredown patient export (CSV)
    pmc_patients/     -- PMC-Patients v2 (parquet from HuggingFace)
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
| NHGRI-EBI GWAS Catalog | Open Access | 5,617 | Pre-filtered parquet |
| AFND (Allele Frequency Net Database) | Open Access | 11 | Pre-filtered parquet |
| Pan-UK Biobank (Neale Lab) | Open Access | 17,212 | Bgzipped TSV (T1D phenotype) |
| ImmunoBase / GWAS Catalog | Open Access | 1,388 | TSV download |
| ADEx (Autoimmune Disease Explorer) | GEO Open | 667,733 | GEO series matrix files |
| IAAA (Immune Atlas Autoimmune Arthritis) | GEO Open | (merged above) | GEO series matrix file |
| HMP IBDMDB (NIH) | dbGaP Open | 5,544 | Taxonomic profiles TSV |
| Open Targets Platform | Open Access | 52,471 | Pre-filtered parquet |
| CTD (Comparative Toxicogenomics DB) | Open Access | 194,096 | TSV.gz (autoimmune filtered from 9.65M) |
| EPA AQS (Air Quality System) | Public Domain | 25,722 | Annual CSV downloads (2000-2023) |
| Human Protein Atlas v25 | CC BY-SA | 20,162 | TSV download (autoimmune filtered from 20K genes) |
| Mendeley Data (mouse lipidomics) | CC BY-NC-SA | 1,612 | CSV download (EAE model) |
| Flaredown (patient tracker) | Open Data | 5,025,070 | CSV export |
| PMC-Patients v2 (HuggingFace) | CC BY-NC-SA | 250,294 | Parquet download via Azure VM |

---

## Important Notes

- **Z-scores** are IQR-based (not standard deviation), making them robust to outliers
- **Missingness flags** (`{col}_missing = 1`) indicate imputed values -- always include these as features
- **Units are harmonized**: WBC is always 10^3/uL, hemoglobin is g/dL, platelets are 10^3/uL
- **NHANES autoimmune labels** are derived from MCQ (Medical Conditions Questionnaire) self-reported diagnoses, not clinical confirmation. MCQ fields used: MCQ160A/MCQ195 (arthritis type), MCQ160N (lupus), MCQ160M (thyroid), MCQ160K (celiac)
- **MIMIC data** has only 100 rows (demo subset) -- primarily useful for longitudinal patterns, not statistical power
- **genetic_risk_scores** contains raw GWAS hits from two sources (FinnGen + HugeAmp), not polygenic risk scores -- you would need to compute PRS separately
