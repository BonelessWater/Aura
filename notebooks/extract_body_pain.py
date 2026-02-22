# Databricks notebook source
# MAGIC %md
# MAGIC # Aura: Body-Part and Pain-Level Extraction from PMC-Patients
# MAGIC
# MAGIC Uses Azure OpenAI (gpt-4.1-mini) to extract body-part / pain-level pairs
# MAGIC from patient summaries.
# MAGIC
# MAGIC Saves progress every 1,000 rows so it can resume after interruptions.
# MAGIC
# MAGIC **Produces:** `pmc_patients_body_pain` (Tier 2)
# MAGIC
# MAGIC **Source:** `workspace.aura.pmc_patients`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import os
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
logger = logging.getLogger("aura_extract_body_pain")

VOLUME_ROOT = "/Volumes/workspace/aura/aura_data"
CHECKPOINT_DIR = os.path.join(VOLUME_ROOT, "body_pain_checkpoints")

AZURE_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AZURE_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT_GPT41_MINI", "gpt-4.1-mini")
AZURE_API_VERSION = os.environ.get("OPENAI_API_VERSION", "2024-08-01-preview")

if not AZURE_ENDPOINT or not AZURE_API_KEY:
    raise RuntimeError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set")

client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION,
)

BATCH_SIZE = 1000

VALID_PAIN_LEVELS = {"mild", "moderate", "severe"}

