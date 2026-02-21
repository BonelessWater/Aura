"""
Aura Dataset Downloader
Downloads all freely accessible datasets specified in dataspec.md.
Credentialed datasets (MIMIC-IV, eICU, FinnGen, UK Biobank) are skipped
and must be obtained manually.
"""
import logging
import os
import subprocess
import sys
import zipfile
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")


def download_file(url, dest_path, chunk_size=8192):
    """Download a file from a URL to a local path."""
    logger.info("Downloading %s -> %s", url, dest_path)
    try:
        resp = requests.get(url, stream=True, timeout=120, allow_redirects=True)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                f.write(chunk)
        logger.info("Downloaded successfully: %s (%.2f MB)", dest_path, os.path.getsize(dest_path) / 1e6)
    except requests.RequestException as e:
        logger.error("Failed to download %s: %s", url, e)
        raise


def download_harvard_dataverse():
    """
    Harvard Dataverse: Diagnosis of Rheumatic and Autoimmune Diseases
    DOI: 10.7910/DVN/VM4OR3
    """
    dest_dir = os.path.join(RAW_DIR, "harvard")
    # The Harvard Dataverse API allows direct file download via the dataset DOI
    # We query the dataset metadata first to get file IDs
    api_url = "https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/VM4OR3"
    logger.info("Fetching Harvard Dataverse metadata...")
    try:
        resp = requests.get(api_url, timeout=30)
        resp.raise_for_status()
        metadata = resp.json()
        files = metadata.get("data", {}).get("latestVersion", {}).get("files", [])
        if not files:
            logger.warning("No files found in Harvard Dataverse dataset metadata.")
            return

        for file_info in files:
            file_id = file_info["dataFile"]["id"]
            filename = file_info["dataFile"].get("filename", f"file_{file_id}")
            file_url = f"https://dataverse.harvard.edu/api/access/datafile/{file_id}"
            dest_path = os.path.join(dest_dir, filename)
            if os.path.exists(dest_path):
                logger.info("Already exists, skipping: %s", dest_path)
                continue
            download_file(file_url, dest_path)
    except requests.RequestException as e:
        logger.error("Failed to fetch Harvard Dataverse metadata: %s", e)
        raise


def download_nhanes():
    """
    NHANES CBC and CRP data from recent cycles.
    Downloads the CBC (.XPT) and CRP (.XPT) lab files.
    """
    dest_dir = os.path.join(RAW_DIR, "nhanes")
    # We grab a few key cycles for CBC and high-sensitivity CRP
    files_to_download = {
        # 2017-2018 Pre-pandemic cycle
        "CBC_J.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/CBC_J.XPT",
        "HSCRP_J.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/HSCRP_J.XPT",
        "DEMO_J.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/DEMO_J.XPT",
        # 2015-2016
        "CBC_I.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2015-2016/CBC_I.XPT",
        "HSCRP_I.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2015-2016/HSCRP_I.XPT",
        "DEMO_I.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2015-2016/DEMO_I.XPT",
        # 2013-2014
        "CBC_H.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2013-2014/CBC_H.XPT",
        "HSCRP_H.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2013-2014/HSCRP_H.XPT",
        "DEMO_H.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2013-2014/DEMO_H.XPT",
        # 2011-2012 (the cycle with ANA prevalence data)
        "CBC_G.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2011-2012/CBC_G.XPT",
        "HSCRP_G.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2011-2012/HSCRP_G.XPT",
        "DEMO_G.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2011-2012/DEMO_G.XPT",
    }
    for filename, url in files_to_download.items():
        dest_path = os.path.join(dest_dir, filename)
        if os.path.exists(dest_path):
            logger.info("Already exists, skipping: %s", dest_path)
            continue
        download_file(url, dest_path)


def download_uci_drug():
    """
    UCI Drug-Induced Autoimmunity Prediction dataset.
    """
    dest_dir = os.path.join(RAW_DIR, "uci_drug")
    # UCI datasets can be downloaded via their API
    api_url = "https://archive.ics.uci.edu/static/public/1104/drug_induced_autoimmunity_prediction.zip"
    dest_path = os.path.join(dest_dir, "drug_induced_autoimmunity.zip")
    if os.path.exists(dest_path):
        logger.info("Already exists, skipping UCI download.")
    else:
        try:
            download_file(api_url, dest_path)
        except Exception as e:
            logger.warning("Direct ZIP download failed (%s), trying ucimlrepo...", e)
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "ucimlrepo", "-q"],
                    check=True,
                )
                import importlib
                ucimlrepo = importlib.import_module("ucimlrepo")
                dataset = ucimlrepo.fetch_ucirepo(id=1104)
                dataset.data.features.to_csv(os.path.join(dest_dir, "features.csv"), index=False)
                dataset.data.targets.to_csv(os.path.join(dest_dir, "targets.csv"), index=False)
                logger.info("UCI data saved via ucimlrepo API.")
                return
            except Exception as e2:
                logger.error("ucimlrepo fallback also failed: %s", e2)
                raise

    # Unzip
    if dest_path.endswith(".zip") and os.path.exists(dest_path):
        try:
            with zipfile.ZipFile(dest_path, "r") as z:
                z.extractall(dest_dir)
            logger.info("Unzipped UCI dataset to %s", dest_dir)
        except zipfile.BadZipFile as e:
            logger.error("Bad zip file %s: %s", dest_path, e)


def download_mendeley():
    """
    Mendeley Data: Targeted Lipidomics dataset.
    """
    dest_dir = os.path.join(RAW_DIR, "mendeley")
    # Mendeley provides a direct download API
    api_url = "https://data.mendeley.com/public-files/datasets/m2p6rr9v36/files/1"
    dest_path = os.path.join(dest_dir, "mendeley_data.zip")
    if os.path.exists(dest_path) or any(f.endswith(".csv") for f in os.listdir(dest_dir)):
        logger.info("Mendeley data already present, skipping.")
        return
    try:
        download_file(api_url, dest_path)
        if dest_path.endswith(".zip"):
            with zipfile.ZipFile(dest_path, "r") as z:
                z.extractall(dest_dir)
            logger.info("Unzipped Mendeley dataset to %s", dest_dir)
    except Exception as e:
        logger.warning("Mendeley direct download failed (%s). May need manual download from DOI page.", e)


def main():
    logger.info("=" * 60)
    logger.info("AURA DATASET DOWNLOADER")
    logger.info("=" * 60)

    # 1. Harvard Dataverse
    logger.info("--- [1/4] Harvard Dataverse ---")
    try:
        download_harvard_dataverse()
    except Exception as e:
        logger.error("Harvard Dataverse download failed: %s", e)

    # 2. NHANES
    logger.info("--- [2/4] NHANES (CDC) ---")
    try:
        download_nhanes()
    except Exception as e:
        logger.error("NHANES download failed: %s", e)

    # 3. UCI Drug
    logger.info("--- [3/4] UCI Drug-Induced Autoimmunity ---")
    try:
        download_uci_drug()
    except Exception as e:
        logger.error("UCI download failed: %s", e)

    # 4. Mendeley
    logger.info("--- [4/4] Mendeley Lipidomics ---")
    try:
        download_mendeley()
    except Exception as e:
        logger.error("Mendeley download failed: %s", e)

    logger.info("=" * 60)
    logger.info("DOWNLOAD PHASE COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
