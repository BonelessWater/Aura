# Aura: Data Wrangling & Harmonization Plan

The challenge: 24 datasets across 8 modalities (clinical labs, autoantibodies, genetics, transcriptomics, single-cell, microbiome, proteomics, metabolomics, patient-reported outcomes, and environmental exposures)--all with wildly different schemas, granularities, and clinical vocabularies. We can't afford to throw away features that only exist in one source. This document lays out the architecture for turning that chaos into a single, queryable data lake that preserves every unique signal.

**Status:** Phase 1 (core clinical + genetics + NHANES MCQ reclassification) is IMPLEMENTED and registered in Databricks Unity Catalog (`workspace.aura`). Phase 2 (omics + environmental + patient-reported) is specified below and ready for implementation.

---

## 0. Idempotency Rule: Do Not Rewrangle Completed Data

**Any table that is already properly wrangled, validated, and registered in Databricks Unity Catalog MUST NOT be rewrangled.** This is a hard rule, not a suggestion.

### What "properly wrangled" means
A table is considered properly wrangled if ALL of the following are true:
1. The parquet file exists on the Databricks Volume (`/Volumes/workspace/aura/aura_data/`).
2. The table is registered in Unity Catalog (`workspace.aura.*`) and queryable via SQL.
3. The schema matches the spec in this document (correct column names, types, and units).
4. Row counts are consistent with the source data (no unexplained data loss).
5. The `dataget.md` team reference guide documents it as current.

### Currently locked tables (do not rewrangle)

| Table | Rows | Last Wrangled | Notes |
|:---|:---|:---|:---|
| `core_matrix` | 48,094 | 2026-02-21 | Harvard + NHANES (with MCQ reclassification) + MIMIC Demo |
| `autoantibody_panel` | 12,085 | 2026-02-21 | Harvard only |
| `longitudinal_labs` | 19,646 | 2026-02-21 | MIMIC Demo |
| `genetic_risk_scores` | 69,889 | 2026-02-21 | FinnGen R12 + HugeAmp |
| `healthy_baselines` | 110 | 2026-02-21 | NHANES healthy controls |
| `icd_cluster_map` | 111 | 2026-02-21 | ICD-10 to Aura cluster mapping |
| `drug_risk_index` | 597 | 2026-02-21 | UCI drug dataset |

### When rewrangling IS allowed
- **Schema change:** The spec in this document is updated to add/remove/rename columns.
- **Data correction:** A bug is discovered in the wrangling logic (e.g., wrong unit conversion, incorrect ICD-10 mapping).
- **Source update:** The upstream dataset releases a new version with corrections.
- **Explicit request:** A team member explicitly requests a rewrangle with documented justification.

In all cases, document the reason in the git commit message and update `dataget.md` with the new row counts.

### How to enforce in code
Every wrangling script MUST check for existing output before processing:
```python
import os

output_path = "data/processed/tier2/some_table.parquet"
if os.path.exists(output_path):
    logging.info("SKIP: %s already exists. Delete manually to force rewrangle.", output_path)
    return
```

For Databricks notebooks, check the Unity Catalog:
```python
try:
    existing = spark.table("workspace.aura.some_table")
    row_count = existing.count()
    logging.info("SKIP: workspace.aura.some_table already exists (%d rows).", row_count)
    dbutils.notebook.exit("SKIPPED - table already exists")
except Exception:
    pass  # Table does not exist, proceed with wrangling
```

---

## 1. The Full Dataset Inventory

### 1.1 Already Wrangled & Registered (7 tables, 3 sources in core_matrix)

| Dataset | Grain | Rows in Core Matrix | Tier 2 Extension | Status |
|:---|:---|:---|:---|:---|
| Harvard Dataverse | 1 row = 1 patient snapshot | 12,085 | autoantibody_panel (11 cols) | Implemented |
| NHANES (CBC + DEMO + HSCRP + MCQ) | 1 row = 1 survey participant | 35,909 | -- | Implemented (MCQ reclassification done) |
| MIMIC-IV Demo | 1 row = 1 ICU patient | 100 | longitudinal_labs (19,646 obs) | Implemented |
| FinnGen R12 | 1 row = 1 variant/phenotype | -- | genetic_risk_scores (67,869 rows) | Implemented |
| HugeAmp BioIndex | 1 row = 1 variant/phenotype | -- | genetic_risk_scores (2,020 rows) | Implemented |
| UCI Drug | 1 row = 1 drug compound | -- | -- (Tier 3: drug_risk_index, 597 rows) | Implemented |

**Core matrix total: 48,094 rows x 44 columns** across 3 patient-level sources (Harvard, NHANES, MIMIC Demo). NHANES includes MCQ-derived autoimmune diagnoses: healthy (31,102), systemic (2,063), endocrine (1,943), gastrointestinal (801).

### 1.2 Local Raw Data NOT Yet Wrangled

| Dataset | Rows | Key Value | Wrangling Needed |
|:---|:---|:---|:---|
| MIMIC-IV Demo (full tables) | 100 patients, 35 CSVs | Prescriptions, microbiology, procedures, chart events | Extract additional Tier 2 tables |

### 1.3 On Databricks Volume raw/ -- NOT Yet Wrangled (16 datasets)

| Dataset | Files | Raw Size | Target Tier | Priority |
|:---|:---|:---|:---|:---|
| Flaredown | 1 CSV | ~50 MB | Tier 1 (patient-reported) | High |
| ADEx | 5 GEO matrices | ~200 MB | Tier 2 (transcriptomics) | Medium |
| IAAA | 1 GEO matrix | ~100 MB | Tier 2 (transcriptomics) | Medium |
| GWAS Catalog | 1 parquet | ~150 MB | Tier 2 (extend genetic_risk_scores) | High |
| Pan-UK Biobank | 1 TSV.bgz | ~500 MB | Tier 2 (GWAS summary stats) | Medium |
| ImmunoBase | 2 files | ~50 MB | Tier 2 (fine-mapping credible sets) | Medium |
| AFND | 1 parquet | ~10 MB | Tier 2 (HLA frequencies) | High |
| HMP | 2 CSVs | ~100 MB | Tier 2 (microbiome) | Medium |
| HMDB | 1 CSV | ~50 MB | Tier 2 (metabolomics) | Medium |
| Olink/UKB-PPP | 1 xlsx | ~20 MB | Tier 2 (proteomics) | Medium |
| MetaboLights | 1 parquet | ~5 MB | Tier 2 (metabolomics index) | Low |
| CTD | 6 TSVs | ~500 MB | Tier 3 (chemical-disease reference) | High |
| EPA AQS | 22 files | ~200 MB | Tier 3 (environmental exposure) | Medium |
| HPA | 2 files | ~100 MB | Tier 3 (protein expression reference) | Medium |
| Open Targets | 1 parquet | ~50 MB | Tier 3 (drug-target reference) | High |
| Mendeley | 3 CSVs | ~5 MB | Tier 3 (lipidomics validation) | Low |

### 1.4 Pending Access

| Dataset | Status | Notes |
|:---|:---|:---|
| ImmPort 10KIP | DUA accepted 2026-02-21 | Download pending (Azure VM required) |
| HCA eQTL (Human Cell Atlas) | Not downloaded | 1.2M PBMCs, large H5AD files |
| Allen Immune Health Atlas | Not downloaded | 16M+ single cells, very large |

---

## 2. Architecture: The Expanded Data Lake

