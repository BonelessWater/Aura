"""
Tests for download scripts (dataspec sections 5-13) and pipeline_remaining.

Tests verify:
- Module imports and function signatures
- URL/API endpoint correctness
- Download function error handling
- Pipeline task registry completeness
- Upload/verify/delete workflow logic
"""
import importlib
import os
import sys
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


class TestDownloadModuleImports(unittest.TestCase):
    """Verify all download modules can be imported and have correct signatures."""

    DOWNLOAD_MODULES = [
        "scripts.downloads.sec05_mendeley",
        "scripts.downloads.sec05_open_targets",
        "scripts.downloads.sec06_adex",
        "scripts.downloads.sec06_iaaa",
        "scripts.downloads.sec07_hca_eqtl",
        "scripts.downloads.sec07_allen_atlas",
        "scripts.downloads.sec08_hmp",
        "scripts.downloads.sec09_gwas_catalog",
        "scripts.downloads.sec09_pan_ukbb",
        "scripts.downloads.sec09_afnd",
        "scripts.downloads.sec09_immunobase",
        "scripts.downloads.sec10_olink",
        "scripts.downloads.sec10_hpa",
        "scripts.downloads.sec11_hmdb",
        "scripts.downloads.sec11_metabolights",
        "scripts.downloads.sec12_flaredown",
        "scripts.downloads.sec13_ctd",
        "scripts.downloads.sec13_epa_aqs",
    ]

    def test_all_modules_importable(self):
        """All 19 download modules should be importable."""
        for mod_name in self.DOWNLOAD_MODULES:
            with self.subTest(module=mod_name):
                mod = importlib.import_module(mod_name)
                self.assertIsNotNone(mod)

    def test_all_modules_have_download_function(self):
        """Each module must expose a download(local_path) function."""
        for mod_name in self.DOWNLOAD_MODULES:
            with self.subTest(module=mod_name):
                mod = importlib.import_module(mod_name)
                self.assertTrue(
                    hasattr(mod, "download"),
                    f"{mod_name} missing download() function",
                )
                self.assertTrue(callable(mod.download))

    def test_all_modules_have_logger(self):
        """Each module should configure logging."""
        for mod_name in self.DOWNLOAD_MODULES:
            with self.subTest(module=mod_name):
                mod = importlib.import_module(mod_name)
                self.assertTrue(
                    hasattr(mod, "logger"),
                    f"{mod_name} missing logger",
                )

    def test_all_modules_have_output_dir(self):
        """Each module should define OUTPUT_DIR."""
        for mod_name in self.DOWNLOAD_MODULES:
            with self.subTest(module=mod_name):
                mod = importlib.import_module(mod_name)
                self.assertTrue(
                    hasattr(mod, "OUTPUT_DIR"),
                    f"{mod_name} missing OUTPUT_DIR",
                )

    def test_module_count_matches_datasets(self):
        """Should have exactly 18 download modules (one per dataset)."""
        self.assertEqual(len(self.DOWNLOAD_MODULES), 18)


class TestPipelineRegistry(unittest.TestCase):
    """Verify pipeline_remaining task registry is complete and correct."""

    @classmethod
    def setUpClass(cls):
        cls.pipeline = importlib.import_module("scripts.pipeline_remaining")

    def test_registry_has_all_datasets(self):
        """Task registry should contain all 18 datasets."""
        self.assertEqual(len(self.pipeline.TASK_REGISTRY), 18)

    def test_registry_keys_match_expected(self):
        """Registry keys should match the expected dataset names."""
        expected = {
            "mendeley", "open_targets", "adex", "iaaa",
            "hca_eqtl", "allen_atlas", "hmp",
            "gwas_catalog", "pan_ukbb", "afnd", "immunobase",
            "olink", "hpa", "hmdb", "metabolights",
            "flaredown", "ctd", "epa_aqs",
        }
        self.assertEqual(set(self.pipeline.TASK_REGISTRY.keys()), expected)

    def test_registry_entries_have_required_fields(self):
        """Each registry entry must have module, filename, subdir, group, section."""
        required_fields = {"module", "filename", "subdir", "group", "section", "description"}
        for key, info in self.pipeline.TASK_REGISTRY.items():
            with self.subTest(dataset=key):
                for field in required_fields:
                    self.assertIn(
                        field, info,
                        f"Registry entry '{key}' missing field '{field}'",
                    )

    def test_registry_groups_valid(self):
        """All group values should be easy, medium, or hard."""
        valid_groups = {"easy", "medium", "hard"}
        for key, info in self.pipeline.TASK_REGISTRY.items():
            with self.subTest(dataset=key):
                self.assertIn(info["group"], valid_groups)

    def test_registry_sections_in_range(self):
        """All section numbers should be between 5 and 13."""
        for key, info in self.pipeline.TASK_REGISTRY.items():
            with self.subTest(dataset=key):
                self.assertGreaterEqual(info["section"], 5)
                self.assertLessEqual(info["section"], 13)

    def test_easy_group_count(self):
        """Should have 8 easy datasets."""
        easy = [k for k, v in self.pipeline.TASK_REGISTRY.items() if v["group"] == "easy"]
        self.assertEqual(len(easy), 8)

    def test_medium_group_count(self):
        """Should have 7 medium datasets."""
        medium = [k for k, v in self.pipeline.TASK_REGISTRY.items() if v["group"] == "medium"]
        self.assertEqual(len(medium), 7)

    def test_hard_group_count(self):
        """Should have 3 hard datasets."""
        hard = [k for k, v in self.pipeline.TASK_REGISTRY.items() if v["group"] == "hard"]
        self.assertEqual(len(hard), 3)


