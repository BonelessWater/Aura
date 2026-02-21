import os
import subprocess
import logging
import json
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s")
logger = logging.getLogger("aura_pipeline")

OUTPUT_DIR = os.path.expanduser("~/aura_data")
VOLUME_ROOT = "dbfs:/Volumes/workspace/aura/aura_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

results_lock = Lock()
results = {}


def run_databricks_cmd(args):
    cmd = ["databricks"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error("databricks %s failed: %s", ' '.join(args[:3]), result.stderr.strip())
            return False, result.stderr.strip()
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error("databricks %s timed out", ' '.join(args[:3]))
        return False, "timeout"


def upload_verify_delete(local_path, remote_subdir):
    fname = os.path.basename(local_path)
    remote_path = f"{VOLUME_ROOT}/raw/{remote_subdir}/{fname}"
    local_size_mb = os.path.getsize(local_path) / 1e6

    logger.info("Uploading %s (%.1f MB) -> %s", fname, local_size_mb, remote_path)
    ok, out = run_databricks_cmd(["fs", "cp", local_path, remote_path, "--overwrite"])
    if not ok:
        logger.error("Upload FAILED for %s: %s", fname, out)
        return False

    logger.info("Verifying %s on Databricks...", fname)
    ok, out = run_databricks_cmd(["fs", "ls", f"{VOLUME_ROOT}/raw/{remote_subdir}/"])
    if not ok or fname not in out:
        logger.error("Verification FAILED for %s", fname)
        return False

    os.remove(local_path)
    logger.info("Done: %s uploaded, verified, local deleted", fname)
    return True


def pipeline_file(download_fn, local_path, remote_subdir, label):
    try:
        logger.info("[%s] Starting download...", label)
        success = download_fn(local_path)
        if not success:
            logger.error("[%s] Download failed", label)
            with results_lock:
                results[label] = "FAILED (download)"
            return
        logger.info("[%s] Download complete, starting upload...", label)
        ok = upload_verify_delete(local_path, remote_subdir)
        with results_lock:
            results[label] = "SUCCESS" if ok else "FAILED (upload)"
    except Exception as exc:
        logger.error("[%s] Pipeline error: %s", label, exc)
        with results_lock:
            results[label] = f"FAILED ({exc})"


# ---- HugeAmp GWAS ----
HUGEAMP_API = "https://bioindex.hugeamp.org/api/bio/query/global-associations"
HUGEAMP_CONT = "https://bioindex.hugeamp.org/api/bio/cont"

GWAS_PHENOTYPES = {
    "T1D": "Type 1 Diabetes", "RhA": "Rheumatoid Arthritis",
    "SLE": "Systemic Lupus Erythematosus", "CD": "Crohn's Disease",
    "UC": "Ulcerative Colitis", "IBD": "Inflammatory Bowel Disease",
    "MultipleSclerosis": "Multiple Sclerosis", "Psoriasis": "Psoriasis",
    "Celiac": "Celiac Disease", "Graves": "Graves' Disease",
    "Vitiligo": "Vitiligo", "LADA": "Latent Autoimmune Diabetes in Adults",
    "Addison": "Autoimmune Addison's Disease",
}


def download_gwas(local_path):
    all_rows = []
    for phenotype, label in GWAS_PHENOTYPES.items():
        logger.info("  GWAS: querying %s (%s)", phenotype, label)
        try:
            resp = requests.get(HUGEAMP_API, params={"q": phenotype, "limit": 500}, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            records = data.get("data", [])
            cont = data.get("continuation")
            while cont:
                r2 = requests.get(HUGEAMP_CONT, params={"token": cont}, timeout=120)
                r2.raise_for_status()
                d2 = r2.json()
                records.extend(d2.get("data", []))
                cont = d2.get("continuation")
            for r in records:
                r["queried_phenotype"] = phenotype
                r["queried_label"] = label
            all_rows.extend(records)
            logger.info("  GWAS: %s -> %d associations", phenotype, len(records))
        except requests.RequestException as exc:
            logger.error("  GWAS: %s failed: %s", phenotype, exc)
    if not all_rows:
        return False
    df = pd.DataFrame(all_rows)
    df.to_parquet(local_path, index=False)
    logger.info("  GWAS: saved %d rows to %s", len(df), local_path)
    return True


# ---- FinnGen R12 (per-file parallel) ----
FINNGEN_ENDPOINTS = {
    "M13_RHEUMA": "Rheumatoid Arthritis",
    "SLE_FG": "Systemic Lupus Erythematosus",
    "K11_IBD_STRICT": "Inflammatory Bowel Disease",
    "E4_THYROIDITAUTOIM": "Autoimmune Thyroiditis",
    "L12_PSORIASIS": "Psoriasis",
}

FINNGEN_URL = "https://storage.googleapis.com/finngen-public-data-r12/summary_stats/release/finngen_R12_{ep}.gz"


def make_finngen_downloader(endpoint):
    def download_finngen(local_path):
        url = FINNGEN_URL.format(ep=endpoint)
        logger.info("  FinnGen: downloading %s", endpoint)
        try:
            resp = requests.get(url, stream=True, timeout=600)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
            logger.info("  FinnGen: %s saved (%.1f MB)", endpoint, os.path.getsize(local_path) / 1e6)
            return True
        except requests.RequestException as exc:
            logger.error("  FinnGen: %s failed: %s", endpoint, exc)
            return False
    return download_finngen


if __name__ == "__main__":
    logger.info("========================================")
    logger.info("  Aura Parallel Pipeline")
    logger.info("  Download -> Upload -> Verify -> Delete")
    logger.info("========================================")

    tasks = []

    # GWAS task
    tasks.append((
        download_gwas,
        os.path.join(OUTPUT_DIR, "hugeamp_autoimmune_associations.parquet"),
        "gwas",
        "gwas-hugeamp"
    ))

    # FinnGen tasks (one per endpoint)
    for ep, label in FINNGEN_ENDPOINTS.items():
        tasks.append((
            make_finngen_downloader(ep),
            os.path.join(OUTPUT_DIR, f"finngen_R12_{ep}.gz"),
            "finngen",
            f"finngen-{ep}"
        ))

    # Run all tasks in parallel
    logger.info("Launching %d parallel tasks...", len(tasks))
    with ThreadPoolExecutor(max_workers=6, thread_name_prefix="worker") as pool:
        futures = {}
        for download_fn, local_path, remote_subdir, label in tasks:
            fut = pool.submit(pipeline_file, download_fn, local_path, remote_subdir, label)
            futures[fut] = label
        for fut in as_completed(futures):
            label = futures[fut]
            try:
                fut.result()
            except Exception as exc:
                logger.error("[%s] Unhandled exception: %s", label, exc)
                with results_lock:
                    results[label] = f"FAILED ({exc})"

    # Summary
    logger.info("\n========================================")
    logger.info("  Pipeline Summary")
    logger.info("========================================")
    for label, status in sorted(results.items()):
        logger.info("  %-25s %s", label, status)

    remaining = [f for f in os.listdir(OUTPUT_DIR) if os.path.isfile(os.path.join(OUTPUT_DIR, f))]
    if remaining:
        logger.warning("Local files remaining: %s", remaining)
    else:
        logger.info("All local files cleaned up.")