```
+---------------------------------------------------------------+
|                      TIER 1: CORE MATRICES                     |
|   Unified patient-level feature tables for model training      |
|   +-------------------------+ +-----------------------------+  |
|   | core_matrix             | | patient_reported_outcomes   |  |
|   | 48,094 rows x 44 cols  | | (Flaredown)                |  |
|   | Harvard + NHANES +      | | ~1,700 patients x daily    |  |
|   | MIMIC Demo              | | symptom/treatment tracking |  |
|   +-------------------------+ +-----------------------------+  |
+----------------------------------------------------------------+
|                   TIER 2: EXTENSION TABLES                      |
|   Linked via patient_id or diagnosis_cluster foreign keys      |
|                                                                |
|   CLINICAL PANELS           GENETIC                            |
|   +-------------------+    +----------------------------+      |
|   | autoantibody_panel|    | genetic_risk_scores        |      |
|   | 12,085 rows       |    | 69,889 FinnGen + HugeAmp   |      |
|   +-------------------+    +----------------------------+      |
|   | longitudinal_labs |    | gwas_catalog_associations  |      |
|   | 19,646 obs        |    | (NHGRI-EBI curated hits)   |      |
|   +-------------------+    +----------------------------+      |
|   |                   |    | pan_ukbb_sumstats          |      |
|   |                   |    | (Pan-ancestry GWAS)        |      |
|   |                   |    +----------------------------+      |
|   |                   |    | immunobase_credible_sets   |      |
|   |                   |    | (Fine-mapped loci)         |      |
|   |                   |    +----------------------------+      |
|   |                   |    | hla_frequencies            |      |
|   |                   |    | (AFND population-level)    |      |
|   +-------------------+    +----------------------------+      |
|   | mimic_prescriptions|                                       |
|   | mimic_microbiology |   OMICS                               |
|   +-------------------+    +----------------------------+      |
|                            | transcriptomics_signatures |      |
|                            | (ADEx + IAAA)              |      |
|                            +----------------------------+      |
|                            | microbiome_profiles        |      |
|                            | (HMP gut taxon abundances) |      |
|                            +----------------------------+      |
|                            | proteomics_associations    |      |
|                            | (Olink/UKB-PPP)           |      |
|                            +----------------------------+      |
|                            | metabolomics_associations  |      |
|                            | (HMDB + MetaboLights)      |      |
|                            +----------------------------+      |
+----------------------------------------------------------------+
|                   TIER 3: REFERENCE LOOKUPS                    |
|   Static tables queried at inference time                      |
|   +------------------+ +------------------+ +----------------+ |
|   | drug_risk_index  | | healthy_baselines| | icd_cluster_map| |
|   | 597 rows         | | 110 rows         | | 111 rows       | |
|   +------------------+ +------------------+ +----------------+ |
|   | open_targets     | | ctd_chemical_    | | epa_air_quality| |
|   | _associations    | | disease          | | _reference     | |
|   +------------------+ +------------------+ +----------------+ |
|   | hpa_protein_     | | mendeley_        |                    |
|   | expression       | | lipidomics       |                    |
|   +------------------+ +------------------+                    |
+----------------------------------------------------------------+
```

### Tier 1: Core Matrices (Patient-Level Training Tables)
Every row represents **one patient at one point in time**. These are the primary training tables for classification models. The `core_matrix` holds clinical lab data; `patient_reported_outcomes` holds longitudinal symptom data from Flaredown (different grain: daily entries per patient).

### Tier 2: Extension Tables (Specialized Signal Preservers)
Linked to Tier 1 via `patient_id` FK (for patient-level data) or `diagnosis_cluster` FK (for disease-level aggregate data like transcriptomics signatures). These store features that only exist in a subset of datasets.

### Tier 3: Reference Lookups (Context Layers)
Not patient-level. Static reference tables the model queries at inference time to add context (e.g., "Is this patient on a drug known to mimic lupus?", "Is this chemical linked to autoimmune disease?", "What protein biomarkers distinguish SLE from RA?").

---

## 3. Tier 1: Core Matrix Schema (Implemented)

### 3.1 Unified Column Mapping

Every dataset contributes to this shared schema. Columns not present in a source dataset are filled with `NaN` (explicit missingness -- not zero). Imputation is applied per the missingness strategy in Section 8.5.

| Unified Column | Type | Unit | Harvard | NHANES | MIMIC |
|:---|:---|:---|:---|:---|:---|
| `patient_id` | str | -- | gen | SEQN-based | subject_id |
| `source` | str | -- | "harvard" | "nhanes" | "mimic_demo" |
| `age` | float | years | Age | RIDAGEYR | anchor_age |
| `sex` | cat | M/F | Gender | RIAGENDR | gender |
| `diagnosis_raw` | str | -- | Diagnosis | MCQ-derived | icd_code |
| `diagnosis_icd10` | str | ICD-10 | mapped | MCQ-mapped | crosswalk |
| `diagnosis_cluster` | str | -- | mapped | MCQ-mapped | mapped |
| `esr` | float | mm/hr | ESR | -- | -- |
| `crp` | float | mg/L | CRP | LBXHSCRP | -- |
| `wbc` | float | 10^3/uL | -- | LBXWBCSI | -- |
| `rbc` | float | 10^6/uL | -- | LBXRBCSI | -- |
| `hemoglobin` | float | g/dL | -- | LBXHGB | -- |
| `hematocrit` | float | % | -- | LBXHCT | -- |
| `mcv` | float | fL | -- | LBXMCVSI | -- |
| `mch` | float | pg | -- | LBXMCHSI | -- |
| `rdw` | float | % | -- | LBXRDW | -- |
| `platelet_count` | float | 10^3/uL | -- | LBXPLTSI | -- |
| `lymphocyte_pct` | float | % | -- | LBXLYPCT | -- |
| `neutrophil_pct` | float | % | -- | LBXNEPCT | -- |
| `bmi` | float | kg/m^2 | -- | BMXBMI | -- |
| `illness_duration` | float | months | -- | -- | -- |

### 3.2 Unit Standardization Rules (Implemented)

The `detect_and_convert_units()` function uses median-based heuristics to detect and correct unit mismatches at ingest time. It requires >= 10 non-null values to trigger.

| Marker | Canonical Unit | Detection Rule | Conversion |
|:---|:---|:---|:---|
| WBC | 10^3/uL | median > 30 (cells/uL range) | divide by 1000 |
| Hemoglobin | g/dL | median > 50 (g/L range) | divide by 10 |
| Platelet count | 10^3/uL | median > 50000 (cells/uL range) | divide by 1000 |
| CRP | mg/L | Generally consistent | verify per source |

### 3.3 Diagnosis Label Harmonization (Implemented)

All diagnoses are mapped to ICD-10 codes via a case-insensitive lookup dictionary covering 130+ autoimmune conditions.

| Source | Original Format | Mapping Strategy | Coverage |
|:---|:---|:---|:---|
| Harvard Dataverse | Disease name strings | `DISEASE_TO_ICD10` lookup (case-insensitive) | ~100% |
| NHANES | MCQ self-reported conditions | MCQ160A/MCQ195 (arthritis type), MCQ160N (lupus), MCQ160M (thyroid), MCQ160K (celiac) | ~100% |
| MIMIC-IV Demo | ICD-9 codes | `ICD9_TO_ICD10` crosswalk dictionary | Partial |

### 3.4 Diagnosis Clusters (Implemented)

ICD-10 codes are grouped into 11 Aura clusters via `ICD10_TO_CLUSTER`:

