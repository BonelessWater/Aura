# Aura

This repository hosts the Aura platform.

## Aura Platform Blueprint

This document outlines the integrated blueprint for the Aura platform, combining a multimodal user experience, a dual-confidence Retrieval-Augmented Generation (RAG) engine, a community ecosystem, and a local multi-agent architecture.

---

## 1. Patient Intake: Gathering the Odyssey

The user journey begins with a seamless, multimodal onboarding process designed to capture the full scope of hidden symptoms.

- **Longitudinal Labs:**
  - Users upload historical blood work PDFs (CBC, CMP, CRP).
  - The system encourages multiple years of data to establish a baseline.

- **Clinical Interview:**
  - Users type out their symptom history in plain English.

- **Visual Evidence:**
  - Users upload photos of visible physical changes (e.g., rash, joint swelling) or videos demonstrating physical limitations (e.g., restricted mobility).

---

## 2. The Engine: Multi-Agent RAG Architecture

The technical heart of Aura runs locally via vLLM on Ubuntu, ensuring absolute data privacy, avoiding API rate limits, and eliminating medical hallucination.

- **Agent 1: Extractor & Vision Parser**
  - Parses raw PDFs into standardized JSON arrays (e.g., standardizing mg/dL to mmol/L).
  - A local Vision-Language Model translates uploaded photos/videos into clinical keywords (e.g., a photo of a swollen knee becomes "localized edema and erythema").

- **Agent 2: Medical Researcher (RAG Engine)**
  - Takes the combined JSON from Agent 1 and queries a pre-built, local vector database (FAISS or ChromaDB) loaded with thousands of PubMed medical journals.
  - Retrieves exact paragraphs of clinical literature matching the patient's specific lab ratios and visual symptoms.

- **Agent 3: Dual-Scorer (Router)**
  - Evaluates patient data against retrieved research papers to calculate two distinct metrics:
    - **Primary Metric – Category Confidence:** (e.g., 92% Systemic Autoimmune Alignment). High confidence, driven by broad inflammatory trends like elevated NLR and CRP.
    - **Secondary Metric – Disease Confidence:** (e.g., 65% Systemic Lupus Erythematosus Alignment). Lower confidence, highly caveated, driven by specific multimodal flags like a malar rash combined with leukopenia.

- **Agent 4: Translator**
  - Drafts final outputs, strictly citing the DOIs (Digital Object Identifiers) provided by the Medical Researcher.

---

## 3. The Output: Bridging the Specialty Gap

The Translator Agent generates two distinct deliverables, serving both sides of the medical divide.

### Deliverable A: Clinical SOAP Note (For the Doctor)
- A professional, black-and-white document designed for General Practitioners.
- **Objective Data:** Highlights trends in blood work and summarizes visual evidence.
- **Assessment (Dual-Score):**
  - "Data indicates a 92% alignment with a Systemic Autoimmune profile, with secondary literature flags (65%) suggesting a Systemic Lupus Erythematosus etiology."
- **Literature Grounding:**
  - Every claim is backed by a hard citation. E.g., "Sustained CRP elevation combined with localized erythema is highly characteristic of systemic autoimmune escalation. (Source: Journal of Clinical Rheumatology, 2024. DOI: 10.1097/...)"
- **Plan:** Justifies a specific specialist referral.

### Deliverable B: Layman's Compass (For the Patient)
- An empathetic, highly readable dashboard that demystifies their data.
- **Translation:**
  - "Your blood work and photos strongly suggest your immune system is causing systemic inflammation. The research indicates this pattern is often seen in conditions like Lupus, though only a doctor can diagnose you."
- **Next Step:**
  - Gives the patient the exact script to use when handing the SOAP note to their GP.

---

## 4. The Ecosystem: Action & Support

Once the patient has their data, Aura provides the infrastructure to act on it.

- **Geographic Specialist Routing:**
  - Uses "Category Confidence" to filter its directory. If flagged for the Systemic category and located in Atlanta, Aura recommends top-rated, in-network Rheumatologists in the Atlanta metro area specializing in complex diagnostics.

- **Clustered Support Forums:**
  - Users are invited into a moderated community based on Category Confidence (Systemic, Gastrointestinal, or Endocrine).
  - Forums are clustered by category, not specific disease, allowing users to share advice on navigating the diagnostic process without competing medical advice.
  - An NLP layer actively filters out dangerous dosage recommendations or miracle cures.

---

*This blueprint integrates privacy, precision, and community to empower patients and clinicians alike.*
