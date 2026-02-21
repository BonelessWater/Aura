"""
Aura Remaining Datasets Pipeline
=================================
Parallel download -> upload -> verify -> delete pipeline for all datasets
NOT yet on Databricks (dataspec sections 5-13).

Follows the same pattern as pipeline.py (HugeAmp/FinnGen):
  1. Download from external API/source to local disk on Azure VM
  2. Upload to Databricks Volume via `databricks fs cp`
  3. Verify the file exists on the Volume
  4. Delete the local copy

Usage (on Azure VM aura-dl):
    ssh azureuser@20.65.67.169
    source ~/aura-env/bin/activate
    python3 ~/pipeline_remaining.py

    # Run specific groups:
    python3 ~/pipeline_remaining.py --group easy
    python3 ~/pipeline_remaining.py --group medium
    python3 ~/pipeline_remaining.py --group hard

    # Run specific datasets:
    python3 ~/pipeline_remaining.py --only flaredown ctd epa_aqs

    # Dry run (show what would be downloaded):
    python3 ~/pipeline_remaining.py --dry-run
"""
import argparse
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
)
logger = logging.getLogger("aura_pipeline_remaining")

OUTPUT_DIR = os.path.expanduser("~/aura_data")
VOLUME_ROOT = "dbfs:/Volumes/workspace/aura/aura_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

results_lock = Lock()
results = {}
timings = {}


# ---------------------------------------------------------------------------
# Databricks upload / verify / delete (copied from pipeline.py)
# ---------------------------------------------------------------------------

