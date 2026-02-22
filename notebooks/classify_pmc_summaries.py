# Databricks notebook source
# MAGIC %md
# MAGIC # Aura: LLM Classification of PMC-Patients Summaries
# MAGIC
# MAGIC Uses Azure OpenAI (gpt-4o-mini) to:
# MAGIC 1. Extract the diagnosis category from each paper title
# MAGIC 2. Classify each sentence in the patient summary as diagnosis vs preliminary
# MAGIC
# MAGIC Saves progress every 1,000 rows so it can resume after interruptions.
# MAGIC
# MAGIC **Produces:** `pmc_patients_classified` (Tier 2)
# MAGIC
# MAGIC **Source:** `workspace.aura.pmc_patients`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import os
import re
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from openai import AzureOpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("aura_classify_pmc")

VOLUME_ROOT = "/Volumes/workspace/aura/aura_data"
CHECKPOINT_DIR = os.path.join(VOLUME_ROOT, "classify_checkpoints")

AZURE_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AZURE_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI", "gpt-4o-mini")
AZURE_API_VERSION = os.environ.get("OPENAI_API_VERSION", "2024-08-01-preview")

if not AZURE_ENDPOINT or not AZURE_API_KEY:
    raise RuntimeError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set")

client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION,
)

BATCH_SIZE = 1000

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Helper Functions

# COMMAND ----------

def split_into_sentences(text):
    """Split patient summary into numbered sentences.

    Splits on sentence-ending punctuation followed by whitespace.
    Returns list of (line_number, sentence_text) tuples, 1-indexed.
    """
    if not text or pd.isna(text):
        return []
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    return [(i + 1, s) for i, s in enumerate(sentences)]


def format_numbered_lines(sentences):
    """Format sentences as numbered lines for the LLM prompt."""
    return "\n".join(f"{num}: {text}" for num, text in sentences)


def parse_diagnosis_response(response_text):
    """Parse the LLM response for diagnosis extraction from title.

    Expected: a single line with the disease name, or 'none'.
    """
    text = response_text.strip().lower()
    if text in ("none", "n/a", "null", ""):
        return None
    return response_text.strip()


def parse_line_numbers(response_text):
    """Parse comma-separated line numbers from LLM response.

    Expected: '3, 7' or 'none'.
    Returns list of ints.
    """
    text = response_text.strip().lower()
    if text in ("none", "n/a", "null", ""):
        return []
    numbers = re.findall(r'\d+', text)
    return [int(n) for n in numbers]


def classify_row(title, patient_summary):
    """Call Azure OpenAI to classify one patient row.

    Returns dict with:
      - diagnosis: str or None (from title)
      - diagnosis_lines: list[int] (sentence numbers with diagnosis info)
      - preliminary_lines: list[int] (sentence numbers with presentation info)
    """
    sentences = split_into_sentences(patient_summary)
    if not sentences:
        return {
            "diagnosis": None,
            "diagnosis_lines": [],
            "preliminary_lines": [],
        }

    numbered = format_numbered_lines(sentences)
    all_line_nums = [num for num, _ in sentences]

    prompt = (
        f"Title: {title}\n\n"
        f"Lines:\n{numbered}\n\n"
        "Q1: What disease is this about? One phrase or none.\n"
        "Q2: Which line numbers mention the diagnosis? Numbers only or none."
    )

    try:
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You classify medical case reports. "
                        "Answer Q1 with just the disease name or none. "
                        "Answer Q2 with just comma-separated line numbers or none. "
                        "Reply with exactly two lines, nothing else."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=60,
        )
        reply = response.choices[0].message.content.strip()
        lines = reply.split("\n")

        diagnosis = parse_diagnosis_response(lines[0]) if len(lines) >= 1 else None
        diag_lines = parse_line_numbers(lines[1]) if len(lines) >= 2 else []

        diag_set = set(diag_lines)
        prelim_lines = [n for n in all_line_nums if n not in diag_set]

        return {
            "diagnosis": diagnosis,
            "diagnosis_lines": diag_lines,
            "preliminary_lines": prelim_lines,
        }

    except Exception as exc:
        try:
            time.sleep(2)
            response = client.chat.completions.create(
                model=AZURE_DEPLOYMENT,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You classify medical case reports. "
                            "Answer Q1 with just the disease name or none. "
                            "Answer Q2 with just comma-separated line numbers or none. "
                            "Reply with exactly two lines, nothing else."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=60,
            )
            reply = response.choices[0].message.content.strip()
            lines = reply.split("\n")
            diagnosis = parse_diagnosis_response(lines[0]) if len(lines) >= 1 else None
            diag_lines = parse_line_numbers(lines[1]) if len(lines) >= 2 else []
            diag_set = set(diag_lines)
            prelim_lines = [n for n in all_line_nums if n not in diag_set]
            return {
                "diagnosis": diagnosis,
                "diagnosis_lines": diag_lines,
                "preliminary_lines": prelim_lines,
            }
        except Exception as retry_exc:
            logger.error("LLM call failed (after retry) for title='%s': %s", title[:60], retry_exc)
            return {
                "diagnosis": None,
                "diagnosis_lines": [],
                "preliminary_lines": [],
            }


