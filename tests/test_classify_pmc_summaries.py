"""
Tests for notebooks/classify_pmc_summaries.py.

Uses actual PMC-Patients parquet data as test fixtures.
Tests helper functions locally and LLM integration live against real summaries.
"""
import os
import re
import json
import logging

import pandas as pd
import pytest
from dotenv import load_dotenv
from openai import AzureOpenAI

logger = logging.getLogger(__name__)

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "pmc_sample.parquet"
)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ---------------------------------------------------------------------------
# Replicate helper functions from the notebook
# ---------------------------------------------------------------------------

def split_into_sentences(text):
    if not text or pd.isna(text):
        return []
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    return [(i + 1, s) for i, s in enumerate(sentences)]


def format_numbered_lines(sentences):
    return "\n".join(f"{num}: {text}" for num, text in sentences)


def parse_diagnosis_response(response_text):
    text = response_text.strip().lower()
    if text in ("none", "n/a", "null", ""):
        return None
    return response_text.strip()


def parse_line_numbers(response_text):
    text = response_text.strip().lower()
    if text in ("none", "n/a", "null", ""):
        return []
    numbers = re.findall(r'\d+', text)
    return [int(n) for n in numbers]


def build_text_from_lines(sentences, line_numbers):
    sentence_map = {num: text for num, text in sentences}
    parts = [sentence_map[n] for n in sorted(line_numbers) if n in sentence_map]
    return " ".join(parts) if parts else ""


def classify_row(client, title, patient_summary):
    """Call Azure OpenAI to classify one patient row."""
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

    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT41_NANO", "gpt-4.1-nano"),
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pmc_df():
    assert os.path.exists(FIXTURE_PATH), f"Fixture not found: {FIXTURE_PATH}"
    df = pd.read_parquet(FIXTURE_PATH)
    assert len(df) > 0, "Fixture parquet is empty"
    return df


@pytest.fixture(scope="module")
def llm_client():
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not endpoint or not api_key:
        pytest.skip("AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY not set")
    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
    )


@pytest.fixture(scope="module")
def autoimmune_rows(pmc_df):
    keywords = [
        "rheumatoid arthritis", "crohn", "psoriasis", "lupus",
        "multiple sclerosis", "type 1 diabetes",
    ]
    mask = pmc_df["title"].str.lower().apply(
        lambda t: any(kw in t for kw in keywords)
    )
    return pmc_df[mask]


@pytest.fixture(scope="module")
def control_rows(pmc_df):
    keywords = [
        "rheumatoid arthritis", "crohn", "psoriasis", "lupus",
        "multiple sclerosis", "type 1 diabetes", "sarcoidosis",
    ]
    mask = pmc_df["title"].str.lower().apply(
        lambda t: not any(kw in t for kw in keywords)
    )
    return pmc_df[mask]


# ---------------------------------------------------------------------------
# Tests: Sentence Splitting (on real data)
# ---------------------------------------------------------------------------

class TestSentenceSplitting:

    def test_real_summary_splits(self, pmc_df):
        row = pmc_df.iloc[0]
        sentences = split_into_sentences(row["patient_summary"])
        assert len(sentences) > 0
        assert sentences[0][0] == 1
        for i, (num, _) in enumerate(sentences):
            assert num == i + 1

    def test_all_rows_produce_sentences(self, pmc_df):
        for _, row in pmc_df.iterrows():
            sentences = split_into_sentences(row["patient_summary"])
            assert len(sentences) > 0, f"No sentences for {row['patient_id']}"

    def test_no_empty_sentences(self, pmc_df):
        for _, row in pmc_df.iterrows():
            sentences = split_into_sentences(row["patient_summary"])
            for num, text in sentences:
                assert text.strip(), f"Empty sentence {num} in {row['patient_id']}"

    def test_none_input(self):
        assert split_into_sentences(None) == []

    def test_nan_input(self):
        assert split_into_sentences(float("nan")) == []

    def test_sentence_count_reasonable(self, pmc_df):
        for _, row in pmc_df.iterrows():
            sentences = split_into_sentences(row["patient_summary"])
            assert len(sentences) >= 2, (
                f"Too few sentences ({len(sentences)}) for {row['patient_id']}"
            )


class TestFormatNumberedLines:

    def test_real_summary_format(self, pmc_df):
        sentences = split_into_sentences(pmc_df.iloc[0]["patient_summary"])
        formatted = format_numbered_lines(sentences)
        lines = formatted.split("\n")
        assert lines[0].startswith("1: ")
        assert lines[1].startswith("2: ")

    def test_round_trip(self, pmc_df):
        for _, row in pmc_df.head(5).iterrows():
            sentences = split_into_sentences(row["patient_summary"])
            formatted = format_numbered_lines(sentences)
            for num, text in sentences:
                assert text in formatted


# ---------------------------------------------------------------------------
# Tests: Response Parsing
# ---------------------------------------------------------------------------

