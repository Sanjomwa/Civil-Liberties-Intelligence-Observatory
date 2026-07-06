"""@bruin
name: reporting.validate_pressure_attribution_contracts
type: python
image: python:3.12
connection: duckdb-parquet

tags:
  - validation
  - reporting

description: |
  Validates the four ADR-0006 pressure-attribution reporting marts in
  BigQuery, mirroring intelligence.validate_ooni_intelligence_contracts
  (the established contract-validator pattern in this repo).

  Read-only contract validator for the attribution leaf marts.

  Performs:
    - schema contract validation (required columns present)
    - grain uniqueness checks (composite natural keys -- three of the
      four marts have no single id column, by design: they are leaf
      marts at their sources' natural grains, per ADR-0006)
    - nullability checks on the grain key columns

  The arithmetic tripwire (attribution_residual) is NOT re-checked here;
  it is enforced at materialization time by
  mart_pressure_attribution_daily's own custom_checks block (TD-57).

depends:
  - reporting.mart_pressure_attribution_daily
  - reporting.mart_pressure_attribution_conflict_drivers
  - reporting.mart_pressure_attribution_platform_drivers
  - reporting.mart_pressure_attribution_ooni_daily

materialization:
  type: table
  strategy: create+replace
@bruin"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd
from google.cloud import bigquery


PROJECT_ID = os.getenv(
    "GOOGLE_CLOUD_PROJECT",
    "encoded-joy-485413-k5"
)


# key_columns define each mart's declared grain (see each asset's
# GRAIN note); uniqueness is asserted over their concatenation.
CONTRACTS = {
    f"{PROJECT_ID}.reporting.mart_pressure_attribution_daily": {
        "key_columns": ["measurement_date"],
        "required_columns": {
            "measurement_date",
            "country",
            "iso2",
            "composite_pressure_score",
            "pressure_level",
            "conflict_pressure_score",
            "conflict_weight",
            "conflict_contribution",
            "conflict_week_start_date",
            "conflict_data_grain",
            "platform_pressure_score",
            "platform_weight",
            "platform_contribution",
            "platform_period_start",
            "platform_data_grain",
            "conflict_share",
            "platform_share",
            "attribution_residual",
            "composite_delta_7d",
            "attribution_methodology_version",
            "reporting_version",
            "snapshot_at",
        },
    },
    f"{PROJECT_ID}.reporting.mart_pressure_attribution_conflict_drivers": {
        "key_columns": [
            "week_start_date",
            "admin1",
            "event_type",
            "sub_event_type",
            "disorder_type",
        ],
        "required_columns": {
            "week_start_date",
            "country",
            "admin1",
            "event_type",
            "sub_event_type",
            "events",
            "fatalities",
            "pressure_domain",
            "severity_tier",
            "classification_confidence",
            "methodology_risk_level",
            "intensity_mass",
            "week_intensity_mass",
            "weekly_intensity_share",
            "weekly_intensity_rank",
            "attribution_methodology_version",
            "reporting_version",
            "snapshot_at",
        },
    },
    f"{PROJECT_ID}.reporting.mart_pressure_attribution_platform_drivers": {
        "key_columns": ["period_start", "product", "reason"],
        "required_columns": {
            "period_start",
            "period_end",
            "product",
            "reason",
            "removal_items",
            "period_detailed_total",
            "period_detailed_share",
            "period_share_rank",
            "google_requests",
            "attribution_methodology_version",
            "reporting_version",
            "snapshot_at",
        },
    },
    f"{PROJECT_ID}.reporting.mart_pressure_attribution_ooni_daily": {
        "key_columns": ["measurement_date", "test_name", "protocol"],
        "required_columns": {
            "measurement_date",
            "country",
            "test_name",
            "protocol",
            "total_experiment_results",
            "blocking_signal_count",
            "blocked_results",
            "ok_results",
            "high_confidence_events",
            "blocking_signal_rate",
            "attribution_methodology_version",
            "reporting_version",
            "snapshot_at",
        },
    },
}


def _key_expression(key_columns: list[str]) -> str:
    parts = [
        f"COALESCE(CAST({column} AS STRING), '<null>')"
        for column in key_columns
    ]
    return "CONCAT(" + ", '|', ".join(parts) + ")"


def _fetch_metrics(
    client: bigquery.Client,
    table_id: str,
    key_columns: list[str],
    null_checked_columns: list[str],
) -> dict:
    key_expr = _key_expression(key_columns)
    null_conditions = " OR ".join(
        f"{column} IS NULL" for column in null_checked_columns
    ) or "FALSE"

    query = f"""
    SELECT
        COUNT(*) AS row_count,
        COUNT(DISTINCT {key_expr}) AS distinct_keys,
        COUNTIF({null_conditions}) AS null_key_rows
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
    distinct_keys = int(metrics["distinct_keys"])

    if row_count == 0:
        failures.append("empty_table")

    if row_count != distinct_keys:
        failures.append("grain_key_not_unique")

    if int(metrics["null_key_rows"]) > 0:
        failures.append("null_grain_key_rows")

    return failures


def validate_table(
    client: bigquery.Client,
    table_id: str,
    contract: dict[str, object],
) -> dict[str, object]:
    table = client.get_table(table_id)

    required_columns = set(contract["required_columns"])
    key_columns = list(contract["key_columns"])

    schema_failures = _schema_failures(
        table,
        required_columns,
    )

    # disorder_type is nullable in ACLED's own export; the key
    # expression already maps NULL to a sentinel so uniqueness still
    # holds, and the null check simply skips that one column.
    null_checked_columns = [
        column for column in key_columns if column != "disorder_type"
    ]

    metrics = _fetch_metrics(
        client,
        table_id,
        key_columns,
        null_checked_columns,
    )

    metric_failures = _metric_failures(metrics)

    failures = schema_failures + metric_failures

    return {
        "table_id": table_id,
        "status": "failed" if failures else "passed",
        "hard_failures": ",".join(failures),
        "row_count": int(metrics["row_count"]),
        "distinct_keys": int(metrics["distinct_keys"]),
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

    frame = pd.DataFrame(rows)

    failed = frame[frame["status"] == "failed"]
    if not failed.empty:
        details = "; ".join(
            f"{row.table_id}: {row.hard_failures}"
            for row in failed.itertuples()
        )
        raise RuntimeError(
            f"pressure-attribution contract validation failed -- {details}"
        )

    return frame