def build_text_from_lines(sentences, line_numbers):
    """Reconstruct text from selected sentence numbers."""
    sentence_map = {num: text for num, text in sentences}
    parts = [sentence_map[n] for n in sorted(line_numbers) if n in sentence_map]
    return " ".join(parts) if parts else ""


# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Checkpoint Helpers

# COMMAND ----------

def get_completed_patient_ids():
    """Load patient_ids already processed from checkpoint parquets."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    done = set()
    for fname in os.listdir(CHECKPOINT_DIR):
        if fname.endswith(".parquet"):
            try:
                chunk = pd.read_parquet(os.path.join(CHECKPOINT_DIR, fname))
                done.update(chunk["patient_id"].tolist())
            except Exception as exc:
                logger.error("Bad checkpoint %s: %s", fname, exc)
    return done


def save_checkpoint(batch_df, batch_num):
    """Save a batch of classified rows as a checkpoint parquet."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    path = os.path.join(CHECKPOINT_DIR, f"batch_{batch_num:05d}.parquet")
    batch_df.to_parquet(path, index=False, coerce_timestamps="us", allow_truncated_timestamps=True)
    logger.info("Checkpoint saved: %s (%d rows)", path, len(batch_df))


def merge_checkpoints(df_source):
    """Merge all checkpoint parquets into the final output."""
    parts = []
    for fname in sorted(os.listdir(CHECKPOINT_DIR)):
        if fname.endswith(".parquet"):
            parts.append(pd.read_parquet(os.path.join(CHECKPOINT_DIR, fname)))
    if not parts:
        logger.error("No checkpoint files found to merge")
        return None
    merged = pd.concat(parts, ignore_index=True)
    # Drop duplicates in case of overlapping checkpoints
    merged = merged.drop_duplicates(subset=["patient_id"], keep="last")
    logger.info("Merged %d checkpoint files -> %d rows", len(parts), len(merged))
    return merged


# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Process All Patients (with checkpointing)

# COMMAND ----------

def classify_batch(batch_df, max_workers=64):
    """Classify a batch of rows using parallel LLM calls.

    Returns a DataFrame with classification columns added.
    """
    results = {}
    errors = 0

    def process_row(patient_id, title, summary):
        return patient_id, classify_row(title, summary)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for _, row in batch_df.iterrows():
            f = executor.submit(process_row, row["patient_id"], row["title"], row["patient_summary"])
            futures[f] = row["patient_id"]

        for future in as_completed(futures):
            try:
                pid, result = future.result()
                results[pid] = result
            except Exception as exc:
                errors += 1
                pid = futures[future]
                results[pid] = {
                    "diagnosis": None,
                    "diagnosis_lines": [],
                    "preliminary_lines": [],
                }
                logger.error("Row %s failed: %s", pid, exc)

    # Build output columns
    out = batch_df.copy()
    out["diagnosis"] = out["patient_id"].map(lambda pid: results.get(pid, {}).get("diagnosis"))
    out["diagnosis_lines"] = out["patient_id"].map(
        lambda pid: json.dumps(results.get(pid, {}).get("diagnosis_lines", []))
    )
    out["preliminary_lines"] = out["patient_id"].map(
        lambda pid: json.dumps(results.get(pid, {}).get("preliminary_lines", []))
    )

    diag_texts = []
    prelim_texts = []
    for _, row in out.iterrows():
        sentences = split_into_sentences(row["patient_summary"])
        r = results.get(row["patient_id"], {"diagnosis_lines": [], "preliminary_lines": []})
        diag_texts.append(build_text_from_lines(sentences, r["diagnosis_lines"]))
        prelim_texts.append(build_text_from_lines(sentences, r["preliminary_lines"]))

    out["diagnosis_text"] = diag_texts
    out["preliminary_text"] = prelim_texts

    output_cols = [
        "patient_id", "pmid", "title",
        "diagnosis", "diagnosis_lines", "preliminary_lines",
        "diagnosis_text", "preliminary_text",
        "patient_summary", "age_years", "sex", "pub_date",
    ]
    output_cols = [c for c in output_cols if c in out.columns]

    for col in out.select_dtypes(include=["datetime64[ns]"]).columns:
        out[col] = out[col].dt.floor("us")

    return out[output_cols], errors