class TestParseDiagnosisResponse:

    def test_disease_name(self):
        assert parse_diagnosis_response("rheumatoid arthritis") == "rheumatoid arthritis"

    def test_none_string(self):
        assert parse_diagnosis_response("none") is None

    def test_na_string(self):
        assert parse_diagnosis_response("N/A") is None

    def test_empty(self):
        assert parse_diagnosis_response("") is None

    def test_preserves_case(self):
        assert parse_diagnosis_response("Crohn's disease") == "Crohn's disease"

    def test_whitespace_stripped(self):
        assert parse_diagnosis_response("  lupus  ") == "lupus"


class TestParseLineNumbers:

    def test_simple(self):
        assert parse_line_numbers("3, 7") == [3, 7]

    def test_single(self):
        assert parse_line_numbers("5") == [5]

    def test_none_string(self):
        assert parse_line_numbers("none") == []

    def test_empty(self):
        assert parse_line_numbers("") == []

    def test_messy_format(self):
        assert parse_line_numbers("Lines 3, 7, and 12") == [3, 7, 12]

    def test_with_prefix(self):
        assert parse_line_numbers("Q2: 3, 7") == [2, 3, 7]


# ---------------------------------------------------------------------------
# Tests: Text Reconstruction (on real data)
# ---------------------------------------------------------------------------

class TestBuildTextFromLines:

    def test_real_summary_subset(self, pmc_df):
        sentences = split_into_sentences(pmc_df.iloc[0]["patient_summary"])
        text = build_text_from_lines(sentences, [1, 2])
        assert sentences[0][1] in text
        assert sentences[1][1] in text

    def test_empty_lines(self, pmc_df):
        sentences = split_into_sentences(pmc_df.iloc[0]["patient_summary"])
        assert build_text_from_lines(sentences, []) == ""

    def test_out_of_range_ignored(self, pmc_df):
        sentences = split_into_sentences(pmc_df.iloc[0]["patient_summary"])
        text = build_text_from_lines(sentences, [1, 9999])
        assert sentences[0][1] in text

    def test_diag_and_prelim_cover_all(self, pmc_df):
        sentences = split_into_sentences(pmc_df.iloc[0]["patient_summary"])
        all_nums = [n for n, _ in sentences]
        diag = [1, 3]
        prelim = [n for n in all_nums if n not in diag]
        diag_text = build_text_from_lines(sentences, diag)
        prelim_text = build_text_from_lines(sentences, prelim)
        for num, text in sentences:
            if num in diag:
                assert text in diag_text
            else:
                assert text in prelim_text


# ---------------------------------------------------------------------------
# Tests: Live LLM Integration (hits Azure OpenAI with real patient data)
# ---------------------------------------------------------------------------

