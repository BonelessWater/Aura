"""Test loading PMC patient data from Databricks.

Tests against pmc_patients (source table, always available) to verify
the Databricks connection and data pipeline work. When pmc_patients_classified
is ready, run with --classified flag or change TABLE below.

Fetches a small sample (10 rows) to verify:
- Connection works
- Table exists and is queryable
- Expected columns are present
- Data types and non-null constraints hold
- Text fields contain actual clinical content
"""

import logging
import configparser
from pathlib import Path

import pytest
import pandas as pd

logger = logging.getLogger(__name__)

DATABRICKS_HOST = "dbc-893d098d-9dcb.cloud.databricks.com"
WAREHOUSE_ID = "a3f84fea6e440a44"
SAMPLE_LIMIT = 10

# Source table (always exists)
SOURCE_TABLE = "workspace.aura.pmc_patients"
SOURCE_COLUMNS = {
    "patient_id",
    "patient_uid",
    "pmid",
    "title",
    "patient_summary",
    "age_years",
    "sex",
    "pub_date",
}

# Classified table (created by the LLM classification job)
CLASSIFIED_TABLE = "workspace.aura.pmc_patients_classified"
CLASSIFIED_COLUMNS = SOURCE_COLUMNS | {
    "diagnosis",
    "diagnosis_lines",
    "preliminary_lines",
    "diagnosis_text",
    "preliminary_text",
}


def _get_token():
    """Read Databricks token from ~/.databrickscfg."""
    cfg_path = Path.home() / ".databrickscfg"
    if not cfg_path.exists():
        return None
    config = configparser.ConfigParser()
    config.read(cfg_path)
    if "DEFAULT" in config and "token" in config["DEFAULT"]:
        return config["DEFAULT"]["token"]
    return None


def _connect():
    """Create a Databricks SQL connection, or None if no credentials."""
    token = _get_token()
    if not token:
        return None
    from databricks import sql as databricks_sql
    return databricks_sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        access_token=token,
    )


def _table_exists(connection, table):
    """Check if a table exists in Databricks."""
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT 1 FROM {table} LIMIT 1")
        cursor.fetchone()
        return True
    except Exception:
        return False
    finally:
        cursor.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db_connection():
    """Shared Databricks connection for all tests."""
    conn = _connect()
    if conn is None:
        pytest.skip("No Databricks token found in ~/.databrickscfg")
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def source_sample(db_connection):
    """Fetch a small sample from the source pmc_patients table."""
    cursor = db_connection.cursor()
    cursor.execute(f"SELECT * FROM {SOURCE_TABLE} LIMIT {SAMPLE_LIMIT}")
    df = cursor.fetchall_arrow().to_pandas()
    cursor.close()
    return df


@pytest.fixture(scope="module")
def source_count(db_connection):
    """Fetch the row count from the source table."""
    cursor = db_connection.cursor()
    cursor.execute(f"SELECT COUNT(*) AS cnt FROM {SOURCE_TABLE}")
    row = cursor.fetchone()
    cursor.close()
    return row[0]


@pytest.fixture(scope="module")
def classified_sample(db_connection):
    """Fetch sample from classified table, skip if not yet created."""
    if not _table_exists(db_connection, CLASSIFIED_TABLE):
        pytest.skip(f"{CLASSIFIED_TABLE} does not exist yet (job still running?)")
    cursor = db_connection.cursor()
    cursor.execute(f"SELECT * FROM {CLASSIFIED_TABLE} LIMIT {SAMPLE_LIMIT}")
    df = cursor.fetchall_arrow().to_pandas()
    cursor.close()
    return df


# ---------------------------------------------------------------------------
# Tests: source table (pmc_patients)
# ---------------------------------------------------------------------------