| Cluster | ICD-10 Prefixes | Example Conditions |
|:---|:---|:---|
| `healthy` | Z00 | Healthy controls (NHANES, Harvard) |
| `systemic` | M05, M06, M32, M33, M34, M35 | RA, SLE, Sjogren's, Scleroderma |
| `endocrine` | E06, E10, E05 | Hashimoto's, T1D, Graves' |
| `gastrointestinal` | K50, K51, K52, K90 | Crohn's, UC, Celiac, IBD |
| `neurological` | G35, G61, G70 | MS, Guillain-Barre, Myasthenia Gravis |
| `dermatological` | L10, L12, L13, L40, L63, L80 | Psoriasis, Pemphigus, Vitiligo, Alopecia |
| `ophthalmic` | H20 | Uveitis, Scleritis |
| `other_autoimmune` | D86, M30, M45 | Sarcoidosis, Polyarteritis, AS |
| `haematological` | D59, D69 | AIHA, ITP |
| `renal` | N04, M32.1 | Nephrotic syndrome, Lupus nephritis |
| `pulmonary` | J84 | Idiopathic pulmonary fibrosis |

See `dataget.md` Source Breakdown for current per-source cluster counts.

---

## 4. Tier 1 Expansion: New Patient-Level Sources

### 4.1 NHANES MCQ -- Autoimmune Condition Flags (IMPLEMENTED -- DO NOT REWRANGLE)
*Source: NHANES MCQ_G through MCQ_J (4 cycles)*

MCQ reclassification is complete and integrated into the core_matrix. NHANES patients now have MCQ-derived autoimmune diagnoses: systemic (2,063), endocrine (1,943), gastrointestinal (801). MCQ fields used: MCQ160A/MCQ195 (arthritis type), MCQ160N (lupus), MCQ160M (thyroid), MCQ160K (celiac). See `dataget.md` for current cluster breakdown.

### 4.2 Flaredown Patient-Reported Outcomes (Not Yet Implemented)
*Source: Kaggle Flaredown dataset (~1,700 patients, daily longitudinal entries)*

**Goal:** Create a separate Tier 1 table for patient-reported outcomes. This data has a fundamentally different grain (daily symptom entries per patient) that doesn't fit into the single-snapshot core_matrix.

**Target table: `patient_reported_outcomes`**

| Column | Type | Source Column | Notes |
|:---|:---|:---|:---|
| `patient_id` | str | gen | `flaredown_{user_id}` |
| `source` | str | -- | Always "flaredown" |
| `date` | date | trackable_date | Daily entry date |
| `condition` | str | condition_name | Self-reported condition (e.g., "Lupus", "Crohn's") |
| `diagnosis_cluster` | str | mapped | Map condition_name to Aura cluster |
| `symptom` | str | symptom_name | What symptom (e.g., "Fatigue", "Joint Pain") |
| `symptom_severity` | int | symptom_value | 0-4 severity scale |
| `treatment` | str | treatment_name | Medication or treatment |
| `treatment_dose` | str | treatment_dose | Dosage if reported |
| `trigger` | str | trigger_name | Environmental trigger (food, stress, etc.) |
| `country` | str | country | Patient country (57 countries) |

**Wrangling steps:**
1. Load the Flaredown CSV from Databricks Volume `raw/flaredown/`.
2. Parse the wide-format CSV into a long-format table (one row per symptom/treatment/trigger entry per day).
3. Map `condition_name` to `diagnosis_cluster` via fuzzy matching against `DISEASE_TO_ICD10`.
4. Generate `patient_id` as `flaredown_{user_id}`.
5. Validate date ranges and remove entries with missing dates.
6. Export as `tier1_patient_reported_outcomes.parquet`.

**Key considerations:**
- This table is NOT joinable to `core_matrix` by patient_id (different patients entirely).
- It IS joinable by `diagnosis_cluster` for disease-level aggregation.
- Primary use: learning symptom-treatment-trigger temporal patterns per condition.
- Secondary use: symptom severity distributions as features for the patient-facing translator agent.

### 4.3 MIMIC-IV Demo -- Extended Clinical Tables (Not Yet Implemented)
*Source: MIMIC-IV Demo 35 CSV files across hosp/ and icu/ subdirectories*

**Goal:** Extract additional clinical context for the 100 MIMIC patients already in the core_matrix. Currently we only use labevents; the full demo has prescriptions, diagnoses, microbiology, chart events, and ICU stays.

**New Tier 2 extension tables to create:**

**`mimic_prescriptions`** (FK to core_matrix via patient_id):

| Column | Type | Source | Notes |
|:---|:---|:---|:---|
| `patient_id` | str | subject_id | `mimic_demo_{subject_id}` |
| `drug` | str | drug | Drug name |
| `drug_type` | str | drug_type | MAIN, BASE, ADDITIVE |
| `route` | str | route | IV, PO, etc. |
| `start_dt` | str | starttime | Prescription start |
| `stop_dt` | str | stoptime | Prescription stop |

**`mimic_microbiology`** (FK to core_matrix via patient_id):

| Column | Type | Source | Notes |
|:---|:---|:---|:---|
| `patient_id` | str | subject_id | `mimic_demo_{subject_id}` |
| `charttime` | str | charttime | When sample was drawn |
| `spec_type` | str | spec_type_desc | Specimen type (BLOOD, URINE, etc.) |
| `org_name` | str | org_name | Organism identified |
| `interpretation` | str | interpretation | S/R/I (susceptibility) |

**Wrangling steps:**
1. Decompress `mimic_iv_demo.zip` if not already done.
2. Load `hosp/prescriptions.csv.gz`, `hosp/microbiologyevents.csv.gz`.
3. Map subject_id to `patient_id` = `mimic_demo_{subject_id}`.
4. Validate FK integrity against core_matrix.
5. Export as `tier2_mimic_prescriptions.parquet` and `tier2_mimic_microbiology.parquet`.

---

## 5. Tier 2: Extension Tables

### 5.1 Autoantibody Panel (Implemented -- Harvard Only)
*Source: Harvard Dataverse (12,085 rows)*

| Column | Type | Values | Notes |
|:---|:---|:---|:---|
| `patient_id` | str | | FK to Core Matrix |
| `ana_status` | float | 0.0 / 1.0 | Antinuclear Antibody |
| `anti_dsdna` | float | 0.0 / 1.0 | Anti-double-stranded DNA |
| `hla_b27` | float | 0.0 / 1.0 | HLA-B27 antigen |
| `anti_sm` | float | 0.0 / 1.0 | Anti-Smith antibody |
| `anti_ro` | float | 0.0 / 1.0 | Anti-Ro/SSA antibody |
| `anti_la` | float | 0.0 / 1.0 | Anti-La/SSB antibody |
| `rf_status` | float | 0.0 / 1.0 | Rheumatoid Factor |
| `anti_ccp` | float | 0.0 / 1.0 | Anti-CCP antibody |
| `c3` | float | mg/dL | Complement C3 level |
| `c4` | float | mg/dL | Complement C4 level |

### 5.2 Genetic Risk Scores (Implemented -- DO NOT REWRANGLE)
*Source: FinnGen R12 (67,869 rows) + HugeAmp BioIndex (~2,020 rows)*

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | "finngen_r12" or "hugeamp" |
| `variant_id` | str | rsID or chr:pos format |
| `gene` | str | Nearest gene to the variant |
| `chrom` | str | Chromosome |
| `pos` | bigint | Genomic position |
| `ref` / `alt` | str | Reference and alternate alleles |
| `pvalue` | float | GWAS p-value |
| `beta` | float | Effect size |
| `se` | float | Standard error |
| `af` | float | Allele frequency |
| `finngen_endpoint` | str | FinnGen phenotype code (empty for HugeAmp) |
| `diagnosis_cluster` | str | Mapped Aura cluster |
| `diagnosis_icd10` | str | ICD-10 code |
| `queried_phenotype` | str | HugeAmp phenotype code (HugeAmp rows only) |

