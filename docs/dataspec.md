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

---

## 2. Epidemiological Baseline and Population Norms

### NHANES (National Health and Nutrition Examination Survey)
*   **Description**: Large-scale US population health survey with continuous cycles.
*   **Host**: CDC NCHS
*   **Direct Link**: [https://wwwn.cdc.gov/nchs/nhanes/](https://wwwn.cdc.gov/nchs/nhanes/)
*   **Key Features**: ANA status, CBC (WBC, Lymphocytes, Monocytes, Neutrophils, Eosinophils, Basophils, RDW, MPV).
*   **Format**: SAS Transport Files (.XPT)
*   **License**: Public Domain
*   **Protocol**: Download via "Questionnaires, Datasets, and Related Documentation" directory. Use `pd.read_sas()` in Python.

---

## 3. Population-Scale Genetic and Clinical Repositories

### Autoimmune Disease Knowledge Portal (Shigesi 2025 & Million Veterans)
*   **Description**: Aggregated large-scale GWAS and clinical phenotyping datasets.
    *   *Shigesi 2025*: 654,677 samples (Immunological diseases, EU ancestry).
    *   *Million Veterans Program*: 632,310 samples (Trans-ancestry GWAS).
*   **Scale**: 1,286,987 total samples.
*   **Host**: HugeAmp (Broad Institute / UCSD)
*   **Direct Link**: [https://hugeamp.org/](https://hugeamp.org/)
*   **Key Features**: Clinical phenotype mapping, genetic risk scores, immunological health markers.
*   **Format**: Tabular / API
*   **License**: Open Access / Consortium Use
*   **Protocol**: Query via the GraphQL API or direct portal download for specific phenotype/genotype matrices.

### FinnGen (Data Release R12)
*   **Description**: Nationwide Finnish cohort linking biobank samples to longitudinal digital health record registries.
*   **Scale**: 520,348 participants.
*   **Host**: University of Helsinki / FinnGen Consortium
*   **Direct Link**: [https://www.finngen.fi/en](https://www.finngen.fi/en)
*   **Key Features**: Clinical endpoints for autoimmune diseases (ICD codes), longitudinal health registries, genotype data.
*   **Format**: Phenotype matrices (Tabular), VCF
*   **License**: FinnGen Data Use Agreement (Research level)
*   **Protocol**: Access via the Sandbox environment or public summary statistics for preliminary weight training.

---

## 4. Pharmacological and Targeted Molecular Datasets

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

### Open Targets Platform
*   **Description**: Target-disease association scores aggregated from 22 evidence sources (genetic associations, known drugs, differential expression, animal models, pathways). Autoimmune diseases deeply indexed.
*   **Host**: EMBL-EBI / Wellcome Sanger Institute
*   **Direct Link**: [https://platform.opentargets.org](https://platform.opentargets.org)
*   **Key Features**: Drug-target evidence, genetic validation scores, pathway annotations, mouse model phenotypes for autoimmune targets.
*   **Format**: Parquet / JSON (bulk download), REST API
*   **License**: Open Access
*   **Protocol**: Bulk download via [AWS Open Data Registry](https://registry.opendata.aws/opentargets/) or query via GraphQL API.

---

## 5. Transcriptomics and Epigenomics

### ADEx (Autoimmune Diseases Explorer)
*   **Description**: 82 curated transcriptomics and methylation studies covering 5,609 samples across SLE, RA, Sjogren's syndrome, systemic sclerosis, and type 1 diabetes. All data sourced from NCBI-GEO and manually harmonized.
*   **Host**: GENYO (Centre for Genomics and Oncological Research, Spain)
*   **Direct Link**: [https://adex.genyo.es](https://adex.genyo.es)
*   **Key Features**: Processed gene expression matrices, DNA methylation beta values, clinical metadata, differential expression and pathway analysis tools.
*   **Format**: Compressed text files (expression/methylation matrices)
*   **License**: Open Access
*   **Protocol**: Select diseases and datasets via web interface, download processed matrices as compressed folders.

### IAAA (Interactive Analysis and Atlas for Autoimmune Disease)
*   **Description**: Integrated atlas combining 929 bulk RNA-seq peripheral blood samples across 10 autoimmune diseases with 783,203 single cells from 96 samples across 6 diseases (Crohn's, MS, RA, Sjogren's, SLE, systemic sclerosis, UC).
*   **Host**: NCBI / Published resource
*   **Direct Link**: See [PMC9235372](https://pmc.ncbi.nlm.nih.gov/articles/PMC9235372/) for access details.
*   **Key Features**: Bulk and single-cell transcriptomic profiles, cell-type deconvolution signatures, cross-disease gene expression comparisons.
*   **Format**: Processed matrices
*   **License**: Open Access
*   **Protocol**: Download via links in the publication supplementary materials.

---

## 6. Single-Cell Immune Atlases

### Human Cell Atlas -- Autoimmune Single-Cell eQTL Project
*   **Description**: 1,267,758 PBMCs from 982 subjects with single-cell eQTL mapping to autoimmune GWAS loci. Identifies which immune cell types drive genetic risk for autoimmune diseases.
*   **Host**: Human Cell Atlas Data Explorer
*   **Direct Link**: [https://explore.data.humancellatlas.org/projects/f2078d5f-2e7d-4844-8552-f7c41a231e52](https://explore.data.humancellatlas.org/projects/f2078d5f-2e7d-4844-8552-f7c41a231e52)
*   **Key Features**: Cell-type-resolved genetic effect sizes, PBMC subset proportions, eQTL-GWAS colocalization results.
*   **Format**: HDF5 / AnnData / Loom
*   **License**: CC BY 4.0
*   **Protocol**: Download via HCA Data Explorer portal.

### Allen Institute Immune Health Atlas
*   **Description**: 16+ million single cells from 108 healthy donors spanning pediatric, young adult, and older adult cohorts. Defines age-stratified immune cell reference ranges at single-cell resolution.
*   **Host**: Allen Institute for Immunology
*   **Direct Link**: [https://apps.allenimmunology.org/aifi/resources/imm-health-atlas/](https://apps.allenimmunology.org/aifi/resources/imm-health-atlas/)
*   **Key Features**: Age-stratified PBMC subset frequencies, single-cell gene expression profiles, healthy immune baseline.
*   **Format**: AnnData / H5AD
*   **License**: Open Access
*   **Protocol**: Download via the Allen Institute portal or CZ CELLxGENE.

---

## 7. Gut Microbiome

### Human Microbiome Project (HMP)
*   **Description**: NIH-funded reference microbiome dataset from 300 healthy adults across 18 body sites, plus disease cohort samples. 16S and whole metagenome shotgun sequencing.
*   **Host**: NIH Common Fund / AWS
*   **Direct Link**: [https://registry.opendata.aws/human-microbiome-project/](https://registry.opendata.aws/human-microbiome-project/)
*   **Key Features**: 16S rRNA profiles, whole metagenome assemblies, metabolic pathway reconstructions, healthy population microbiome baseline.
*   **Format**: FASTQ / BIOM / TSV
*   **License**: Public Domain
*   **Protocol**: Direct download from AWS S3 bucket `s3://human-microbiome-project`.

---

## 8. Expanded Genetics and GWAS

### NHGRI-EBI GWAS Catalog -- Full Summary Statistics
*   **Description**: 625,113+ curated SNP-trait associations from published GWAS. Full genome-wide summary statistics available for 66% of cataloged studies (~56 TB total). Autoimmune diseases are among the most heavily represented trait categories.
*   **Scale**: 7,400+ curated publications, 1,040,000+ SNP-trait associations.
*   **Host**: EMBL-EBI / NHGRI
*   **Direct Link**: [https://www.ebi.ac.uk/gwas/](https://www.ebi.ac.uk/gwas/)
*   **Key Features**: Per-variant effect sizes, p-values, allele frequencies for autoimmune phenotypes. Enables polygenic risk score construction.
*   **Format**: TSV (per-study summary statistics)
*   **License**: Open Access
*   **Protocol**: Browse by trait (e.g. "rheumatoid arthritis"), download full summary stats from [summary statistics portal](https://www.ebi.ac.uk/gwas/labs/downloads/summary-statistics).

### Pan-UK Biobank GWAS Summary Statistics
*   **Description**: GWAS summary statistics for 7,266 traits across 6 ancestry groups in 500K UK Biobank participants. All autoimmune phenotypes included. No UK Biobank application required for these summary stats.
*   **Host**: Broad Institute / AWS
*   **Direct Link**: [https://pan.ukbb.broadinstitute.org/downloads/](https://pan.ukbb.broadinstitute.org/downloads/)
*   **Key Features**: Pan-ancestry effect sizes, per-population allele frequencies, heritability estimates, LD score regression results.
*   **Format**: TSV / Hail
*   **License**: CC BY 4.0
*   **Protocol**: Download per-phenotype flat files directly from AWS S3 using the phenotype manifest.

### Allele Frequency Net Database (AFND)
*   **Description**: HLA allele and haplotype frequencies from 1,505 worldwide populations (10M+ individuals). Includes KIR-disease association database with autoimmune disorder records.
*   **Host**: Royal College of Pathologists / Allele Frequency Net
*   **Direct Link**: [https://www.allelefrequencies.net](https://www.allelefrequencies.net)
*   **Key Features**: Population-stratified HLA-A, -B, -C, -DRB1, -DQB1 frequencies; KIR-disease associations for autoimmune conditions.
*   **Format**: Tabular (web export) / programmatic via Python
*   **License**: Open Access
*   **Protocol**: Use `HLAfreq` Python package for programmatic download and combination of population datasets.

### ImmunoBase -- Autoimmune Fine-Mapping Credible Sets
*   **Description**: Summary statistics from published Immunochip studies with fine-mapping credible sets for autoimmune loci. Covers celiac disease, autoimmune thyroiditis, primary biliary cirrhosis, RA, and more. A catalog of 85 studies with 230 fine-mapped GWAS loci.
*   **Host**: University of Cambridge / Wellcome Trust
*   **Direct Link**: [http://www.immunobase.org](http://www.immunobase.org)
*   **Key Features**: Credible variant sets (some mapped to 5 or fewer variants), allelic heterogeneity estimates, causal variant predictions.
*   **Format**: Tabular
*   **License**: Open Access
*   **Protocol**: Download Immunochip summary statistics per disease from the portal.

---

## 9. Proteomics

### Olink Insight / UK Biobank Pharma Proteomics Project (UKB-PPP)
*   **Description**: 300,000+ protein-disease risk associations across 106 diseases derived from Olink Explore 3072 profiling of 50,000+ UK Biobank participants. Largest population-scale plasma proteomics study to date.
*   **Host**: Olink / UK Biobank Consortium
*   **Direct Link**: [https://olink.com/olink-insight/](https://olink.com/olink-insight/)
*   **Key Features**: Protein-disease association scores, plasma protein quantification (NPX values), disease risk effect sizes for autoimmune conditions.
*   **Format**: Web-based query / downloadable results
*   **License**: Open Access (Olink Insight platform)
*   **Protocol**: Query disease-protein associations via the Olink Insight web tool. UKB-PPP summary data available via linked publications.

### Human Protein Atlas v25 -- Disease Blood Atlas
*   **Description**: Plasma proteomics profiling across 32 disease cohorts covering 71 diseases (including autoimmune conditions) using both Olink HT and SomaScan platforms.
*   **Host**: Human Protein Atlas Consortium
*   **Direct Link**: [https://www.proteinatlas.org](https://www.proteinatlas.org)
*   **Key Features**: Cross-platform validated protein biomarkers, disease-specific protein expression profiles, blood cell type protein expression.
*   **Format**: TSV (bulk download), interactive web atlas
*   **License**: CC BY-SA 3.0
*   **Protocol**: Bulk download via [https://www.proteinatlas.org/about/download](https://www.proteinatlas.org/about/download) or query individual proteins/diseases via web interface.

---

## 10. Metabolomics

### Serum Metabolome Database (HMDB)
*   **Description**: 4,651 small molecule metabolites with 10,895 concentration values in human serum, linked to disease associations. Part of the broader Human Metabolome Database (220,000+ metabolite entries).
*   **Host**: University of Alberta
*   **Direct Link**: [https://serummetabolome.ca](https://serummetabolome.ca) / [https://hmdb.ca](https://hmdb.ca)
*   **Key Features**: Normal and abnormal metabolite concentration ranges, disease-metabolite associations, metabolic pathway mapping.
*   **Format**: XML / CSV (bulk download), REST API
*   **License**: Open Access
*   **Protocol**: Bulk download metabolite data from HMDB, or query disease-specific metabolite panels via search interface.

### MetaboLights (EMBL-EBI)
*   **Description**: Global repository of raw metabolomics study data across 6,815+ studies. Contains autoimmune-specific metabolomics studies (SLE, RA, IBD serum/plasma metabolomics).
*   **Host**: EMBL-EBI
*   **Direct Link**: [https://www.ebi.ac.uk/metabolights/](https://www.ebi.ac.uk/metabolights/)
*   **Key Features**: Raw and processed metabolomics data, study metadata, sample annotations with disease labels.
*   **Format**: Study-dependent (mzML, CSV, ISA-Tab)
*   **License**: Open Access
*   **Protocol**: Search by disease term, download per-study data packages.

---

## 11. Patient-Reported Outcomes

### Flaredown Autoimmune Symptom Tracker
*   **Description**: Real-world patient-reported data from 1,700+ chronic illness patients across 57 countries. Daily longitudinal tracking of symptom severity, treatments and doses, and environmental triggers (foods, stress, allergens). Users report ~8 conditions on average, reflecting real-world comorbidity patterns.
*   **Host**: Kaggle
*   **Direct Link**: [https://www.kaggle.com/datasets/flaredown/flaredown-autoimmune-symptom-tracker](https://www.kaggle.com/datasets/flaredown/flaredown-autoimmune-symptom-tracker)
*   **Key Features**: Daily symptom severity scores, treatment-response correlations, trigger-flare temporal patterns, multi-condition comorbidity data.
*   **Format**: CSV
*   **License**: Open (Kaggle)
*   **Protocol**: `kaggle datasets download -d flaredown/flaredown-autoimmune-symptom-tracker`

---

## 12. Environmental Exposure Covariates

### Comparative Toxicogenomics Database (CTD)
*   **Description**: Manually curated chemical-gene-disease interaction database linking environmental chemicals to autoimmune disease pathways. Enables environmental risk factor modeling.
*   **Host**: NC State University / Mount Desert Island Biological Laboratory
*   **Direct Link**: [https://ctdbase.org](https://ctdbase.org)
*   **Key Features**: Chemical-gene interactions, chemical-disease associations, gene-disease associations, enriched pathway data for autoimmune conditions.
*   **Format**: TSV / XML (bulk download), REST API
*   **License**: Open Access
*   **Protocol**: Bulk download from [https://ctdbase.org/downloads/](https://ctdbase.org/downloads/) or query via batch search tools.

### EPA Air Quality System (AQS) Data
*   **Description**: Historical and current air quality measurements (PM2.5, PM10, ozone, NO2, SO2) by monitoring station, location, and date across the US. Published research links long-term PM2.5 exposure to increased risk of RA, connective tissue diseases, and IBD.
*   **Host**: US EPA
*   **Direct Link**: [https://www.epa.gov/aqs](https://www.epa.gov/aqs)
*   **Key Features**: Daily/annual pollutant concentrations by geographic coordinates, temporal trends, county-level aggregations.
*   **Format**: CSV / API
*   **License**: Public Domain
*   **Protocol**: Download pre-generated data files from [https://aqs.epa.gov/aqsweb/airdata/download_files.html](https://aqs.epa.gov/aqsweb/airdata/download_files.html) or query via AQS API.