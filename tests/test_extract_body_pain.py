"""
Tests for notebooks/extract_body_pain.py.

Uses actual PMC-Patients parquet data as test fixtures.
Tests helper functions locally and LLM integration live against real summaries.
"""
import os
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


# ---------------------------------------------------------------------------
# Replicate helper functions from the notebook
# ---------------------------------------------------------------------------

def parse_body_pain_response(response_text):
    """Parse LLM response into list of body-part/pain-level dicts."""
    text = response_text.strip()

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

    return validated


def extract_body_pain_row(client, patient_summary):
    """Call Azure OpenAI to extract body-part/pain-level pairs from one summary."""
    if not patient_summary or pd.isna(patient_summary):
        return []

    text = patient_summary[:3000]
    prompt = f"Patient summary:\n{text}"

    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT41_MINI", "gpt-4.1-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=300,
    )
    reply = response.choices[0].message.content.strip()
    return parse_body_pain_response(reply)


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
def pain_rows(pmc_df):
    """Rows whose patient_summary contains the word 'pain'."""
    mask = pmc_df["patient_summary"].str.lower().str.contains("pain")
    return pmc_df[mask]


@pytest.fixture(scope="module")
def no_pain_rows(pmc_df):
    """Rows whose patient_summary does NOT contain the word 'pain'."""
    mask = ~pmc_df["patient_summary"].str.lower().str.contains("pain")
    return pmc_df[mask]


# ---------------------------------------------------------------------------
# Tests: Response Parsing (no LLM calls)
# ---------------------------------------------------------------------------

class TestParseBodyPainResponse:

    def test_valid_json_array(self):
        raw = '[{"body_part": "left knee", "pain_level": "moderate"}]'
        result = parse_body_pain_response(raw)
        assert len(result) == 1
        assert result[0]["body_part"] == "left knee"
        assert result[0]["pain_level"] == "moderate"

    def test_multiple_extractions(self):
        raw = json.dumps([
            {"body_part": "right knee", "pain_level": "severe"},
            {"body_part": "lower back", "pain_level": "mild"},
        ])
        result = parse_body_pain_response(raw)
        assert len(result) == 2

    def test_empty_array(self):
        assert parse_body_pain_response("[]") == []

    def test_none_string(self):
        assert parse_body_pain_response("none") == []

    def test_na_string(self):
        assert parse_body_pain_response("N/A") == []

    def test_empty_string(self):
        assert parse_body_pain_response("") == []

    def test_invalid_json(self):
        assert parse_body_pain_response("not json at all") == []

    def test_invalid_pain_level_dropped(self):
        raw = '[{"body_part": "knee", "pain_level": "extreme"}]'
        result = parse_body_pain_response(raw)
        assert len(result) == 0

    def test_empty_body_part_dropped(self):
        raw = '[{"body_part": "", "pain_level": "mild"}]'
        result = parse_body_pain_response(raw)
        assert len(result) == 0

    def test_markdown_code_fence_stripped(self):
        raw = '```json\n[{"body_part": "chest", "pain_level": "severe"}]\n```'
        result = parse_body_pain_response(raw)
        assert len(result) == 1
        assert result[0]["body_part"] == "chest"

    def test_object_wrapper_unwrapped(self):
        raw = '{"extractions": [{"body_part": "abdomen", "pain_level": "moderate"}]}'
        result = parse_body_pain_response(raw)
        assert len(result) == 1
        assert result[0]["body_part"] == "abdomen"

    def test_pain_level_case_insensitive(self):
        raw = '[{"body_part": "knee", "pain_level": "Moderate"}]'
        result = parse_body_pain_response(raw)
        assert len(result) == 1
        assert result[0]["pain_level"] == "moderate"

    def test_mixed_valid_and_invalid(self):
        raw = json.dumps([
            {"body_part": "knee", "pain_level": "mild"},
            {"body_part": "", "pain_level": "severe"},
            {"body_part": "back", "pain_level": "unknown"},
            {"body_part": "chest", "pain_level": "moderate"},
        ])
        result = parse_body_pain_response(raw)
        assert len(result) == 2
        assert result[0]["body_part"] == "knee"
        assert result[1]["body_part"] == "chest"

    def test_non_dict_items_skipped(self):
        raw = '[{"body_part": "knee", "pain_level": "mild"}, "invalid", 42]'
        result = parse_body_pain_response(raw)
        assert len(result) == 1

    def test_unknown_object_wrapper_returns_empty(self):
        raw = '{"unknown_key": [{"body_part": "knee", "pain_level": "mild"}]}'
        result = parse_body_pain_response(raw)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Tests: Fixture Integrity (real data, no LLM)
# ---------------------------------------------------------------------------

class TestFixtureIntegrity:

    def test_has_required_columns(self, pmc_df):
        required = ["patient_id", "title", "patient_summary"]
        for col in required:
            assert col in pmc_df.columns, f"Missing column: {col}"

    def test_has_pain_and_no_pain_cases(self, pmc_df):
        has_pain = pmc_df["patient_summary"].str.lower().str.contains("pain").any()
        has_no_pain = (~pmc_df["patient_summary"].str.lower().str.contains("pain")).any()
        assert has_pain, "Fixture should have cases mentioning pain"
        assert has_no_pain, "Fixture should have cases without pain"

    def test_summaries_not_empty(self, pmc_df):
        for _, row in pmc_df.iterrows():
            assert row["patient_summary"] and len(row["patient_summary"]) > 50, (
                f"Summary too short for {row['patient_id']}"
            )

    def test_row_count(self, pmc_df):
        assert len(pmc_df) >= 10, "Fixture should have at least 10 rows"


# ---------------------------------------------------------------------------
# Tests: Live LLM Integration (hits Azure OpenAI with real patient data)
# ---------------------------------------------------------------------------