def classify_pmc_summaries():
    """Classify all pmc_patients rows, saving progress every BATCH_SIZE rows."""
    dest = os.path.join(VOLUME_ROOT, "tier2_pmc_patients_classified.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete to re-run.", dest)
        return pd.read_parquet(dest)

    src = os.path.join(VOLUME_ROOT, "tier1_pmc_patients.parquet")
    if not os.path.exists(src):
        logger.error("Source not found: %s", src)
        return None

    logger.info("Loading pmc_patients...")
    df = pd.read_parquet(src)
    logger.info("Loaded %d rows", len(df))

    # Check what is already done
    done_ids = get_completed_patient_ids()
    remaining = df[~df["patient_id"].isin(done_ids)]
    logger.info("Already classified: %d | Remaining: %d", len(done_ids), len(remaining))

    if len(remaining) == 0:
        logger.info("All rows already classified. Merging checkpoints...")
        merged = merge_checkpoints(df)
        merged.to_parquet(dest, index=False, coerce_timestamps="us", allow_truncated_timestamps=True)
        logger.info("Final output saved: %s (%d rows)", dest, len(merged))
        return merged

    # Process in batches
    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE
    start_batch = len(done_ids) // BATCH_SIZE
    start_time = time.time()
    total_errors = 0

    for i in range(0, len(remaining), BATCH_SIZE):
        batch_num = start_batch + (i // BATCH_SIZE)
        batch_df = remaining.iloc[i:i + BATCH_SIZE]
        batch_start = time.time()

        logger.info(
            "Batch %d/%d (%d rows) starting...",
            batch_num + 1, start_batch + total_batches, len(batch_df),
        )

        classified_batch, batch_errors = classify_batch(batch_df)
        total_errors += batch_errors
        save_checkpoint(classified_batch, batch_num)

        batch_elapsed = time.time() - batch_start
        total_elapsed = time.time() - start_time
        rows_done = i + len(batch_df)
        rate = rows_done / total_elapsed if total_elapsed > 0 else 0
        eta = (len(remaining) - rows_done) / rate / 60 if rate > 0 else 0

        logger.info(
            "Batch %d done in %.0fs | Total: %d/%d (%.1f%%) | %.1f rows/s | ETA: %.0f min | Errors: %d",
            batch_num + 1, batch_elapsed,
            len(done_ids) + rows_done, len(df),
            100 * (len(done_ids) + rows_done) / len(df),
            rate, eta, total_errors,
        )

    # Merge all checkpoints into final output
    logger.info("All batches complete. Merging checkpoints...")
    merged = merge_checkpoints(df)
    merged.to_parquet(dest, index=False, coerce_timestamps="us", allow_truncated_timestamps=True)
    logger.info("Final output saved: %s (%d rows)", dest, len(merged))

    n_diagnosed = merged["diagnosis"].notna().sum()
    logger.info("Diagnosed: %d / %d (%.1f%%)",
                n_diagnosed, len(merged), 100 * n_diagnosed / max(len(merged), 1))
    logger.info("Top diagnoses:\n%s",
                merged["diagnosis"].value_counts().head(20).to_string())

    return merged


output_df = classify_pmc_summaries()
if output_df is not None:
    n = output_df["diagnosis"].notna().sum()
    logger.info("Done: %d total, %d with diagnosis", len(output_df), n)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Register Table

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.pmc_patients_classified
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier2_pmc_patients_classified.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT diagnosis, COUNT(*) as cases
# MAGIC FROM workspace.aura.pmc_patients_classified
# MAGIC WHERE diagnosis IS NOT NULL
# MAGIC GROUP BY diagnosis
# MAGIC ORDER BY cases DESC
# MAGIC LIMIT 30;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Verify: sample classified rows
# MAGIC SELECT patient_id, diagnosis,
# MAGIC        SUBSTRING(preliminary_text, 1, 300) as preliminary_preview,
# MAGIC        SUBSTRING(diagnosis_text, 1, 200) as diagnosis_preview
# MAGIC FROM workspace.aura.pmc_patients_classified
# MAGIC WHERE diagnosis IS NOT NULL
# MAGIC LIMIT 5;