class TestSourceConnection:
    """Verify connection and source table basics."""

    def test_sample_returns_rows(self, source_sample):
        assert len(source_sample) == SAMPLE_LIMIT
        logger.info("Fetched %d sample rows from %s", len(source_sample), SOURCE_TABLE)

    def test_row_count(self, source_count):
        assert source_count > 200_000, f"Expected >200K rows, got {source_count:,}"
        logger.info("Total rows in %s: %d", SOURCE_TABLE, source_count)

    def test_expected_columns(self, source_sample):
        actual = set(source_sample.columns)
        missing = SOURCE_COLUMNS - actual
        assert not missing, f"Missing columns: {missing}"
        logger.info("Columns: %s", list(source_sample.columns))


class TestSourceDataQuality:
    """Verify source data is usable for classification."""

    def test_patient_summary_not_empty(self, source_sample):
        non_null = source_sample["patient_summary"].dropna()
        non_empty = non_null[non_null.str.strip() != ""]
        assert len(non_empty) > 0, "All patient_summary values are empty"
        logger.info("Non-empty patient_summary: %d/%d", len(non_empty), len(source_sample))

    def test_patient_summary_has_clinical_content(self, source_sample):
        text = source_sample["patient_summary"].dropna().iloc[0]
        assert len(text) > 100, f"Text too short ({len(text)} chars): {text[:80]}"
        logger.info("Sample text (%d chars): %s...", len(text), text[:150])

    def test_patient_id_is_numeric(self, source_sample):
        ids = pd.to_numeric(source_sample["patient_id"], errors="coerce")
        assert ids.notna().all(), "Some patient_id values are not numeric"

    def test_title_not_empty(self, source_sample):
        non_null = source_sample["title"].dropna()
        assert len(non_null) > 0, "All title values are empty"

    def test_sample_row_preview(self, source_sample):
        """Print a full row for visual inspection."""
        row = source_sample.iloc[0]
        logger.info("--- Sample row from %s ---", SOURCE_TABLE)
        for col in ["patient_id", "pmid", "title", "patient_summary", "age_years", "sex"]:
            val = row.get(col, "N/A")
            if isinstance(val, str) and len(val) > 200:
                val = val[:200] + "..."
            logger.info("  %s: %s", col, val)


# ---------------------------------------------------------------------------
# Tests: classified table (pmc_patients_classified) -- skipped if not ready
# ---------------------------------------------------------------------------

class TestClassifiedSchema:
    """Verify classified table has the additional LLM-generated columns."""

    def test_has_diagnosis_column(self, classified_sample):
        assert "diagnosis" in classified_sample.columns

    def test_has_preliminary_text_column(self, classified_sample):
        assert "preliminary_text" in classified_sample.columns

    def test_has_diagnosis_text_column(self, classified_sample):
        assert "diagnosis_text" in classified_sample.columns

    def test_all_expected_columns(self, classified_sample):
        actual = set(classified_sample.columns)
        missing = CLASSIFIED_COLUMNS - actual
        assert not missing, f"Missing columns: {missing}"


class TestClassifiedDataQuality:
    """Verify classified data is ready for fine-tuning."""

    def test_preliminary_text_not_empty(self, classified_sample):
        non_null = classified_sample["preliminary_text"].dropna()
        non_empty = non_null[non_null.str.strip() != ""]
        assert len(non_empty) > 0

    def test_diagnosis_not_empty(self, classified_sample):
        non_null = classified_sample["diagnosis"].dropna()
        non_empty = non_null[non_null.str.strip() != ""]
        assert len(non_empty) > 0

    def test_diagnosis_is_short_label(self, classified_sample):
        non_null = classified_sample["diagnosis"].dropna()
        avg_len = non_null.str.len().mean()
        assert avg_len < 200, f"Diagnosis avg length {avg_len:.0f} chars seems too long"

    def test_sample_row_preview(self, classified_sample):
        row = classified_sample.iloc[0]
        logger.info("--- Sample row from %s ---", CLASSIFIED_TABLE)
        for col in ["patient_id", "diagnosis", "preliminary_text", "diagnosis_text"]:
            val = row.get(col, "N/A")
            if isinstance(val, str) and len(val) > 200:
                val = val[:200] + "..."
            logger.info("  %s: %s", col, val)
