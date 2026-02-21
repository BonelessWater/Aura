# Aura: Autoimmune Risk Analysis - Data Acquisition Specification

This specification outlines the key data sources required for training the Aura bio-fingerprinting triage engine.

## 1. Primary Supervised Autoimmune Feature Matrices

### Diagnosis of Rheumatic and Autoimmune Diseases (Harvard Dataverse)
*   **Description**: 12,085 de-identified records (RA, AS, Sjögren's, PsA, SLE, Reactive Arthritis, and controls).
*   **Host**: Harvard Dataverse
*   **Direct Link**: [https://doi.org/10.7910/DVN/VM4OR3](https://doi.org/10.7910/DVN/VM4OR3)
*   **Key Features**: ESR, CRP, C3, C4, RF, Anti-CCP, ANA, anti-dsDNA, HLA-B27, anti-SM, anti-Ro, anti-La.
*   **Format**: Excel/CSV
*   **License**: CC BY
*   **Protocol**: Direct download via DOI link.

### Comprehensive Autoimmune Disorder Dataset (Kaggle)
*   **Description**: 12,500 records linking CBC metrics to autoimmune outcomes and illness duration.
*   **Host**: Kaggle
*   **Direct Link**: [kaggle.com/datasets/abdullahragheb/all-autoimmune-disorder-10k](https://www.kaggle.com/datasets/abdullahragheb/all-autoimmune-disorder-10k)
*   **Key Features**: Age, Gender, Illness Duration, RBC, Hemoglobin, Hematocrit, MCV, MCH.
*   **Format**: CSV (3.35 MB)
*   **License**: MIT
*   **Protocol**: `kaggle datasets download -d abdullahragheb/all-autoimmune-disorder-10k`

---

## 2. Gastrointestinal Cluster Specialization

### Gastrointestinal Disease Dataset (Kaggle)
*   **Description**: 30,560 records for identifying structural GI autoimmunity (IBD) vs. functional distress.
*   **Host**: Kaggle
*   **Direct Link**: [kaggle.com/datasets/amanik000/gastrointestinal-disease-dataset](https://www.kaggle.com/datasets/amanik000/gastrointestinal-disease-dataset)
*   **Key Features**: Age, Gender, Weight, BMI, CRP/ESR, Fecal Calprotectin.
*   **Format**: CSV
*   **License**: CC BY 4.0
*   **Protocol**: Direct download via Kaggle API or web interface.

---

## 3. Epidemiological Baseline and Population Norms

### NHANES (National Health and Nutrition Examination Survey)
*   **Description**: Large-scale US population health survey with continuous cycles.
*   **Host**: CDC NCHS
*   **Direct Link**: [https://wwwn.cdc.gov/nchs/nhanes/](https://wwwn.cdc.gov/nchs/nhanes/)
*   **Key Features**: ANA status, CBC (WBC, Lymphocytes, Monocytes, Neutrophils, Eosinophils, Basophils, RDW, MPV).
*   **Format**: SAS Transport Files (.XPT)
*   **License**: Public Domain
*   **Protocol**: Download via "Questionnaires, Datasets, and Related Documentation" directory. Use `pd.read_sas()` in Python.

### ImmPort 10,000 Immunomes Project (10KIP)
*   **Description**: Harmonized baseline of 10,344 healthy subjects for reference thresholds.
*   **Host**: ImmPort (NIAID)
*   **Direct Link**: [http://10kimmunomes.org/](http://10kimmunomes.org/)
*   **Key Features**: CBC, CMP, Lipid Profiles, Clinical Lab Tests.
*   **Format**: TSV/CSV/SQL
*   **License**: ImmPort DUA (Registration required)
*   **Protocol**: Register at ImmPort portal, accept DUA, then download via portal or GA4GH DRS API.

---

## 4. Longitudinal and Critical Care records (EHR)

### MIMIC-IV
*   **Description**: High-resolution longitudinal hospital data from Beth Israel Deaconess Medical Center (2008–2019).
*   **Host**: PhysioNet (MIT)
*   **Direct Link**: [https://physionet.org/content/mimiciv/](https://physionet.org/content/mimiciv/)
*   **Key Features**: Time-series lab events (labevents), demographics, medications.
*   **Format**: CSV / BigQuery
*   **License**: PhysioNet Credentialed Health Data License 1.5.0 (Requires CITI training)
*   **Protocol**: 5-step credentialing (PhysioNet profile -> CITI training -> Application -> DUA signature).

### eICU Collaborative Research Database
*   **Description**: Multi-center ICU database with 200,000+ admissions.
*   **Host**: PhysioNet / Philips
*   **Direct Link**: [https://physionet.org/content/eicu-crd/](https://physionet.org/content/eicu-crd/)
*   **Key Features**: Metabolic markers (BUN, magnesium, pH), lab offsets.
*   **Format**: CSV / PostgreSQL
*   **License**: PhysioNet Credentialed Health Data License.
*   **Protocol**: Same credentialing process as MIMIC-IV.

---

## 5. Synthetic Patient Generation

### Synthea
*   **Description**: Open-source patient population simulator for modeling rare/overlapping disease states.
*   **Host**: SyntheticMass (MITRE) / GitHub
*   **Direct Link**: [https://synthea.mitre.org/downloads](https://synthea.mitre.org/downloads)
*   **Key Features**: FHIR-based medical histories, custom disease modules.
*   **Format**: FHIR, C-CDA, CSV
*   **License**: Apache 2.0
*   **Protocol**: Download pre-generated cohorts or clone from `github.com/synthetichealth/synthea`.

---

## 6. Pharmacological and Molecular Datasets

### Drug-Induced Autoimmunity Prediction (UCI)
*   **Description**: Molecular descriptors for predicting autoimmune mimicry from medications.
*   **Host**: UCI Machine Learning Repository
*   **Direct Link**: [https://archive.ics.uci.edu/dataset/1104/drug_induced_autoimmunity_prediction](https://archive.ics.uci.edu/dataset/1104/drug_induced_autoimmunity_prediction)
*   **Key Features**: 195 physicochemical drug properties.
*   **Format**: Tabular
*   **License**: Standard UCI open-access
*   **Protocol**: Direct download or `ucimlrepo` Python library.

### Targeted Lipidomics and Flow Cytometry (Mendeley Data)
*   **Description**: Deep molecular subsets for validating structural immune dysregulation.
*   **Host**: Mendeley Data
*   **Direct Link**: [https://data.mendeley.com/datasets/m2p6rr9v36/1](https://data.mendeley.com/datasets/m2p6rr9v36/1)
*   **Key Features**: Plasma lipidomics, lymphocyte subset flow cytometry (IL-17, systemic sclerosis).
*   **Format**: CSV
*   **License**: CC BY 4.0
*   **Protocol**: Open access via DOI.