### 5.3 GWAS Catalog Associations (Not Yet Implemented)
*Source: NHGRI-EBI GWAS Catalog (downloaded to Databricks Volume `raw/gwas_catalog/`)*

**Goal:** Extend the genetic_risk_scores table with curated associations from the GWAS Catalog. This adds breadth beyond FinnGen's 5 endpoints and HugeAmp's 13 phenotypes, covering all published autoimmune GWAS.

**Target table: `gwas_catalog_associations`**

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | Always "gwas_catalog" |
| `variant_id` | str | rsID |
| `gene` | str | Reported gene(s) |
| `chrom` | str | Chromosome |
| `pos` | bigint | Genomic position (GRCh38) |
| `risk_allele` | str | Strongest risk allele |
| `pvalue` | float | P-value |
| `or_beta` | float | Odds ratio or beta |
| `ci_95` | str | 95% confidence interval |
| `trait` | str | Reported trait (e.g., "Rheumatoid arthritis") |
| `study_accession` | str | GWAS Catalog study ID (e.g., GCST000001) |
| `pubmed_id` | str | PubMed ID of the source study |
| `diagnosis_cluster` | str | Mapped Aura cluster |
| `diagnosis_icd10` | str | Mapped ICD-10 code |

**Wrangling steps:**
1. Load the parquet file from Databricks Volume.
2. Filter to autoimmune-related traits using keyword matching against the `trait` field.
3. Map trait names to `diagnosis_cluster` and `diagnosis_icd10` via the existing disease lookup.
4. Standardize variant_id format (ensure consistent rsID representation).
5. Deduplicate on (variant_id, trait, study_accession).
6. Export as `tier2_gwas_catalog_associations.parquet`.

### 5.4 Pan-UK Biobank Summary Statistics (Not Yet Implemented)
*Source: Pan-UKBB GWAS (downloaded to Databricks Volume `raw/pan_ukbb/`)*

**Goal:** Add pan-ancestry GWAS summary statistics for autoimmune phenotypes. This is the only multi-ancestry GWAS source in the lake.

**Target table: `pan_ukbb_sumstats`**

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | Always "pan_ukbb" |
| `variant_id` | str | chr:pos:ref:alt format |
| `gene` | str | Nearest gene (if annotated) |
| `chrom` | str | Chromosome |
| `pos` | bigint | Genomic position (GRCh37) |
| `ref` / `alt` | str | Reference and alternate alleles |
| `pvalue` | float | P-value (meta-analysis across ancestries) |
| `beta` | float | Effect size |
| `se` | float | Standard error |
| `af` | float | Allele frequency |
| `ancestry` | str | EUR, AFR, EAS, AMR, SAS, MID |
| `phenotype` | str | UKBB phenotype code |
| `phenotype_description` | str | Human-readable phenotype name |
| `diagnosis_cluster` | str | Mapped Aura cluster |
| `n_cases` | int | Number of cases |
| `n_controls` | int | Number of controls |
| `heritability` | float | SNP heritability estimate |

**Wrangling steps:**
1. Load the bgzipped TSV from Databricks Volume.
2. Filter to autoimmune-related phenotypes using a phenotype manifest lookup.
3. Filter to genome-wide significant hits (p < 5e-8) to keep table sizes manageable.
4. Map phenotype codes to Aura `diagnosis_cluster`.
5. Standardize variant_id to match the FinnGen/GWAS Catalog format for cross-table joins.
6. Export as `tier2_pan_ukbb_sumstats.parquet`.

### 5.5 ImmunoBase Fine-Mapping Credible Sets (Not Yet Implemented)
*Source: ImmunoBase (downloaded to Databricks Volume `raw/immunobase/`)*

**Goal:** Add fine-mapped credible variant sets for autoimmune loci. These narrow down GWAS signals to likely causal variants -- a precision layer the broader GWAS tables can't provide.

**Target table: `immunobase_credible_sets`**

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | Always "immunobase" |
| `locus_id` | str | Locus identifier |
| `variant_id` | str | rsID |
| `chrom` | str | Chromosome |
| `pos` | bigint | Genomic position |
| `posterior_probability` | float | Posterior probability of being causal |
| `credible_set_size` | int | Number of variants in the credible set |
| `disease` | str | Disease name |
| `diagnosis_cluster` | str | Mapped Aura cluster |

**Wrangling steps:**
1. Load the ImmunoBase files from Databricks Volume.
2. Parse the per-disease credible set files.
3. Standardize variant_id format.
4. Map disease names to Aura clusters.
5. Export as `tier2_immunobase_credible_sets.parquet`.

### 5.6 HLA Frequencies (Not Yet Implemented)
*Source: AFND via HLAfreq package (downloaded to Databricks Volume `raw/afnd/`)*

**Goal:** Population-level HLA allele frequencies. HLA is the single strongest genetic risk factor for most autoimmune diseases. This table lets the model incorporate population-stratified HLA risk.

**Target table: `hla_frequencies`**

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | Always "afnd" |
| `hla_locus` | str | HLA-A, -B, -C, -DRB1, -DQB1 |
| `allele` | str | HLA allele name (e.g., "A*02:01") |
| `population` | str | Population name |
| `region` | str | Geographic region |
| `sample_size` | int | Number of individuals |
| `frequency` | float | Allele frequency (0-1) |
| `associated_diseases` | str | Autoimmune diseases linked to this allele (from KIR-disease DB) |

**Wrangling steps:**
1. Load the parquet file from Databricks Volume.
2. Filter to HLA loci relevant to autoimmune disease (DRB1, DQB1, B primarily).
3. Normalize allele naming conventions (2-field vs 4-field resolution).
4. Add disease association annotations from AFND's KIR-disease database.
5. Export as `tier2_hla_frequencies.parquet`.

### 5.7 Longitudinal Labs (Implemented -- DO NOT REWRANGLE)
*Source: MIMIC-IV Demo (19,646 observations)*

| Column | Type | Notes |
|:---|:---|:---|
| `patient_id` | str | FK to Core Matrix |
| `event_timestamp` | str | When the lab was drawn |
| `lab_item` | str | wbc, rbc, hemoglobin, hematocrit, platelet_count, mcv, mch, rdw, esr, crp |
| `lab_value` | float | Measured value |
| `lab_unit` | str | Unit of measurement |
| `source` | str | Always "mimic_demo" |

### 5.8 Transcriptomics Signatures (Not Yet Implemented)
*Sources: ADEx (5 GEO matrices) + IAAA (1 GEO matrix)*

**Goal:** Extract disease-level gene expression signatures that can be linked to Aura diagnosis clusters. Not patient-level (different patients from different studies), but disease-level aggregate signatures.

**Target table: `transcriptomics_signatures`**

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | "adex" or "iaaa" |
| `study_id` | str | GEO accession (e.g., GSE12345) |
| `disease` | str | Disease name from study metadata |
| `diagnosis_cluster` | str | Mapped Aura cluster |
| `sample_type` | str | "expression" or "methylation" |
| `gene_symbol` | str | Gene symbol |
| `log2_fc` | float | Log2 fold-change (disease vs healthy) |
| `adj_pvalue` | float | Adjusted p-value |
| `direction` | str | "up" or "down" |
| `platform` | str | Microarray/RNA-seq platform |
| `n_disease` | int | Number of disease samples |
| `n_control` | int | Number of control samples |