class TestPipelineFunctions(unittest.TestCase):
    """Test pipeline utility functions."""

    @classmethod
    def setUpClass(cls):
        cls.pipeline = importlib.import_module("scripts.pipeline_remaining")

    def test_volume_root_correct(self):
        """Volume root should match Databricks workspace path."""
        self.assertEqual(
            self.pipeline.VOLUME_ROOT,
            "dbfs:/Volumes/workspace/aura/aura_data",
        )

    @patch("scripts.pipeline_remaining.subprocess.run")
    def test_run_databricks_cmd_success(self, mock_run):
        """Successful databricks command should return (True, stdout)."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="success output", stderr="",
        )
        ok, out = self.pipeline.run_databricks_cmd(["fs", "ls", "/test"])
        self.assertTrue(ok)
        self.assertEqual(out, "success output")

    @patch("scripts.pipeline_remaining.subprocess.run")
    def test_run_databricks_cmd_failure(self, mock_run):
        """Failed databricks command should return (False, stderr)."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="error message",
        )
        ok, out = self.pipeline.run_databricks_cmd(["fs", "cp", "a", "b"])
        self.assertFalse(ok)
        self.assertEqual(out, "error message")

    @patch("scripts.pipeline_remaining.subprocess.run")
    def test_run_databricks_cmd_timeout(self, mock_run):
        """Timed-out databricks command should return (False, 'timeout')."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="databricks", timeout=300)
        ok, out = self.pipeline.run_databricks_cmd(["fs", "cp", "a", "b"])
        self.assertFalse(ok)
        self.assertEqual(out, "timeout")

    def test_make_download_fn_returns_callable(self):
        """make_download_fn should return a callable wrapper."""
        fn = self.pipeline.make_download_fn("sec13_ctd")
        self.assertTrue(callable(fn))

    def test_build_tasks_creates_tuples(self):
        """build_tasks should create (fn, path, subdir, label) tuples."""
        tasks = self.pipeline.build_tasks(["ctd", "flaredown"])
        self.assertEqual(len(tasks), 2)
        for task in tasks:
            self.assertEqual(len(task), 4)
            fn, path, subdir, label = task
            self.assertTrue(callable(fn))
            self.assertIsInstance(path, str)
            self.assertIsInstance(subdir, str)
            self.assertIsInstance(label, str)


class TestDownloadErrorHandling(unittest.TestCase):
    """Test that download functions handle errors gracefully."""

    @patch("scripts.downloads.sec05_mendeley.requests.get")
    def test_mendeley_handles_api_error(self, mock_get):
        """Mendeley download should handle API errors gracefully."""
        import requests
        mock_get.side_effect = requests.RequestException("Connection refused")
        mod = importlib.import_module("scripts.downloads.sec05_mendeley")
        result = mod.download("/tmp/test_mendeley.zip")
        self.assertFalse(result)

    @patch("scripts.downloads.sec05_open_targets.requests.post")
    def test_open_targets_handles_api_error(self, mock_post):
        """Open Targets should handle GraphQL API errors."""
        import requests
        mock_post.side_effect = requests.RequestException("Timeout")
        mod = importlib.import_module("scripts.downloads.sec05_open_targets")
        result = mod.download("/tmp/test_ot.parquet")
        self.assertFalse(result)

    @patch("scripts.downloads.sec13_ctd.requests.get")
    def test_ctd_handles_download_error(self, mock_get):
        """CTD should handle HTTP download errors."""
        import requests
        mock_get.side_effect = requests.RequestException("404 Not Found")
        mod = importlib.import_module("scripts.downloads.sec13_ctd")
        result = mod.download("/tmp/test_ctd.tsv.gz")
        self.assertFalse(result)


class TestURLConstants(unittest.TestCase):
    """Verify critical URL constants are correctly defined."""

    def test_open_targets_graphql_url(self):
        mod = importlib.import_module("scripts.downloads.sec05_open_targets")
        self.assertEqual(
            mod.OT_GRAPHQL,
            "https://api.platform.opentargets.org/api/v4/graphql",
        )

    def test_gwas_catalog_api_url(self):
        mod = importlib.import_module("scripts.downloads.sec09_gwas_catalog")
        self.assertEqual(
            mod.GWAS_API,
            "https://www.ebi.ac.uk/gwas/rest/api",
        )

    def test_hca_project_uuid(self):
        mod = importlib.import_module("scripts.downloads.sec07_hca_eqtl")
        self.assertEqual(
            mod.HCA_PROJECT_UUID,
            "f2078d5f-2e7d-4844-8552-f7c41a231e52",
        )

    def test_ctd_download_base(self):
        mod = importlib.import_module("scripts.downloads.sec13_ctd")
        self.assertEqual(
            mod.CTD_DOWNLOAD_BASE,
            "https://ctdbase.org/reports/",
        )

    def test_epa_aqs_base(self):
        mod = importlib.import_module("scripts.downloads.sec13_epa_aqs")
        self.assertEqual(
            mod.AQS_BASE,
            "https://aqs.epa.gov/aqsweb/airdata",
        )

    def test_hpa_download_base(self):
        mod = importlib.import_module("scripts.downloads.sec10_hpa")
        self.assertEqual(
            mod.HPA_DOWNLOAD_BASE,
            "https://www.proteinatlas.org/download",
        )

    def test_flaredown_kaggle_dataset(self):
        mod = importlib.import_module("scripts.downloads.sec12_flaredown")
        self.assertEqual(
            mod.KAGGLE_DATASET,
            "flaredown/flaredown-autoimmune-symptom-tracker",
        )


class TestUploadVerifyDelete(unittest.TestCase):
    """Test the upload_verify_delete workflow."""

    @classmethod
    def setUpClass(cls):
        cls.pipeline = importlib.import_module("scripts.pipeline_remaining")

    @patch("scripts.pipeline_remaining.run_databricks_cmd")
    @patch("scripts.pipeline_remaining.os.remove")
    @patch("scripts.pipeline_remaining.os.path.getsize")
    def test_upload_verify_delete_success(self, mock_size, mock_remove, mock_cmd):
        """Successful upload should verify and delete local file."""
        mock_size.return_value = 1000000  # 1 MB

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            f.write(b"test data")
            tmp_path = f.name

        # Use actual basename so verify check matches
        basename = os.path.basename(tmp_path)
        mock_cmd.side_effect = [
            (True, "uploaded"),  # upload
            (True, basename),   # verify (ls output contains filename)
        ]

        try:
            result = self.pipeline.upload_verify_delete(tmp_path, "test_subdir")
            self.assertTrue(result)
            mock_remove.assert_called_once_with(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @patch("scripts.pipeline_remaining.run_databricks_cmd")
    @patch("scripts.pipeline_remaining.os.path.getsize")
    def test_upload_verify_delete_upload_fails(self, mock_size, mock_cmd):
        """Failed upload should return False without deleting."""
        mock_size.return_value = 1000000
        mock_cmd.return_value = (False, "upload error")

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            f.write(b"test data")
            tmp_path = f.name

        try:
            result = self.pipeline.upload_verify_delete(tmp_path, "test_subdir")
            self.assertFalse(result)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @patch("scripts.pipeline_remaining.run_databricks_cmd")
    @patch("scripts.pipeline_remaining.os.path.getsize")
    def test_upload_verify_delete_verify_fails(self, mock_size, mock_cmd):
        """Failed verification should return False."""
        mock_size.return_value = 1000000
        mock_cmd.side_effect = [
            (True, "uploaded"),  # upload succeeds
            (True, "other_file.txt"),  # verify fails (filename not in ls output)
        ]

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            f.write(b"test data")
            tmp_path = f.name

        try:
            result = self.pipeline.upload_verify_delete(tmp_path, "test_subdir")
            self.assertFalse(result)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestDiseaseConstants(unittest.TestCase):
    """Verify disease/phenotype constants across modules are consistent."""

    def test_open_targets_has_core_autoimmune_diseases(self):
        mod = importlib.import_module("scripts.downloads.sec05_open_targets")
        disease_names = set(mod.AUTOIMMUNE_DISEASES.values())
        core = {"rheumatoid arthritis", "systemic lupus erythematosus",
                "Crohn disease", "ulcerative colitis", "multiple sclerosis"}
        for d in core:
            self.assertIn(d, disease_names, f"Missing {d} from Open Targets diseases")

    def test_gwas_catalog_has_core_autoimmune_traits(self):
        mod = importlib.import_module("scripts.downloads.sec09_gwas_catalog")
        trait_names = set(mod.AUTOIMMUNE_EFOS.values())
        core = {"rheumatoid arthritis", "Crohn's disease",
                "multiple sclerosis", "celiac disease"}
        for t in core:
            self.assertIn(t, trait_names, f"Missing {t} from GWAS Catalog traits")

    def test_afnd_has_key_hla_alleles(self):
        mod = importlib.import_module("scripts.downloads.sec09_afnd")
        self.assertIn("B*27:05", mod.AUTOIMMUNE_HLA)  # AS
        self.assertIn("DRB1*04:01", mod.AUTOIMMUNE_HLA)  # RA
        self.assertIn("DRB1*15:01", mod.AUTOIMMUNE_HLA)  # MS


if __name__ == "__main__":
    unittest.main()
