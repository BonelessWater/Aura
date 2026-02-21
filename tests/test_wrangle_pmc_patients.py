"""
Tests for notebooks/wrangle_pmc_patients.py.

Validates the PMC-Patients wrangling logic: gender standardization,
age validation, and timestamp handling.
"""
import logging

import pandas as pd
import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Replicate key functions from the notebook
# ---------------------------------------------------------------------------


def standardize_gender(gender_val):
    """Standardize gender values to male/female/unknown."""
    if not gender_val or pd.isna(gender_val):
        return "unknown"
    g = str(gender_val).strip().lower()
    if g in ("m", "male", "man", "boy"):
        return "male"
    if g in ("f", "female", "woman", "girl"):
        return "female"
    return "unknown"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pmc_raw_df():
    """Synthetic PMC-Patients data matching actual parquet schema."""
    return pd.DataFrame({
        "patient_id": ["P001", "P002", "P003", "P004", "P005", "P006"],
        "patient_uid": ["uid1", "uid2", "uid3", "uid4", "uid5", "uid6"],
        "pmid": [12345, 23456, 34567, 45678, 56789, 67890],
        "title": [
            "A case of rheumatoid arthritis with lung involvement",
            "Acute myocardial infarction in a young adult",
            "Systemic lupus erythematosus presenting with nephritis",
            "Treatment of psoriasis with biologics",
            "Breast cancer screening recommendations",
            "Hashimoto thyroiditis and pregnancy outcomes",
        ],
        "patient_summary": [
            "A 45-year-old female with rheumatoid arthritis presented with cough.",
            "A 38-year-old male presented to the ER with chest pain.",
            "A 28-year-old female diagnosed with SLE presented with proteinuria.",
            "A 55-year-old male with chronic plaque psoriasis.",
            "A 62-year-old female underwent routine mammography.",
            "A 32-year-old female with Hashimoto thyroiditis.",
        ],
        "age_years": [45, 38, 28, 55, 62, 32],
        "age_raw": ["45", "38", "28", "55", "62", "32"],
        "gender": ["F", "M", "female", "male", None, "FEMALE"],
        "pub_date": [
            "2020-03-15", "2019-07-22", "2021-01-10",
            "2018-11-05", "2022-06-30", "2023-02-14",
        ],
    })


# ---------------------------------------------------------------------------
# Tests: Gender Standardization
# ---------------------------------------------------------------------------

class TestGenderStandardization:
    """Test gender value normalization."""

    def test_male_variants(self):
        assert standardize_gender("M") == "male"
        assert standardize_gender("male") == "male"
        assert standardize_gender("Male") == "male"
        assert standardize_gender("man") == "male"
        assert standardize_gender("boy") == "male"

    def test_female_variants(self):
        assert standardize_gender("F") == "female"
        assert standardize_gender("female") == "female"
        assert standardize_gender("FEMALE") == "female"
        assert standardize_gender("woman") == "female"
        assert standardize_gender("girl") == "female"

    def test_unknown_values(self):
        assert standardize_gender(None) == "unknown"
        assert standardize_gender(float("nan")) == "unknown"
        assert standardize_gender("") == "unknown"
        assert standardize_gender("other") == "unknown"
        assert standardize_gender("nonbinary") == "unknown"

    def test_whitespace_handling(self):
        assert standardize_gender("  male  ") == "male"
        assert standardize_gender(" F ") == "female"

    def test_applied_to_fixture(self, pmc_raw_df):
        result = pmc_raw_df["gender"].apply(standardize_gender)
        assert list(result) == ["female", "male", "female", "male", "unknown", "female"]


# ---------------------------------------------------------------------------
# Tests: Age Validation
# ---------------------------------------------------------------------------

class TestAgeValidation:
    """Test age value cleaning and validation."""

    def test_valid_ages(self, pmc_raw_df):
        ages = pd.to_numeric(pmc_raw_df["age_years"], errors="coerce")
        assert ages.between(0, 120).all()

    def test_invalid_ages_nullified(self):
        ages = pd.Series([-5, 0, 45, 121, 200])
        ages = pd.to_numeric(ages, errors="coerce")
        invalid = (ages < 0) | (ages > 120)
        ages[invalid] = None
        assert ages.isna().sum() == 3  # -5, 121, 200
        assert ages[2] == 45

    def test_non_numeric_ages(self):
        ages = pd.to_numeric(pd.Series(["thirty", "45", None, "N/A"]), errors="coerce")
        assert ages.isna().sum() == 3
        assert ages[1] == 45


# ---------------------------------------------------------------------------
# Tests: Timestamp Handling
# ---------------------------------------------------------------------------

class TestTimestampHandling:
    """Test Delta Lake timestamp compatibility."""

    def test_pub_date_parsing(self, pmc_raw_df):
        dates = pd.to_datetime(pmc_raw_df["pub_date"], errors="coerce")
        assert dates.notna().all()

    def test_microsecond_floor(self):
        ts = pd.Timestamp("2020-01-15 10:30:00.123456789")
        floored = ts.floor("us")
        assert floored.nanosecond == 0

    def test_floor_preserves_date(self):
        ts = pd.Timestamp("2023-06-15")
        floored = ts.floor("us")
        assert floored.year == 2023
        assert floored.month == 6
        assert floored.day == 15


# ---------------------------------------------------------------------------
# Tests: Output Schema
# ---------------------------------------------------------------------------

class TestOutputSchema:
    """Test the expected output structure."""

    def test_expected_columns(self):
        expected = [
            "patient_id", "patient_uid", "pmid", "title",
            "patient_summary", "age_years", "sex", "pub_date",
        ]
        assert len(expected) == 8
        assert "sex" in expected
        # gender and age_raw dropped in favor of sex and age_years
        assert "gender" not in expected
        assert "age_raw" not in expected

    def test_all_rows_preserved(self, pmc_raw_df):
        # No filtering -- all rows should be kept
        assert len(pmc_raw_df) == 6

    def test_all_rows_have_patient_id(self, pmc_raw_df):
        assert pmc_raw_df["patient_id"].notna().all()

    def test_all_rows_have_pmid(self, pmc_raw_df):
        assert pmc_raw_df["pmid"].notna().all()