**Wrangling steps (ADEx):**
1. Load the 5 GEO expression matrices from Databricks Volume `raw/adex/`.
2. For each matrix: read sample metadata to identify disease vs control groups.
3. Compute differential expression (log2 fold-change + adjusted p-value) per gene per disease.
4. Filter to significant genes (adj_pvalue < 0.05, |log2_fc| > 1.0).
5. Map disease names to Aura clusters.
6. Combine all studies into a single table.

**Wrangling steps (IAAA):**
1. Load the bulk RNA-seq expression matrix from Databricks Volume `raw/iaaa/`.
2. Parse sample annotations to extract disease labels (10 autoimmune diseases).
3. Compute disease-vs-healthy differential expression signatures.
4. Filter and format identically to ADEx.
5. Append to the combined transcriptomics_signatures table.
6. Export as `tier2_transcriptomics_signatures.parquet`.

**Join strategy:** Linked to core_matrix via `diagnosis_cluster` (not patient_id). Used to identify which genes are differentially expressed in a patient's diagnosed condition.

### 5.9 Microbiome Profiles (Not Yet Implemented)
*Source: Human Microbiome Project (downloaded to Databricks Volume `raw/hmp/`)*

**Goal:** Healthy gut microbiome reference profiles. Similar to how `healthy_baselines` provides reference lab ranges, this provides reference microbial composition.

**Target table: `microbiome_profiles`**

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | Always "hmp" |
| `sample_id` | str | HMP sample identifier |
| `body_site` | str | Stool, oral, skin, etc. |
| `subject_id` | str | De-identified subject |
| `taxon_level` | str | phylum, class, order, family, genus, species |
| `taxon_name` | str | Taxonomic name |
| `relative_abundance` | float | 0-1 relative abundance |
| `sequencing_method` | str | 16S or WGS |

**Wrangling steps:**
1. Load the 2 CSV files from Databricks Volume `raw/hmp/`.
2. Parse the OTU/taxon abundance table into long format.
3. Filter to gut (stool) samples only (primary relevance for autoimmune-gut axis).
4. Normalize abundance values to relative proportions summing to 1.0 per sample.
5. Export as `tier2_microbiome_profiles.parquet`.

### 5.10 Proteomics Associations (Not Yet Implemented)
*Source: Olink/UKB-PPP (downloaded to Databricks Volume `raw/olink/`)*

**Goal:** Protein-disease risk associations for autoimmune conditions. Each row links a plasma protein to a disease with an effect size.

**Target table: `proteomics_associations`**

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | Always "olink_ukbppp" |
| `protein` | str | Protein name (Olink panel ID) |
| `gene` | str | Gene encoding the protein |
| `uniprot_id` | str | UniProt accession |
| `disease` | str | Disease name |
| `diagnosis_cluster` | str | Mapped Aura cluster |
| `beta` | float | Effect size (NPX units) |
| `se` | float | Standard error |
| `pvalue` | float | P-value |
| `n_cases` | int | Number of cases |
| `direction` | str | "up" or "down" in disease vs healthy |

**Wrangling steps:**
1. Load the xlsx file from Databricks Volume `raw/olink/`.
2. Parse the protein-disease association table.
3. Filter to autoimmune-related diseases using keyword matching.
4. Map disease names to Aura clusters.
5. Standardize protein identifiers (add UniProt IDs where possible).
6. Export as `tier2_proteomics_associations.parquet`.

### 5.11 Metabolomics Associations (Not Yet Implemented)
*Sources: HMDB (1 CSV) + MetaboLights (1 parquet index)*

**Goal:** Metabolite-disease associations and reference concentration ranges for autoimmune conditions.

**Target table: `metabolomics_associations`**

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | "hmdb" or "metabolights" |
| `metabolite_id` | str | HMDB ID or MetaboLights accession |
| `metabolite_name` | str | Common name |
| `chemical_class` | str | Lipid, amino acid, etc. |
| `disease` | str | Associated disease |
| `diagnosis_cluster` | str | Mapped Aura cluster |
| `normal_low` | float | Normal concentration lower bound |
| `normal_high` | float | Normal concentration upper bound |
| `unit` | str | Concentration unit |
| `biofluid` | str | Serum, plasma, urine, etc. |
| `direction` | str | "elevated" or "decreased" in disease |

**Wrangling steps (HMDB):**
1. Load the CSV from Databricks Volume `raw/hmdb/`.
2. Parse metabolite records, extracting disease associations and normal concentration ranges.
3. Filter to metabolites with autoimmune disease associations.
4. Map disease names to Aura clusters.

**Wrangling steps (MetaboLights):**
1. Load the parquet index from Databricks Volume `raw/metabolights/`.
2. Extract study-level metadata (study ID, disease, sample count, metabolites measured).
3. Filter to autoimmune-related studies.
4. Combine with HMDB data.
5. Export as `tier2_metabolomics_associations.parquet`.

---

## 6. Tier 3: Reference Lookups

### 6.1 Drug-Induced Autoimmunity Risk Index (Implemented)
*Source: UCI Repository (597 compounds)*

| Column | Type | Notes |
|:---|:---|:---|
| `Label` | int | 0 = no autoimmunity risk, 1 = autoimmunity risk |
| `SMILES` | str | Drug molecular structure (SMILES notation) |
| `split` | str | "train" or "test" (original dataset split) |
| *(195 columns)* | float/int | Physicochemical descriptors (MolWt, MolLogP, TPSA, etc.) |

### 6.2 Healthy Baseline Reference Ranges (Implemented)
*Source: NHANES healthy controls (CRP <= 10 mg/L filter applied)*

| Column | Type | Notes |
|:---|:---|:---|
| `marker` | str | Lab marker name (11 markers) |
| `age_bucket` | str | "0-17", "18-30", "31-45", "46-60", "61+" |
| `sex` | str | M/F |
| `count` | int | Number of subjects in this stratum |
| `p5` - `p95` | float | 5th, 25th, 50th, 75th, 95th percentiles |

### 6.3 ICD-10 to Aura Cluster Mapping (Implemented)

| Column | Type | Notes |
|:---|:---|:---|
| `icd10_code` | str | Standard ICD-10 code |
| `icd10_description` | str | Human-readable disease name |
| `aura_cluster` | str | One of the 11 clusters listed in Section 3.4 |

### 6.4 Open Targets Associations (Not Yet Implemented)
*Source: Open Targets Platform (downloaded to Databricks Volume `raw/open_targets/`)*

**Goal:** Drug-target-disease association scores aggregated from 22 evidence sources. Supplements the UCI drug_risk_index with validated drug-target evidence for autoimmune conditions.

**Target table: `open_targets_associations`**

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | Always "open_targets" |
| `target_id` | str | Ensembl gene ID |
| `target_symbol` | str | Gene symbol |
| `disease_id` | str | EFO disease ID |
| `disease_name` | str | Disease name |
| `diagnosis_cluster` | str | Mapped Aura cluster |
| `overall_score` | float | 0-1 overall association score |
| `genetic_association` | float | Genetic evidence score |
| `known_drug` | float | Known drug evidence score |
| `literature` | float | Literature evidence score |
| `animal_model` | float | Animal model evidence score |
| `affected_pathway` | float | Pathway evidence score |

