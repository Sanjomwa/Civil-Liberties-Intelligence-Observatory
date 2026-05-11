"""@bruin
name: features.validate_protocol_daily_signals
type: python
image: python:3.12
connection: duckdb-parquet

tags:
  - validation
  - features_bq
  - dataset_ooni

description: |
  Validates the features.protocol_daily_signals contract in BigQuery.

  Read-only validation asset for pipeline observability.

  Performs:
    - schema contract validation
    - uniqueness checks
    - nullability checks
    - metric range checks
    - statistical guardrail monitoring

depends:
  - features.protocol_daily_signals

materialization:
  type: table
  strategy: create+replace
@bruin"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from google.cloud import bigquery


PROJECT_ID = "encoded-joy-485413-k5"
TABLE_ID = f"{PROJECT_ID}.features.protocol_daily_signals"


REQUIRED_COLUMNS = {
    "feature_id",
    "measurement_date",
    "country",
    "protocol",
    "test_family",
    "asn",
    "feature_grain",
    "measurement_count",
    "observation_count",
    "signal_rate",
    "anomaly_score",
    "sample_quality_score",
    "low_sample_flag",
    "sparse_window_flag",
    "zero_variance_flag",
    "guardrail_config_json",
    "feature_version",
    "computed_at",
}


def _fetch_metrics(client: bigquery.Client) -> dict:
    query = f"""
    SELECT
        COUNT(*) AS row_count,
        COUNT(DISTINCT feature_id) AS distinct_feature_ids,

        COUNTIF(feature_id IS NULL) AS null_feature_ids,
        COUNTIF(measurement_date IS NULL) AS null_dates,
        COUNTIF(country IS NULL) AS null_countries,
        COUNTIF(protocol IS NULL) AS null_protocols,

        COUNTIF(signal_rate < 0 OR signal_rate > 1)
            AS invalid_signal_rates,

        COUNTIF(sample_quality_score < 0 OR sample_quality_score > 1)
            AS invalid_quality_scores,

        COUNTIF(low_sample_flag)
            AS low_sample_rows,

        COUNTIF(sparse_window_flag)
            AS sparse_window_rows,

        COUNTIF(zero_variance_flag)
            AS zero_variance_rows

    FROM `{TABLE_ID}`
    """

    rows = client.query(query).result()
    row = next(rows)

    return dict(row.items())


def _schema_failures(table: bigquery.Table) -> list[str]:
    actual = {field.name for field in table.schema}
    missing = sorted(REQUIRED_COLUMNS - actual)

    if not missing:
        return []

    return [f"missing_columns={','.join(missing)}"]


def _metric_failures(metrics: dict) -> list[str]:
    failures = []

    row_count = int(metrics["row_count"])
    distinct_feature_ids = int(metrics["distinct_feature_ids"])

    if row_count != distinct_feature_ids:
        failures.append("feature_id_not_unique")

    if int(metrics["null_feature_ids"]) > 0:
        failures.append("null_feature_ids")

    if int(metrics["null_dates"]) > 0:
        failures.append("null_dates")

    if int(metrics["null_countries"]) > 0:
        failures.append("null_countries")

    if int(metrics["null_protocols"]) > 0:
        failures.append("null_protocols")

    if int(metrics["invalid_signal_rates"]) > 0:
        failures.append("invalid_signal_rates")

    if int(metrics["invalid_quality_scores"]) > 0:
        failures.append("invalid_quality_scores")

    return failures


def materialize() -> pd.DataFrame:
    client = bigquery.Client(project=PROJECT_ID)

    table = client.get_table(TABLE_ID)

    schema_failures = _schema_failures(table)

    metrics = _fetch_metrics(client)

    metric_failures = _metric_failures(metrics)

    hard_failures = schema_failures + metric_failures

    return pd.DataFrame(
        [
            {
                "table_id": TABLE_ID,
                "status": "failed" if hard_failures else "passed",
                "hard_failures": ",".join(hard_failures),

                "row_count": int(metrics["row_count"]),
                "distinct_feature_ids": int(
                    metrics["distinct_feature_ids"]
                ),

                "low_sample_rows": int(
                    metrics["low_sample_rows"]
                ),

                "sparse_window_rows": int(
                    metrics["sparse_window_rows"]
                ),

                "zero_variance_rows": int(
                    metrics["zero_variance_rows"]
                ),

                "validated_at": datetime.now(
                    timezone.utc
                ),
            }
        ]
    )
