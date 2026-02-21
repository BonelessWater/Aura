"""
DatabricksClient — thin singleton wrapper around the Databricks SDK.

Provides:
  - SQL statement execution (with polling)
  - Feature Store read/write (databricks-feature-engineering)
  - Vector Search index access
  - MLflow experiment helpers
"""

from __future__ import annotations

import time
from typing import Any, Optional

import mlflow
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

WAREHOUSE_ID = "a3f84fea6e440a44"
CATALOG      = "aura"


class DatabricksClient:
    _instance: Optional[DatabricksClient] = None

    def __new__(cls) -> DatabricksClient:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self.w            = WorkspaceClient()   # reads ~/.databrickscfg
        self.warehouse_id = WAREHOUSE_ID
        self.catalog      = CATALOG
        self._vs_client: Any = None

    # ── SQL ──────────────────────────────────────────────────────────────────

    def run_sql(self, sql: str, desc: str = "") -> list[list]:
        """
        Execute SQL, poll until done, return data_array (list of rows).
        Raises RuntimeError on failure.
        """
        r     = self.w.statement_execution.execute_statement(
            warehouse_id=self.warehouse_id,
            statement=sql,
            wait_timeout="50s",
        )
        stmt  = r.statement_id
        state = r.status.state
        polls = 0
        while state in (StatementState.PENDING, StatementState.RUNNING) and polls < 180:
            time.sleep(5)
            polls += 1
            r     = self.w.statement_execution.get_statement(stmt)
            state = r.status.state
        if state != StatementState.SUCCEEDED:
            raise RuntimeError(
                f"SQL failed [{state}]: {r.status.error}\n  SQL: {sql[:300]}"
            )
        if r.result and r.result.data_array:
            return r.result.data_array
        return []

    def create_schema(self, schema: str) -> None:
        self.run_sql(f"CREATE SCHEMA IF NOT EXISTS {self.catalog}.{schema}")

    def create_table_as(self, table: str, select_sql: str) -> None:
        self.run_sql(f"CREATE OR REPLACE TABLE {table} AS {select_sql}")

    # ── Feature Store ─────────────────────────────────────────────────────────

    def get_feature_store(self):
        """Return a FeatureEngineeringClient (databricks-feature-engineering)."""
        try:
            from databricks.feature_engineering import FeatureEngineeringClient
            return FeatureEngineeringClient()
        except ImportError:
            # Fallback to older package name
            from databricks.feature_store import FeatureStoreClient
            return FeatureStoreClient()

    # ── Vector Search ─────────────────────────────────────────────────────────

    def get_vs_client(self):
        """Return a VectorSearchClient (databricks-vectorsearch)."""
        if self._vs_client is None:
            from databricks.vector_search.client import VectorSearchClient
            self._vs_client = VectorSearchClient()
        return self._vs_client

    def get_vs_index(self, endpoint: str, index_name: str):
        """Get a VS index handle for similarity search or upsert."""
        return self.get_vs_client().get_index(
            endpoint_name=endpoint,
            index_name=index_name,
        )

    # ── MLflow ────────────────────────────────────────────────────────────────

    def setup_mlflow(self, experiment_name: str) -> str:
        """Configure MLflow to use Databricks tracking, return experiment_id."""
        mlflow.set_tracking_uri("databricks")
        exp = mlflow.set_experiment(experiment_name)
        return exp.experiment_id

    # ── File (Volume) upload ──────────────────────────────────────────────────

    def upload_file(self, local_path: str, volume_path: str) -> None:
        with open(local_path, "rb") as f:
            self.w.files.upload(volume_path, f, overwrite=True)

    def upload_bytes(self, buf, volume_path: str) -> None:
        import io
        if not isinstance(buf, io.IOBase):
            buf = io.BytesIO(buf)
        buf.seek(0)
        self.w.files.upload(volume_path, buf, overwrite=True)


# Convenience singleton accessor
def get_client() -> DatabricksClient:
    return DatabricksClient()