**Wrangling steps:**
1. Load the parquet from Databricks Volume `raw/open_targets/`.
2. Filter to autoimmune disease EFO IDs.
3. Map EFO disease IDs to Aura clusters via a manual EFO-to-ICD10 crosswalk.
4. Keep the evidence-type subscores for feature engineering.
5. Export as `tier3_open_targets_associations.parquet`.

### 6.5 CTD Chemical-Disease Interactions (Not Yet Implemented)
*Source: Comparative Toxicogenomics Database (6 TSV files on Databricks Volume `raw/ctd/`)*

**Goal:** Link environmental chemicals to autoimmune disease pathways. This enables "Is this patient exposed to chemicals known to trigger autoimmunity?" queries.

**Target table: `ctd_chemical_disease`**

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | Always "ctd" |
| `chemical_name` | str | Chemical name |
| `chemical_id` | str | MeSH ID |
| `cas_rn` | str | CAS registry number |
| `disease_name` | str | Disease name |
| `disease_id` | str | MeSH/OMIM ID |
| `diagnosis_cluster` | str | Mapped Aura cluster |
| `direct_evidence` | str | "marker/mechanism" or "therapeutic" |
| `inference_gene_symbol` | str | Gene mediating the interaction |
| `inference_score` | float | CTD inference score |
| `pubmed_ids` | str | Pipe-separated PubMed IDs |

**Wrangling steps:**
1. Load the 6 TSV files from Databricks Volume `raw/ctd/`.
2. Focus on `CTD_chemicals_diseases.tsv.gz` as the primary file.
3. Filter to autoimmune-related diseases using MeSH disease tree traversal (Immune System Diseases branch).
4. Map CTD disease names to Aura clusters.
5. Separate direct evidence (curated) from inferred associations.
6. Export as `tier3_ctd_chemical_disease.parquet`.

### 6.6 EPA Air Quality Reference (Not Yet Implemented)
*Source: EPA AQS (22 files on Databricks Volume `raw/epa_aqs/`)*

**Goal:** County-level annual pollutant concentrations for environmental exposure modeling. Published research links PM2.5 to increased RA, connective tissue disease, and IBD risk.

**Target table: `epa_air_quality_reference`**

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | Always "epa_aqs" |
| `year` | int | Measurement year |
| `state_code` | str | FIPS state code |
| `county_code` | str | FIPS county code |
| `state_name` | str | State name |
| `county_name` | str | County name |
| `latitude` | float | Monitor latitude |
| `longitude` | float | Monitor longitude |
| `parameter` | str | PM2.5, PM10, Ozone, NO2, SO2 |
| `arithmetic_mean` | float | Annual mean concentration |
| `first_max_value` | float | Annual max value |
| `unit` | str | ug/m3, ppb, ppm |
| `observation_count` | int | Number of daily observations |

**Wrangling steps:**
1. Load the 22 files from Databricks Volume `raw/epa_aqs/` (multiple years, multiple pollutants).
2. Parse annual summary files (pre-aggregated by EPA).
3. Filter to the 5 pollutants of interest (PM2.5, PM10, Ozone, NO2, SO2).
4. Standardize column names across years.
5. Aggregate to county-level annual means.
6. Export as `tier3_epa_air_quality_reference.parquet`.