class TestLLMExtraction:
    """Live integration tests - calls gpt-4.1-nano with real patient summaries."""

    def test_knee_pain_detected(self, llm_client, pmc_df):
        """pid=3245: right knee joint pain -> should extract knee."""
        row = pmc_df[pmc_df["patient_id"] == "3245"]
        if row.empty:
            pytest.skip("pid=3245 not in fixture")
        result = extract_body_pain_row(llm_client, row.iloc[0]["patient_summary"])
        assert len(result) >= 1
        body_parts = [e["body_part"].lower() for e in result]
        assert any("knee" in bp for bp in body_parts)

    def test_abdominal_pain_detected(self, llm_client, pmc_df):
        """pid=282: abdominal pain in Crohn's case -> should extract abdomen."""
        row = pmc_df[pmc_df["patient_id"] == "282"]
        if row.empty:
            pytest.skip("pid=282 not in fixture")
        result = extract_body_pain_row(llm_client, row.iloc[0]["patient_summary"])
        assert len(result) >= 1
        body_parts = [e["body_part"].lower() for e in result]
        assert any("abdom" in bp or "quadrant" in bp for bp in body_parts)

    def test_chest_pain_detected(self, llm_client, pmc_df):
        """pid=101: substernal chest pain -> should extract chest."""
        row = pmc_df[pmc_df["patient_id"] == "101"]
        if row.empty:
            pytest.skip("pid=101 not in fixture")
        result = extract_body_pain_row(llm_client, row.iloc[0]["patient_summary"])
        assert len(result) >= 1
        body_parts = [e["body_part"].lower() for e in result]
        assert any("chest" in bp or "substernal" in bp for bp in body_parts)

    def test_pleuritic_chest_pain_detected(self, llm_client, pmc_df):
        """pid=2439: pleuritic chest pain in Wegener's case."""
        row = pmc_df[pmc_df["patient_id"] == "2439"]
        if row.empty:
            pytest.skip("pid=2439 not in fixture")
        result = extract_body_pain_row(llm_client, row.iloc[0]["patient_summary"])
        assert len(result) >= 1
        body_parts = [e["body_part"].lower() for e in result]
        assert any("chest" in bp for bp in body_parts)

    def test_no_pain_case_returns_list(self, llm_client, pmc_df):
        """pid=2351: meningitis case with no pain in summary -> returns a list."""
        row = pmc_df[pmc_df["patient_id"] == "2351"]
        if row.empty:
            pytest.skip("pid=2351 not in fixture")
        result = extract_body_pain_row(llm_client, row.iloc[0]["patient_summary"])
        assert isinstance(result, list)

    def test_pain_levels_are_valid(self, llm_client, pain_rows):
        """All returned pain_level values must be mild/moderate/severe."""
        if pain_rows.empty:
            pytest.skip("No pain rows in fixture")
        row = pain_rows.iloc[0]
        result = extract_body_pain_row(llm_client, row["patient_summary"])
        for item in result:
            assert item["pain_level"] in VALID_PAIN_LEVELS, (
                f"Invalid pain level: {item['pain_level']}"
            )

    def test_body_parts_are_nonempty(self, llm_client, pain_rows):
        """All returned body_part values must be non-empty strings."""
        if pain_rows.empty:
            pytest.skip("No pain rows in fixture")
        row = pain_rows.iloc[0]
        result = extract_body_pain_row(llm_client, row["patient_summary"])
        for item in result:
            assert isinstance(item["body_part"], str)
            assert len(item["body_part"].strip()) > 0

    def test_result_is_json_serializable(self, llm_client, pain_rows):
        """Result should round-trip through JSON serialization."""
        if pain_rows.empty:
            pytest.skip("No pain rows in fixture")
        row = pain_rows.iloc[0]
        result = extract_body_pain_row(llm_client, row["patient_summary"])
        serialized = json.dumps(result)
        deserialized = json.loads(serialized)
        assert deserialized == result

    def test_none_summary_returns_empty(self):
        """None or empty summary should return empty list without LLM call."""
        result = extract_body_pain_row(None, None)
        assert result == []
        result = extract_body_pain_row(None, "")
        assert result == []

    def test_repeated_abdominal_pain(self, llm_client, pmc_df):
        """pid=850: multiple mentions of abdominal pain -> at least one extraction."""
        row = pmc_df[pmc_df["patient_id"] == "850"]
        if row.empty:
            pytest.skip("pid=850 not in fixture")
        result = extract_body_pain_row(llm_client, row.iloc[0]["patient_summary"])
        assert len(result) >= 1
        body_parts = [e["body_part"].lower() for e in result]
        assert any("abdom" in bp or "quadrant" in bp for bp in body_parts)

    def test_raw_llm_response_is_valid_json(self, llm_client, pmc_df):
        """Raw LLM response should be parseable as JSON."""
        row = pmc_df.iloc[0]
        text = row["patient_summary"][:3000]
        prompt = f"Patient summary:\n{text}"
        response = llm_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT41_MINI", "gpt-4.1-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=300,
        )
        reply = response.choices[0].message.content.strip()
        data = json.loads(reply)
        assert isinstance(data, (list, dict)), (
            f"Expected JSON array or object, got {type(data)}: {repr(reply)}"
        )

    def test_crohns_airway_case(self, llm_client, pmc_df):
        """pid=380: Crohn's with dyspnea -- all extractions should have valid pain levels."""
        row = pmc_df[pmc_df["patient_id"] == "380"]
        if row.empty:
            pytest.skip("pid=380 not in fixture")
        result = extract_body_pain_row(llm_client, row.iloc[0]["patient_summary"])
        assert isinstance(result, list)
        for item in result:
            assert item["pain_level"] in VALID_PAIN_LEVELS