SYSTEM_PROMPT = (
    "You extract body-part and pain-level information from medical case reports. "
    "For each mention of pain, discomfort, ache, tenderness, or soreness in the text, identify:\n"
    "1. body_part: the anatomical location (e.g. \"right knee\", \"lower back\", \"abdomen\")\n"
    "2. pain_level: classify as \"mild\", \"moderate\", or \"severe\"\n\n"
    "Classification guidance for pain_level:\n"
    "- \"mild\": described as mild, slight, minor, intermittent without distress, "
    "or managed with OTC medication\n"
    "- \"moderate\": described as moderate, persistent, recurrent, requiring prescription "
    "medication, or causing functional limitation\n"
    "- \"severe\": described as severe, intense, acute, excruciating, debilitating, "
    "or requiring emergency intervention\n\n"
    "If no pain, discomfort, ache, tenderness, or soreness is mentioned, return an empty JSON array.\n"
    "Reply with ONLY a JSON array. No other text.\n\n"
    "Example output:\n"
    '[{"body_part": "right knee", "pain_level": "moderate"}, '
    '{"body_part": "lower back", "pain_level": "severe"}]\n'
    "If no pain: []"
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Helper Functions

# COMMAND ----------


def parse_body_pain_response(response_text):
    """Parse LLM response into list of body-part/pain-level dicts.

    Expected: a JSON array of objects with 'body_part' and 'pain_level' keys.
    Returns list of validated dicts. Invalid entries are dropped with a warning.
    """
    text = response_text.strip()

    # Handle markdown code fences the model sometimes emits
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()

    if text.lower() in ("none", "n/a", "null", "", "[]"):
        return []

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON from LLM response: %s", text[:200])
        return []

    # If model wrapped in an object, try to extract the array
    if isinstance(data, dict):
        for key in ("extractions", "results", "pain_data", "data"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            logger.warning("LLM returned JSON object without known list key: %s", text[:200])
            return []

    if not isinstance(data, list):
        logger.warning("LLM response is not a JSON array: %s", text[:200])
        return []

    validated = []
    for item in data:
        if not isinstance(item, dict):
            continue
        bp = item.get("body_part", "").strip()
        pl = item.get("pain_level", "").strip().lower()
        if bp and pl in VALID_PAIN_LEVELS:
            validated.append({"body_part": bp, "pain_level": pl})
        else:
            logger.warning("Dropping invalid extraction: body_part=%r, pain_level=%r", bp, pl)

    return validated


def extract_body_pain_row(patient_summary):
    """Call Azure OpenAI to extract body-part/pain-level pairs from one summary.

    Returns list of dicts: [{"body_part": str, "pain_level": str}, ...]
    """
    if not patient_summary or pd.isna(patient_summary):
        return []

    text = patient_summary[:3000]
    prompt = f"Patient summary:\n{text}"

    try:
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=300,
        )
        reply = response.choices[0].message.content.strip()
        return parse_body_pain_response(reply)

    except Exception as exc:
        try:
            time.sleep(2)
            response = client.chat.completions.create(
                model=AZURE_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=300,
            )
            reply = response.choices[0].message.content.strip()
            return parse_body_pain_response(reply)
        except Exception as retry_exc:
            logger.error(
                "LLM call failed (after retry) for summary starting '%s': %s",
                patient_summary[:60], retry_exc,
            )
            return []


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
    """Save a batch of extracted rows as a checkpoint parquet."""
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

def extract_batch(batch_df, max_workers=64):
    """Extract body-pain pairs for a batch using parallel LLM calls.

    Returns a DataFrame with extraction columns added.
    """
    results = {}
    errors = 0

    def process_row(patient_id, summary):
        return patient_id, extract_body_pain_row(summary)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for _, row in batch_df.iterrows():
            f = executor.submit(process_row, row["patient_id"], row["patient_summary"])
            futures[f] = row["patient_id"]

        for future in as_completed(futures):
            try:
                pid, result = future.result()
                results[pid] = result
            except Exception as exc:
                errors += 1
                pid = futures[future]
                results[pid] = []
                logger.error("Row %s failed: %s", pid, exc)

    out = batch_df.copy()
    out["body_pain_extractions"] = out["patient_id"].map(
        lambda pid: json.dumps(results.get(pid, []))
    )
    out["body_pain_count"] = out["patient_id"].map(
        lambda pid: len(results.get(pid, []))
    )

    output_cols = [
        "patient_id", "pmid", "title",
        "body_pain_extractions", "body_pain_count",
        "patient_summary", "age_years", "sex", "pub_date",
    ]
    output_cols = [c for c in output_cols if c in out.columns]

    for col in out.select_dtypes(include=["datetime64[ns]"]).columns:
        out[col] = out[col].dt.floor("us")

    return out[output_cols], errors


def extract_body_pain_all():
    """Extract body-pain pairs for all pmc_patients rows, saving progress every BATCH_SIZE rows."""
    dest = os.path.join(VOLUME_ROOT, "tier2_pmc_patients_body_pain.parquet")
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
    logger.info("Already extracted: %d | Remaining: %d", len(done_ids), len(remaining))

    if len(remaining) == 0:
        logger.info("All rows already extracted. Merging checkpoints...")
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

        extracted_batch, batch_errors = extract_batch(batch_df)
        total_errors += batch_errors
        save_checkpoint(extracted_batch, batch_num)

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

    n_with_pain = (merged["body_pain_count"] > 0).sum()
    logger.info("With pain data: %d / %d (%.1f%%)",
                n_with_pain, len(merged), 100 * n_with_pain / max(len(merged), 1))

    # Show top body parts across all extractions
    all_extractions = []
    for raw in merged["body_pain_extractions"]:
        try:
            all_extractions.extend(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            continue
    if all_extractions:
        bp_series = pd.Series([e["body_part"] for e in all_extractions])
        logger.info("Top body parts:\n%s", bp_series.value_counts().head(20).to_string())

        pl_series = pd.Series([e["pain_level"] for e in all_extractions])
        logger.info("Pain level distribution:\n%s", pl_series.value_counts().to_string())

    return merged


output_df = extract_body_pain_all()
if output_df is not None:
    n = (output_df["body_pain_count"] > 0).sum()
    logger.info("Done: %d total, %d with pain data", len(output_df), n)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Register Table

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.pmc_patients_body_pain
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier2_pmc_patients_body_pain.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT body_pain_count, COUNT(*) as patients
# MAGIC FROM workspace.aura.pmc_patients_body_pain
# MAGIC GROUP BY body_pain_count
# MAGIC ORDER BY body_pain_count;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Verify: sample extracted rows with pain data
# MAGIC SELECT patient_id, body_pain_count,
# MAGIC        SUBSTRING(body_pain_extractions, 1, 500) as extractions_preview,
# MAGIC        SUBSTRING(patient_summary, 1, 300) as summary_preview
# MAGIC FROM workspace.aura.pmc_patients_body_pain
# MAGIC WHERE body_pain_count > 0
# MAGIC LIMIT 5;