**Join strategy:** This table is not directly joinable to patients (we don't have patient ZIP codes). It serves as a population-level context layer: "Given this patient is from county X, what is their average PM2.5 exposure?"

### 6.7 Human Protein Atlas Expression Reference (Not Yet Implemented)
*Source: HPA v25 (2 files on Databricks Volume `raw/hpa/`)*

**Goal:** Protein expression profiles across disease cohorts, providing a reference for which proteins are over/under-expressed in autoimmune conditions.

**Target table: `hpa_protein_expression`**

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | Always "hpa_v25" |
| `gene` | str | Gene symbol |
| `protein` | str | Protein name |
| `disease` | str | Disease cohort |
| `diagnosis_cluster` | str | Mapped Aura cluster |
| `tissue` | str | Blood, plasma, etc. |
| `expression_level` | str | Not detected / Low / Medium / High |
| `tpm` | float | Transcripts per million (if available) |
| `reliability` | str | Enhanced / Supported / Approved / Uncertain |

**Wrangling steps:**
1. Load the 2 files from Databricks Volume `raw/hpa/`.
2. Filter to blood/plasma protein expression data.
3. Filter to autoimmune-relevant disease cohorts.
4. Map disease names to Aura clusters.
5. Export as `tier3_hpa_protein_expression.parquet`.

### 6.8 Mendeley Lipidomics Reference (Not Yet Implemented)
*Source: Mendeley Data (3 CSVs on Databricks Volume `raw/mendeley/`)*

**Goal:** Plasma lipidomics and flow cytometry reference data for model validation (not training due to small sample size).

**Target table: `mendeley_lipidomics`**

| Column | Type | Notes |
|:---|:---|:---|
| `source` | str | Always "mendeley" |
| `sample_id` | str | Sample identifier |
| `condition` | str | "systemic_sclerosis" or "healthy" |
| `diagnosis_cluster` | str | "systemic" or "healthy" |
| `analyte_type` | str | "lipid" or "cytokine" |
| `analyte_name` | str | Lipid species or cytokine name |
| `value` | float | Measured value |
| `unit` | str | Concentration unit |

**Wrangling steps:**
1. Load the 3 CSVs from Databricks Volume `raw/mendeley/`.
2. Parse into long format (one row per analyte per sample).
3. Identify condition groups from metadata.
4. Map conditions to Aura clusters.
5. Export as `tier3_mendeley_lipidomics.parquet`.

---

## 7. NHANES MCQ Reclassification (IMPLEMENTED -- DO NOT REWRANGLE)

NHANES MCQ reclassification is complete. MCQ fields used: MCQ160A/MCQ195 (arthritis type), MCQ160N (lupus), MCQ160M (thyroid), MCQ160K (celiac). Result: NHANES patients now have autoimmune diagnoses -- systemic (2,063), endocrine (1,943), gastrointestinal (801), with 31,102 remaining as healthy. See `dataget.md` for the authoritative current state.

---

## 8. The ETL Pipeline

### Phase 1 (Implemented): Core Clinical + Genetics

The pipeline is implemented in `scripts/02_wrangle_data.py` with 39 passing tests in `tests/test_02_wrangle_data.py`.

#### 8.1 Phase 1.1: Ingest & Normalize (Per-Dataset)
For each dataset independently:
1. **Load** raw files (CSV, XPT, Excel) into pandas DataFrames.
2. **Rename columns** to the unified schema using a per-source mapping dictionary.
3. **Convert units** via `detect_and_convert_units()` -- median-based heuristic that auto-detects and corrects unit mismatches for WBC, hemoglobin, and platelets.
4. **Map diagnosis labels** to ICD-10 via case-insensitive lookup against 130+ entries in `DISEASE_TO_ICD10`.
5. **Map categorical values** (Positive/Negative) to binary (1.0/0.0) via `map_categorical_to_binary()`.
6. **Generate a unique `patient_id`** prefixed with the source name (e.g., `harvard_0001`, `nhanes_12345`).
7. **Tag with `source` column** for downstream filtering and bias analysis.

#### 8.2 Phase 1.2: Split into Tiers
For each normalized DataFrame:
1. **Extract Tier 1 columns** -> append to master `core_matrix` DataFrame.
2. **Extract Tier 2 columns** (if present) -> write to appropriate extension table.
3. **Validate** that every Tier 2 row has a valid FK back to Tier 1.

#### 8.3 Phase 1.3: Compute Healthy Baselines
From NHANES healthy controls:
1. **Filter for healthy subjects only** (CRP <= 10 mg/L to exclude subclinical inflammation).
2. **Stratify by age bucket + sex** (5 age buckets x 2 sexes = 10 strata per marker).
3. **Compute percentile distributions** (p5, p25, p50, p75, p95) for 11 lab markers.
4. **Export** to the Tier 3 Baseline Reference table.

#### 8.4 Phase 1.4: Feature Engineering & Z-Score Normalization
For every row in the Core Matrix:
1. **Look up** the patient's age/sex bucket in the Baseline Reference table.
2. **Compute an IQR-based Z-score** for each lab marker: `z = (patient_value - p50) / (p75 - p25)`.
3. **Store Z-scores as new columns** (e.g., `wbc_zscore`, `crp_zscore`).

IQR-based z-scores are more robust to outliers than standard deviation-based z-scores. This transforms raw values into **"how far from normal is this person?"** -- the fundamental question Aura answers.

#### 8.5 Phase 1.5: Handle Missingness
Missingness is **informative**, not random. A missing Anti-CCP test means the doctor didn't think to order it -- which itself is a signal.

| Strategy | When to Apply | Implementation |
|:---|:---|:---|
| **Leave as NaN** | Tier 2 features that only exist in specific datasets | Default behavior |
| **Median imputation** | Tier 1 features with <15% missingness within a source | Per-source median fill |
| **KNN imputation** | Tier 1 features with 15-40% missingness | `sklearn.impute.KNNImputer` (k=5) |
| **Missingness indicator** | ALL imputed columns | Binary `{column}_missing` flag (0/1) added before imputation |
| **Do not impute** | Features with >40% missingness within a source | Left as NaN |

#### 8.6 Phase 1.6: FinnGen GWAS Processing
Runs as a Databricks notebook (`wrangle_additional_datasets`):
1. **Read** each FinnGen `.gz` summary stats file in 500K-row chunks.
2. **Filter** to genome-wide significant hits (p < 5e-8 or mlogp > 7.3).
3. **Annotate** with Aura cluster and ICD-10 code per endpoint.
4. **Combine** all endpoints and export to `tier2_genetic_risk_scores.parquet`.

### Phase 2 (Not Yet Implemented): Extended Clinical

#### 8.7 Phase 2.1: MIMIC-IV Extended Tables
1. **Decompress** `mimic_iv_demo.zip`.
2. **Load** prescriptions, microbiology, and other clinical tables.
3. **Map** subject_id to patient_id.
4. **Export** as separate Tier 2 parquet files.

#### 8.8 Phase 2.2: Flaredown Patient-Reported Outcomes
1. **Load** Flaredown CSV from Databricks Volume.
2. **Parse** wide format to long format.
3. **Map** conditions to Aura clusters.
4. **Export** as `tier1_patient_reported_outcomes.parquet`.

### Phase 3 (Not Yet Implemented): Genetics Expansion

#### 8.9 Phase 3.1: GWAS Catalog
1. **Load** parquet from Databricks Volume `raw/gwas_catalog/`.
2. **Filter** to autoimmune traits.
3. **Map** to Aura clusters and ICD-10.
4. **Deduplicate** on (variant_id, trait, study_accession).
5. **Export** as `tier2_gwas_catalog_associations.parquet`.

#### 8.10 Phase 3.2: Pan-UK Biobank
1. **Load** bgzipped TSV from Databricks Volume `raw/pan_ukbb/`.
2. **Filter** to autoimmune phenotypes + genome-wide significance.
3. **Map** phenotype codes to Aura clusters.
4. **Standardize** variant_id format.
5. **Export** as `tier2_pan_ukbb_sumstats.parquet`.

#### 8.11 Phase 3.3: ImmunoBase + AFND
1. **Process** ImmunoBase credible sets -> `tier2_immunobase_credible_sets.parquet`.
2. **Process** AFND HLA frequencies -> `tier2_hla_frequencies.parquet`.

### Phase 4 (Not Yet Implemented): Omics + Environmental

#### 8.12 Phase 4.1: Transcriptomics (ADEx + IAAA)
1. **Load** GEO matrices from Databricks Volume.
2. **Compute** disease-vs-healthy differential expression.
3. **Filter** to significant genes.
4. **Map** diseases to Aura clusters.
5. **Export** as `tier2_transcriptomics_signatures.parquet`.

#### 8.13 Phase 4.2: Microbiome (HMP)
1. **Load** CSVs from Databricks Volume.
2. **Filter** to gut samples.
3. **Normalize** to relative abundances.
4. **Export** as `tier2_microbiome_profiles.parquet`.

#### 8.14 Phase 4.3: Proteomics (Olink)
1. **Load** xlsx from Databricks Volume.
2. **Filter** to autoimmune diseases.
3. **Map** to Aura clusters.
4. **Export** as `tier2_proteomics_associations.parquet`.

#### 8.15 Phase 4.4: Metabolomics (HMDB + MetaboLights)
1. **Load** and parse metabolite-disease associations.
2. **Filter** to autoimmune-related metabolites.
3. **Map** to Aura clusters.
4. **Export** as `tier2_metabolomics_associations.parquet`.

#### 8.16 Phase 4.5: Environmental References
1. **Process** CTD -> `tier3_ctd_chemical_disease.parquet`.
2. **Process** EPA AQS -> `tier3_epa_air_quality_reference.parquet`.

#### 8.17 Phase 4.6: Molecular References
1. **Process** Open Targets -> `tier3_open_targets_associations.parquet`.
2. **Process** HPA -> `tier3_hpa_protein_expression.parquet`.
3. **Process** Mendeley -> `tier3_mendeley_lipidomics.parquet`.

---

## 9. Handling Multi-Source Bias

Merging data from different countries, hospitals, and time periods introduces **distributional shift**. Key mitigations:

1. **Source-Aware Training**: Always include the `source` column as a feature. The model learns that a CRP of 5.0 from a US ICU means something different than from an Iraqi clinic.
2. **IQR-Based Z-Scores**: Per-marker z-scores computed against age/sex-matched healthy baselines normalize across sources more robustly than raw values.
3. **Missingness as Signal**: The `{col}_missing` flags let the model learn from what *wasn't* measured, not just what was.
4. **Stratified Sampling**: When splitting train/val/test, stratify by `source` to ensure every dataset is represented proportionally in each split.
5. **Unit Harmonization**: `detect_and_convert_units()` prevents catastrophic distribution shifts from unit mismatches (e.g., WBC in cells/uL vs 10^3/uL).
6. **Omics Data Normalization**: Transcriptomics, proteomics, and metabolomics data from different platforms require platform-specific normalization before cross-study comparison. Use quantile normalization or ComBat batch correction.

---

## 10. Final Output: What the Model Sees

After the full pipeline (all 4 phases), the data lake will contain:

```
workspace.aura (Databricks Unity Catalog)
|
|-- TIER 1: CORE MATRICES
|   |-- core_matrix                       48,094 rows x 44 cols  (Harvard + NHANES w/ MCQ + MIMIC) [LOCKED]
|   +-- patient_reported_outcomes         TBD rows               (Flaredown daily tracking)
|
|-- TIER 2: CLINICAL EXTENSIONS
|   |-- autoantibody_panel                12,085 rows x 11 cols  (Harvard) [LOCKED]
|   |-- longitudinal_labs                 19,646 rows x  6 cols  (MIMIC Demo) [LOCKED]
|   |-- mimic_prescriptions               TBD    rows            (MIMIC Demo)
|   +-- mimic_microbiology                TBD    rows            (MIMIC Demo)
|
|-- TIER 2: GENETIC EXTENSIONS
|   |-- genetic_risk_scores               69,889 rows x 15 cols  (FinnGen + HugeAmp) [LOCKED]
|   |-- gwas_catalog_associations         TBD    rows            (NHGRI-EBI)
|   |-- pan_ukbb_sumstats                 TBD    rows            (Pan-ancestry GWAS)
|   |-- immunobase_credible_sets          TBD    rows            (Fine-mapped loci)
|   +-- hla_frequencies                   TBD    rows            (AFND population-level)
|
|-- TIER 2: OMICS EXTENSIONS
|   |-- transcriptomics_signatures        TBD    rows            (ADEx + IAAA)
|   |-- microbiome_profiles               TBD    rows            (HMP gut)
|   |-- proteomics_associations           TBD    rows            (Olink/UKB-PPP)
|   +-- metabolomics_associations         TBD    rows            (HMDB + MetaboLights)
|
|-- TIER 3: REFERENCE LOOKUPS
|   |-- healthy_baselines                    110 rows x  9 cols  (NHANES) [LOCKED]
|   |-- icd_cluster_map                      111 rows x  3 cols  (Static) [LOCKED]
|   |-- drug_risk_index                      597 rows x 198 cols (UCI) [LOCKED]
|   |-- open_targets_associations            TBD rows            (Drug-target evidence)
|   |-- ctd_chemical_disease                 TBD rows            (Chemical-disease links)
|   |-- epa_air_quality_reference            TBD rows            (County-level pollution)
|   |-- hpa_protein_expression               TBD rows            (Protein expression atlas)
|   +-- mendeley_lipidomics                  TBD rows            (Lipidomics validation)
```

**Total: 24 tables across 3 tiers.** 7 are [LOCKED] (already wrangled and registered -- see Section 0). The remaining 17 are new tables to be created from datasets already staged on the Databricks Volume.

---

## 11. Pipeline Scripts & Notebooks

### Implemented

| File | Purpose | How to Run |
|:---|:---|:---|
| `scripts/01_download_datasets.py` | Downloads raw data locally | `python scripts/01_download_datasets.py` |
| `scripts/02_wrangle_data.py` | Main ETL pipeline (Phase 1: Tiers 1-3) | `python scripts/02_wrangle_data.py` |
| `scripts/03_register_tables.py` | Generates SQL for table registration | `python scripts/03_register_tables.py` |
| `scripts/pipeline.py` | Azure VM: downloads FinnGen + HugeAmp to Databricks | `ssh azureuser@20.65.67.169 && python3 ~/pipeline.py` |
| `scripts/pipeline_remaining.py` | Azure VM: downloads all Phase 2-4 datasets to Databricks | `python3 ~/pipeline_remaining.py --group easy` |
| `scripts/downloads/*.py` | 20 per-dataset download modules | Used by pipeline_remaining.py |
| `tests/test_02_wrangle_data.py` | 39 tests covering Phase 1 pipeline | `pytest tests/test_02_wrangle_data.py` |
| `notebooks/register_tables.py` | Registers all tables in Unity Catalog | Run in Databricks |
| `notebooks/download_additional_datasets.py` | Downloads FinnGen/GWAS/ImmPort to Volumes | Run in Databricks |
| `notebooks/wrangle_additional_datasets.py` | Processes FinnGen into genetic_risk_scores | Run in Databricks |

### Needed (Not Yet Built)

| File | Purpose | Phase |
|:---|:---|:---|
| `scripts/04_wrangle_mimic_extended.py` | MIMIC-IV prescriptions + microbiology | Phase 2 |
| `scripts/05_wrangle_flaredown.py` | Flaredown patient-reported outcomes | Phase 2 |
| `notebooks/wrangle_genetics_expansion.py` | GWAS Catalog + Pan-UKBB + ImmunoBase + AFND | Phase 3 |
| `notebooks/wrangle_omics.py` | ADEx + IAAA + HMP + Olink + HMDB + MetaboLights | Phase 4 |
| `notebooks/wrangle_references.py` | Open Targets + CTD + EPA + HPA + Mendeley | Phase 4 |

---

## 12. Implementation Priority & Ordering

### High Priority (Do First)
These directly improve the core classification model:

1. **GWAS Catalog associations** -- Broadens genetic coverage beyond FinnGen's 5 endpoints.
2. **AFND HLA frequencies** -- HLA is the #1 genetic risk factor for autoimmunity.
3. **CTD chemical-disease** -- Enables environmental risk modeling.
4. **Open Targets** -- Supplements drug_risk_index with validated evidence.

### Medium Priority (Do Second)
These add new modalities:

7. **Flaredown** -- Only source of patient-reported symptom data.
8. **ADEx + IAAA transcriptomics** -- Adds gene expression signatures per disease.
9. **Olink proteomics** -- Adds protein biomarker associations.
10. **Pan-UK Biobank** -- Adds multi-ancestry GWAS (all others are European-only).
11. **ImmunoBase** -- Narrows GWAS signals to causal variants.
12. **EPA AQS** -- County-level environmental exposure data.

### Low Priority (Do Last)
These are smaller or validation-only:

13. **MIMIC-IV extended tables** -- Only 100 patients; limited statistical power.
14. **HMP microbiome** -- Healthy-only reference; no disease microbiome data yet.
15. **HMDB + MetaboLights metabolomics** -- Mostly reference/index data.
16. **HPA protein expression** -- Reference atlas; overlaps with Olink.
17. **Mendeley lipidomics** -- Small validation set, not for training.

---

## 13. Known Issues & Future Work

| Item | Status | Notes |
|:---|:---|:---|
| NHANES HSCRP (2011-2014) | Resolved | HSCRP was NEVER collected in 2011-2012 or 2013-2014 cycles. Valid HSCRP exists for 2015-2016 (I) and 2017-2018 (J) only. |
| HugeAmp GWAS Portal | Resolved | Fixed API endpoint. Downloaded ~2,020 associations across 13 autoimmune phenotypes. |
| ImmPort 10KIP | DUA Accepted | DUA accepted 2026-02-21. Credentials in Databricks secrets. Download pending (requires Azure VM). |
| Databricks Serverless Egress | Blocked | Serverless compute cannot reach external APIs (DNS fails). Workaround: Azure VM + `databricks fs cp`. |
| NHANES MCQ reclassification | Resolved | Implemented. NHANES patients now have MCQ-derived autoimmune diagnoses. |
| MIMIC-IV Demo | Limited | Only 100 patients in demo subset; full MIMIC requires PhysioNet credentials. |
| Polygenic Risk Scores | Not computed | genetic_risk_scores has raw GWAS hits; PRS aggregation is a downstream task. |
| FinnGen individual-level data | Not available | Only public summary statistics used; individual data requires sandbox access. |
| HCA eQTL + Allen Atlas | Not downloaded | Very large single-cell datasets (1.2M and 16M cells). Need dedicated storage and AnnData processing pipeline. |
| Cross-omics integration | Not designed | No unified schema for joining transcriptomics, proteomics, and metabolomics. Future work: gene-centric join on gene symbol. |
| Data freshness | Static | All datasets are point-in-time snapshots. No automated refresh pipeline. |