def run_databricks_cmd(args, timeout=300):
    """Run a databricks CLI command and return (success, output)."""
    cmd = ["databricks"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        stderr = result.stderr.strip()
        if result.returncode != 0:
            logger.error(
                "databricks %s failed: %s",
                " ".join(args[:3]), stderr,
            )
            return False, stderr
        # Also check stderr for error messages (some commands return 0 on failure)
        if stderr and "error" in stderr.lower():
            logger.error(
                "databricks %s returned 0 but stderr: %s",
                " ".join(args[:3]), stderr,
            )
            return False, stderr
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error("databricks %s timed out after %ds", " ".join(args[:3]), timeout)
        return False, "timeout"


def upload_verify_delete(local_path, remote_subdir, max_retries=3):
    """Upload a local file to Databricks Volume, verify, then delete local copy."""
    fname = os.path.basename(local_path)
    remote_dir = f"{VOLUME_ROOT}/raw/{remote_subdir}"
    remote_path = f"{remote_dir}/{fname}"
    local_size_mb = os.path.getsize(local_path) / 1e6

    # Upload with longer timeout for large files
    timeout = max(300, int(local_size_mb * 10))  # ~10s per MB, min 5 min

    for attempt in range(1, max_retries + 1):
        # Ensure remote directory exists (retry each attempt)
        ok, _ = run_databricks_cmd(["fs", "mkdirs", remote_dir])
        if not ok:
            logger.warning("mkdirs failed for %s, attempt %d", remote_dir, attempt)
        # Brief pause for directory propagation
        time.sleep(1)

        logger.info(
            "Uploading %s (%.1f MB) -> %s (attempt %d/%d, timeout=%ds)",
            fname, local_size_mb, remote_path, attempt, max_retries, timeout,
        )
        ok, out = run_databricks_cmd(
            ["fs", "cp", local_path, remote_path, "--overwrite"],
            timeout=timeout,
        )
        if ok:
            break

        logger.warning(
            "Upload attempt %d/%d failed for %s: %s",
            attempt, max_retries, fname, out,
        )
        if attempt < max_retries:
            wait = attempt * 5
            logger.info("Retrying in %ds...", wait)
            time.sleep(wait)
    else:
        logger.error("Upload FAILED for %s after %d attempts", fname, max_retries)
        return False

    # Verify
    logger.info("Verifying %s on Databricks...", fname)
    ok, out = run_databricks_cmd(
        ["fs", "ls", f"{VOLUME_ROOT}/raw/{remote_subdir}/"],
    )
    if not ok or fname not in out:
        logger.error("Verification FAILED for %s", fname)
        return False

    # Delete local
    os.remove(local_path)
    logger.info("Done: %s uploaded, verified, local deleted", fname)
    return True


def upload_directory(local_dir, remote_subdir):
    """Upload all files in a local directory to Databricks Volume."""
    if not os.path.isdir(local_dir):
        logger.error("Not a directory: %s", local_dir)
        return False

    files = [
        f for f in os.listdir(local_dir)
        if os.path.isfile(os.path.join(local_dir, f))
    ]
    if not files:
        logger.warning("No files to upload in %s", local_dir)
        return False

    logger.info("Uploading %d files from %s", len(files), local_dir)
    all_ok = True
    for fname in files:
        local_path = os.path.join(local_dir, fname)
        ok = upload_verify_delete(local_path, remote_subdir)
        if not ok:
            all_ok = False
            logger.error("Failed to upload %s", fname)

    return all_ok


# ---------------------------------------------------------------------------
# Pipeline task runner
# ---------------------------------------------------------------------------

def pipeline_task(download_fn, local_path, remote_subdir, label):
    """Run a single download -> upload -> verify -> delete pipeline task."""
    start = time.time()
    try:
        logger.info("[%s] Starting download...", label)
        success = download_fn(local_path)
        if not success:
            logger.error("[%s] Download failed", label)
            with results_lock:
                results[label] = "FAILED (download)"
                timings[label] = time.time() - start
            return

        # Check if download produced a directory of files or a single file
        local_dir = os.path.dirname(local_path)
        files_in_dir = [
            f for f in os.listdir(local_dir)
            if os.path.isfile(os.path.join(local_dir, f))
        ]

        if len(files_in_dir) > 1:
            # Multiple files: upload entire directory
            logger.info("[%s] Download complete (%d files), uploading directory...", label, len(files_in_dir))
            ok = upload_directory(local_dir, remote_subdir)
        elif os.path.exists(local_path):
            # Single file: upload directly
            size_mb = os.path.getsize(local_path) / 1e6
            logger.info("[%s] Download complete (%.1f MB), uploading...", label, size_mb)
            ok = upload_verify_delete(local_path, remote_subdir)
        else:
            # Download function succeeded but file not at expected path
            # Try uploading whatever is in the directory
            if files_in_dir:
                logger.info(
                    "[%s] Output at different path, uploading %d files...",
                    label, len(files_in_dir),
                )
                ok = upload_directory(local_dir, remote_subdir)
            else:
                logger.error("[%s] No output files found after download", label)
                ok = False

        elapsed = time.time() - start
        with results_lock:
            results[label] = "SUCCESS" if ok else "FAILED (upload)"
            timings[label] = elapsed

    except Exception as exc:
        logger.error("[%s] Pipeline error: %s", label, exc, exc_info=True)
        with results_lock:
            results[label] = f"FAILED ({exc})"
            timings[label] = time.time() - start


# ---------------------------------------------------------------------------
# Download function imports (inline to avoid import errors on VM)
# ---------------------------------------------------------------------------

def make_download_fn(module_name):
    """Dynamically import a download module and return its download function.

    This allows the pipeline to work whether run from the repo root
    or deployed standalone on the VM.
    """
    def wrapper(local_path):
        # Try relative import first (from repo)
        try:
            import importlib
            mod = importlib.import_module(f"scripts.downloads.{module_name}")
            return mod.download(local_path)
        except ImportError:
            pass

        # Try direct import (deployed on VM alongside download scripts)
        try:
            import importlib
            mod = importlib.import_module(module_name)
            return mod.download(local_path)
        except ImportError:
            pass

        # Try importing from downloads/ subdirectory
        downloads_dir = os.path.join(os.path.dirname(__file__), "downloads")
        if os.path.isdir(downloads_dir):
            sys.path.insert(0, downloads_dir)
            try:
                import importlib
                mod = importlib.import_module(module_name)
                return mod.download(local_path)
            except ImportError:
                pass
            finally:
                sys.path.pop(0)

        logger.error("Could not import download module: %s", module_name)
        return False

    return wrapper


# ---------------------------------------------------------------------------
# Task registry
# ---------------------------------------------------------------------------

# All datasets NOT on Databricks, organized by priority group
TASK_REGISTRY = {
    # --- EASY (direct downloads, small files) ---
    "mendeley": {
        "module": "sec05_mendeley",
        "filename": "mendeley_lipidomics.zip",
        "subdir": "mendeley",
        "group": "easy",
        "section": 5,
        "description": "Mendeley Lipidomics/Flow Cytometry",
    },
    "flaredown": {
        "module": "sec12_flaredown",
        "filename": "flaredown_data.csv",
        "subdir": "flaredown",
        "group": "easy",
        "section": 12,
        "description": "Flaredown Autoimmune Symptom Tracker",
    },
    "ctd": {
        "module": "sec13_ctd",
        "filename": "CTD_chemicals_diseases.tsv.gz",
        "subdir": "ctd",
        "group": "easy",
        "section": 13,
        "description": "CTD Toxicogenomics",
    },
    "epa_aqs": {
        "module": "sec13_epa_aqs",
        "filename": "annual_conc_by_monitor_2023.zip",
        "subdir": "epa_aqs",
        "group": "easy",
        "section": 13,
        "description": "EPA Air Quality System",
    },
    "afnd": {
        "module": "sec09_afnd",
        "filename": "afnd_hla_frequencies.parquet",
        "subdir": "afnd",
        "group": "easy",
        "section": 9,
        "description": "AFND HLA Frequencies",
    },
    "immunobase": {
        "module": "sec09_immunobase",
        "filename": "immunobase_data.tar.gz",
        "subdir": "immunobase",
        "group": "easy",
        "section": 9,
        "description": "ImmunoBase Fine-Mapping",
    },
    "olink": {
        "module": "sec10_olink",
        "filename": "olink_data.xlsx",
        "subdir": "olink",
        "group": "easy",
        "section": 10,
        "description": "Olink/UKB-PPP Proteomics",
    },
    "hpa": {
        "module": "sec10_hpa",
        "filename": "hpa_data.tsv",
        "subdir": "hpa",
        "group": "easy",
        "section": 10,
        "description": "Human Protein Atlas v25",
    },

    # --- MEDIUM (API queries, moderate size) ---
    "open_targets": {
        "module": "sec05_open_targets",
        "filename": "open_targets_autoimmune.parquet",
        "subdir": "open_targets",
        "group": "medium",
        "section": 5,
        "description": "Open Targets Platform",
    },
    "adex": {
        "module": "sec06_adex",
        "filename": "adex_data.tar.gz",
        "subdir": "adex",
        "group": "medium",
        "section": 6,
        "description": "ADEx Autoimmune Transcriptomics",
    },
    "iaaa": {
        "module": "sec06_iaaa",
        "filename": "iaaa_manifest.txt",
        "subdir": "iaaa",
        "group": "medium",
        "section": 6,
        "description": "IAAA Autoimmune Atlas",
    },
    "gwas_catalog": {
        "module": "sec09_gwas_catalog",
        "filename": "gwas_catalog_autoimmune.parquet",
        "subdir": "gwas_catalog",
        "group": "medium",
        "section": 9,
        "description": "GWAS Catalog Summary Stats",
    },
    "pan_ukbb": {
        "module": "sec09_pan_ukbb",
        "filename": "pan_ukbb_manifest.tsv",
        "subdir": "pan_ukbb",
        "group": "medium",
        "section": 9,
        "description": "Pan-UK Biobank GWAS",
    },
    "hmdb": {
        "module": "sec11_hmdb",
        "filename": "hmdb_data.zip",
        "subdir": "hmdb",
        "group": "medium",
        "section": 11,
        "description": "HMDB / Serum Metabolome",
    },
    "metabolights": {
        "module": "sec11_metabolights",
        "filename": "metabolights_index.parquet",
        "subdir": "metabolights",
        "group": "medium",
        "section": 11,
        "description": "MetaboLights Metabolomics",
    },

    # --- HARD (large files, complex downloads) ---
    "hca_eqtl": {
        "module": "sec07_hca_eqtl",
        "filename": "hca_eqtl_data.h5ad",
        "subdir": "hca_eqtl",
        "group": "hard",
        "section": 7,
        "description": "Human Cell Atlas eQTL",
    },
    "allen_atlas": {
        "module": "sec07_allen_atlas",
        "filename": "allen_immune_atlas.h5ad",
        "subdir": "allen_atlas",
        "group": "hard",
        "section": 7,
        "description": "Allen Immune Health Atlas",
    },
    "hmp": {
        "module": "sec08_hmp",
        "filename": "hmp_data.tar.gz",
        "subdir": "hmp",
        "group": "hard",
        "section": 8,
        "description": "Human Microbiome Project",
    },
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_tasks(selected_keys):
    """Build task tuples from selected registry keys."""
    tasks = []
    for key in selected_keys:
        info = TASK_REGISTRY[key]
        local_dir = os.path.join(OUTPUT_DIR, info["subdir"])
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, info["filename"])

        tasks.append((
            make_download_fn(info["module"]),
            local_path,
            info["subdir"],
            key,
        ))
    return tasks


def parse_args():
    parser = argparse.ArgumentParser(
        description="Aura Remaining Datasets Pipeline",
    )
    parser.add_argument(
        "--group",
        choices=["easy", "medium", "hard", "all"],
        default="all",
        help="Run only tasks in this priority group (default: all)",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=list(TASK_REGISTRY.keys()),
        help="Run only these specific datasets",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        choices=list(TASK_REGISTRY.keys()),
        default=[],
        help="Exclude these datasets",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel download workers (default: 4)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run downloads sequentially instead of in parallel",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info("=" * 60)
    logger.info("  Aura Remaining Datasets Pipeline")
    logger.info("  Download -> Upload -> Verify -> Delete")
    logger.info("=" * 60)
    logger.info("  Output dir: %s", OUTPUT_DIR)
    logger.info("  Volume root: %s", VOLUME_ROOT)
    logger.info("=" * 60)

    # Select tasks
    if args.only:
        selected_keys = args.only
    elif args.group == "all":
        selected_keys = list(TASK_REGISTRY.keys())
    else:
        selected_keys = [
            k for k, v in TASK_REGISTRY.items()
            if v["group"] == args.group
        ]

    # Apply exclusions
    selected_keys = [k for k in selected_keys if k not in args.exclude]

    # Sort by section number, then by group priority
    group_order = {"easy": 0, "medium": 1, "hard": 2}
    selected_keys.sort(
        key=lambda k: (
            group_order.get(TASK_REGISTRY[k]["group"], 3),
            TASK_REGISTRY[k]["section"],
        ),
    )

    logger.info("Selected %d datasets:", len(selected_keys))
    for key in selected_keys:
        info = TASK_REGISTRY[key]
        logger.info(
            "  [%s] sec%02d: %s (%s)",
            info["group"].upper(),
            info["section"],
            info["description"],
            key,
        )

    if args.dry_run:
        logger.info("DRY RUN - no downloads will be performed")
        return

    # Build and run tasks
    tasks = build_tasks(selected_keys)
    pipeline_start = time.time()

    if args.sequential:
        logger.info("Running %d tasks sequentially...", len(tasks))
        for download_fn, local_path, remote_subdir, label in tasks:
            pipeline_task(download_fn, local_path, remote_subdir, label)
    else:
        workers = min(args.workers, len(tasks))
        logger.info("Launching %d tasks with %d workers...", len(tasks), workers)
        with ThreadPoolExecutor(
            max_workers=workers, thread_name_prefix="worker",
        ) as pool:
            futures = {}
            for download_fn, local_path, remote_subdir, label in tasks:
                fut = pool.submit(
                    pipeline_task,
                    download_fn, local_path, remote_subdir, label,
                )
                futures[fut] = label

            for fut in as_completed(futures):
                label = futures[fut]
                try:
                    fut.result()
                except Exception as exc:
                    logger.error(
                        "[%s] Unhandled exception: %s", label, exc,
                    )
                    with results_lock:
                        results[label] = f"FAILED ({exc})"

    # Summary
    pipeline_elapsed = time.time() - pipeline_start
    logger.info("")
    logger.info("=" * 60)
    logger.info("  Pipeline Summary")
    logger.info("=" * 60)

    successes = 0
    failures = 0
    for label in selected_keys:
        status = results.get(label, "NOT RUN")
        elapsed = timings.get(label, 0)
        group = TASK_REGISTRY[label]["group"]
        logger.info(
            "  %-20s [%-6s] %-25s (%.0fs)",
            label, group, status, elapsed,
        )
        if "SUCCESS" in status:
            successes += 1
        elif "FAILED" in status:
            failures += 1

    logger.info("=" * 60)
    logger.info(
        "  Total: %d success, %d failed, %d not run",
        successes, failures, len(selected_keys) - successes - failures,
    )
    logger.info("  Pipeline duration: %.1f seconds", pipeline_elapsed)
    logger.info("=" * 60)

    # Check for remaining local files
    remaining = []
    for key in selected_keys:
        subdir = os.path.join(OUTPUT_DIR, TASK_REGISTRY[key]["subdir"])
        if os.path.isdir(subdir):
            files = [
                f for f in os.listdir(subdir)
                if os.path.isfile(os.path.join(subdir, f))
            ]
            if files:
                remaining.extend(
                    os.path.join(subdir, f) for f in files
                )

    if remaining:
        logger.warning("Local files remaining (%d):", len(remaining))
        for f in remaining[:20]:
            logger.warning("  %s", f)
    else:
        logger.info("All local files cleaned up.")


if __name__ == "__main__":
    main()
