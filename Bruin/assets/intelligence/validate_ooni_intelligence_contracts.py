"""@bruin
name: intelligence.validate_ooni_intelligence_contracts
type: python
image: python:3.12
connection: duckdb-parquet

tags:
  - validation
  - intelligence_bq
  - dataset_ooni

description: |
  Validates OONI intelligence contract tables in BigQuery.

  Read-only contract validator for intelligence outputs.

  Performs:
    - schema contract validation
    - uniqueness checks
    - nullability checks
    - intelligence output contract enforcement

depends:
  - intelligence.protocol_signal_regimes
  - intelligence.protocol_lag_relationships
  - intelligence.protocol_relationships

materialization:
  type: table
  strategy: create+replace
@bruin"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from google.cloud import bigquery


PROJECT_ID = "encoded-joy-485413-k5"


CONTRACTS = {
    f"{PROJECT_ID}.intelligence.protocol_signal_regimes": {
        "id_column": "regime_id",
        "required_columns": {
            "regime_id",
            "measurement_date",
            "country",
            "protocol",
            "protocol_state",
            "baseline_divergence_state",
            "confidence_level",
            "statistical_warning_flags",
            "intelligence_guardrail_config_json",
            "intelligence_version",
            "computed_at",
        },
    },
    f"{PROJECT_ID}.intelligence.protocol_lag_relationships": {
        "id_column": "lag_relationship_id",
        "required_columns": {
            "lag_relationship_id",
            "measurement_date",
            "country",
            "target_protocol",
            "driver_protocol",
            "lag_days",
            "guarded_lag_correlation",
            "relationship_state",
            "relationship_sample_count",
            "insufficient_sample_flag",
            "zero_variance_flag",
            "intelligence_guardrail_config_json",
            "intelligence_version",
            "computed_at",
        },
    },
    f"{PROJECT_ID}.intelligence.protocol_relationships": {
        "id_column": "protocol_relationship_id",
        "required_columns": {
            "protocol_relationship_id",
            "measurement_date",
            "country",
            "protocol",
            "protocol_state",
            "intelligence_state",
            "final_confidence_level",
            "final_confidence_score",
            "statistical_warning_flags",
            "intelligence_version",
            "computed_at",
        },
    },
}


def _fetch_metrics(
    client: bigquery.Client,
    table_id: str,
    id_column: str,
) -> dict:
    query = f"""
    SELECT
        COUNT(*) AS row_count,
        COUNT(DISTINCT {id_column}) AS distinct_ids,
        COUNTIF({id_column} IS NULL) AS null_ids
    FROM `{table_id}`
    """

    rows = client.query(query).result()
    row = next(rows)

    return dict(row.items())


def _schema_failures(
    table: bigquery.Table,
    required_columns: set[str],
) -> list[str]:
    actual_columns = {field.name for field in table.schema}

    missing = sorted(required_columns - actual_columns)

    if not missing:
        return []

    return [f"missing_columns={','.join(missing)}"]


def _metric_failures(metrics: dict) -> list[str]:
    failures = []

    row_count = int(metrics["row_count"])
    distinct_ids = int(metrics["distinct_ids"])

    if row_count != distinct_ids:
        failures.append("id_not_unique")

    if int(metrics["null_ids"]) > 0:
        failures.append("null_ids")

    return failures


def validate_table(
    client: bigquery.Client,
    table_id: str,
    contract: dict[str, object],
) -> dict[str, object]:
    table = client.get_table(table_id)

    required_columns = set(contract["required_columns"])
    id_column = str(contract["id_column"])

    schema_failures = _schema_failures(
        table,
        required_columns,
    )

    metrics = _fetch_metrics(
        client,
        table_id,
        id_column,
    )

    metric_failures = _metric_failures(metrics)

    failures = schema_failures + metric_failures

    return {
        "table_id": table_id,
        "status": "failed" if failures else "passed",
        "hard_failures": ",".join(failures),
        "row_count": int(metrics["row_count"]),
        "distinct_ids": int(metrics["distinct_ids"]),
        "validated_at": datetime.now(
            timezone.utc
        ),
    }


def materialize() -> pd.DataFrame:
    client = bigquery.Client(project=PROJECT_ID)

    rows = [
        validate_table(
            client,
            table_id,
            contract,
        )
        for table_id, contract in CONTRACTS.items()
    ]

    return pd.DataFrame(rows)