class TestLLMClassification:
    """Live integration tests - calls gpt-4.1-nano with real patient summaries."""

    def test_case_returns_diagnosis(self, llm_client, pmc_df):
        """Every case report should return a non-null diagnosis."""
        row = pmc_df.iloc[0]
        result = classify_row(llm_client, row["title"], row["patient_summary"])
        assert result["diagnosis"] is not None
        assert len(result["diagnosis"]) > 2

    def test_diagnosis_matches_title_focus(self, llm_client, pmc_df):
        """Diagnosis should reflect the primary focus of the case, not background history."""
        # Title: "Adalimumab induced mononeuritis multiplex in a patient with RA"
        # The case is ABOUT mononeuritis multiplex, not RA
        ra_rows = pmc_df[
            pmc_df["title"].str.lower().str.contains("mononeuritis")
        ]
        if ra_rows.empty:
            pytest.skip("No mononeuritis row in fixture")
        row = ra_rows.iloc[0]
        result = classify_row(llm_client, row["title"], row["patient_summary"])
        assert result["diagnosis"] is not None
        assert "mononeuritis" in result["diagnosis"].lower()

    def test_psoriasis_case_gets_diagnosis(self, llm_client, pmc_df):
        """Psoriasis-focused case should return psoriasis."""
        pso_rows = pmc_df[
            pmc_df["title"].str.lower().str.contains("psoriasis vulgaris flare")
        ]
        if pso_rows.empty:
            pytest.skip("No psoriasis rows in fixture")
        row = pso_rows.iloc[0]
        result = classify_row(llm_client, row["title"], row["patient_summary"])
        assert result["diagnosis"] is not None
        assert "psoriasis" in result["diagnosis"].lower()

    def test_cancer_case_gets_cancer(self, llm_client, pmc_df):
        """Cancer-focused case (even with Crohn's background) should return the cancer."""
        cancer_rows = pmc_df[
            pmc_df["title"].str.lower().str.contains("adenocarcinoma")
        ]
        if cancer_rows.empty:
            pytest.skip("No adenocarcinoma row in fixture")
        row = cancer_rows.iloc[0]
        result = classify_row(llm_client, row["title"], row["patient_summary"])
        assert result["diagnosis"] is not None
        assert "carcinoma" in result["diagnosis"].lower() or "cancer" in result["diagnosis"].lower()

    def test_diagnosis_lines_are_valid(self, llm_client, autoimmune_rows):
        """Diagnosis line numbers should be within range of actual sentences."""
        if autoimmune_rows.empty:
            pytest.skip("No autoimmune rows in fixture")
        row = autoimmune_rows.iloc[0]
        result = classify_row(llm_client, row["title"], row["patient_summary"])
        sentences = split_into_sentences(row["patient_summary"])
        max_line = len(sentences)
        for ln in result["diagnosis_lines"]:
            assert 1 <= ln <= max_line, (
                f"Line {ln} out of range (1-{max_line})"
            )

    def test_diagnosis_lines_not_empty_for_autoimmune(self, llm_client, autoimmune_rows):
        """Autoimmune cases should have at least one diagnosis line."""
        if autoimmune_rows.empty:
            pytest.skip("No autoimmune rows in fixture")
        row = autoimmune_rows.iloc[0]
        result = classify_row(llm_client, row["title"], row["patient_summary"])
        assert len(result["diagnosis_lines"]) > 0, (
            "Autoimmune case should have diagnosis lines"
        )

    def test_preliminary_lines_not_empty(self, llm_client, autoimmune_rows):
        """Autoimmune cases should have preliminary (presentation) lines too."""
        if autoimmune_rows.empty:
            pytest.skip("No autoimmune rows in fixture")
        row = autoimmune_rows.iloc[0]
        result = classify_row(llm_client, row["title"], row["patient_summary"])
        assert len(result["preliminary_lines"]) > 0, (
            "Case should have preliminary/presentation lines"
        )

    def test_no_overlap_between_diag_and_prelim(self, llm_client, autoimmune_rows):
        """Diagnosis and preliminary lines should not overlap."""
        if autoimmune_rows.empty:
            pytest.skip("No autoimmune rows in fixture")
        row = autoimmune_rows.iloc[0]
        result = classify_row(llm_client, row["title"], row["patient_summary"])
        overlap = set(result["diagnosis_lines"]) & set(result["preliminary_lines"])
        assert len(overlap) == 0, f"Lines in both sets: {overlap}"

    def test_all_lines_accounted_for(self, llm_client, autoimmune_rows):
        """Every sentence should be in either diagnosis or preliminary."""
        if autoimmune_rows.empty:
            pytest.skip("No autoimmune rows in fixture")
        row = autoimmune_rows.iloc[0]
        result = classify_row(llm_client, row["title"], row["patient_summary"])
        sentences = split_into_sentences(row["patient_summary"])
        all_nums = set(n for n, _ in sentences)
        classified = set(result["diagnosis_lines"]) | set(result["preliminary_lines"])
        # classified should cover all lines (diagnosis_lines from LLM,
        # preliminary_lines = everything else)
        assert all_nums == classified, (
            f"Missing lines: {all_nums - classified}"
        )

    def test_reconstructed_text_preserves_content(self, llm_client, autoimmune_rows):
        """Splitting by line numbers and rejoining should preserve all sentence text."""
        if autoimmune_rows.empty:
            pytest.skip("No autoimmune rows in fixture")
        row = autoimmune_rows.iloc[0]
        result = classify_row(llm_client, row["title"], row["patient_summary"])
        sentences = split_into_sentences(row["patient_summary"])
        diag_text = build_text_from_lines(sentences, result["diagnosis_lines"])
        prelim_text = build_text_from_lines(sentences, result["preliminary_lines"])
        for num, text in sentences:
            if num in result["diagnosis_lines"]:
                assert text in diag_text
            else:
                assert text in prelim_text

    def test_response_is_two_lines(self, llm_client, pmc_df):
        """Raw LLM response should be exactly two lines."""
        row = pmc_df.iloc[0]
        sentences = split_into_sentences(row["patient_summary"])
        numbered = format_numbered_lines(sentences)

        prompt = (
            f"Title: {row['title']}\n\n"
            f"Lines:\n{numbered}\n\n"
            "Q1: What disease is this about? One phrase or none.\n"
            "Q2: Which line numbers mention the diagnosis? Numbers only or none."
        )
        response = llm_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT41_NANO", "gpt-4.1-nano"),
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
        assert len(lines) == 2, (
            f"Expected 2 lines, got {len(lines)}: {repr(reply)}"
        )


# ---------------------------------------------------------------------------
# Tests: Fixture Integrity
# ---------------------------------------------------------------------------

class TestFixtureIntegrity:

    def test_has_required_columns(self, pmc_df):
        required = ["patient_id", "title", "patient_summary"]
        for col in required:
            assert col in pmc_df.columns, f"Missing column: {col}"

    def test_has_autoimmune_and_control(self, pmc_df):
        titles_lower = pmc_df["title"].str.lower()
        has_autoimmune = titles_lower.str.contains(
            "rheumatoid|crohn|psoriasis|lupus", regex=True
        ).any()
        has_control = titles_lower.str.contains(
            "pneumonia|myocardial|cancer", regex=True
        ).any()
        assert has_autoimmune, "Fixture should have autoimmune cases"
        assert has_control, "Fixture should have non-autoimmune cases"

    def test_summaries_not_empty(self, pmc_df):
        for _, row in pmc_df.iterrows():
            assert row["patient_summary"] and len(row["patient_summary"]) > 50, (
                f"Summary too short for {row['patient_id']}"
            )

    def test_row_count(self, pmc_df):
        assert len(pmc_df) >= 10, "Fixture should have at least 10 rows"
