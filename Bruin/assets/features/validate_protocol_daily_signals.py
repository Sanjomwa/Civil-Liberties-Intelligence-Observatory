"""@bruin
name: features.validate_protocol_daily_signals
type: python
image: python:3.12
connection: bigquery-default

tags:
  - validation
  - features_bq
  - dataset_ooni

description: |
  Validates the features.protocol_daily_signals contract in BigQuery.
  Avoids pandas to_dataframe() on query results (no db-dtypes in Codespaces).

depends:
  - features.protocol_daily_signals

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
    "baseline_signal_stddev_effective",
    "signal_zscore_30d",
    "anomaly_score",
    "sample_quality_score",
    "low_sample_flag",
    "sparse_window_flag",
    "zero_variance_flag",
    "guardrail_config_json",
    "feature_version",
    "computed_at",
}


def _first_query_row_as_dict(client: bigquery.Client, query: str) -> dict[str, object]:
    rows = list(client.query(query).result())
    if not rows:
        raise RuntimeError("validation query returned no rows")
    row = rows[0]
    return {k: row[k] for k in row.keys()}


def materialize() -> pd.DataFrame:
    client = bigquery.Client(project=PROJECT_ID)
    table = client.get_table(TABLE_ID)
    columns = {field.name for field in table.schema}
    missing_columns = sorted(REQUIRED_COLUMNS - columns)

    query = f"""
    SELECT
      COUNT(*) AS row_count,
      COUNT(DISTINCT feature_id) AS distinct_feature_ids,
      COUNTIF(feature_id IS NULL) AS null_feature_ids,
      COUNTIF(measurement_date IS NULL) AS null_dates,
      COUNTIF(country IS NULL) AS null_countries,
      COUNTIF(protocol IS NULL) AS null_protocols,
      COUNTIF(signal_rate < 0 OR signal_rate > 1) AS invalid_signal_rates,
      COUNTIF(sample_quality_score < 0 OR sample_quality_score > 1) AS invalid_quality_scores,
      COUNTIF(low_sample_flag) AS low_sample_rows,
      COUNTIF(sparse_window_flag) AS sparse_window_rows,
      COUNTIF(zero_variance_flag) AS zero_variance_rows,
      COUNTIF(baseline_signal_stddev_effective IS NULL) AS null_effective_stddev,
      COUNTIF(baseline_signal_stddev_effective <= 0) AS nonpositive_effective_stddev,
      COUNTIF(signal_zscore_30d IS NULL) AS null_zscore_rows,
      COUNTIF(anomaly_score IS NULL) AS null_anomaly_rows
    FROM `{TABLE_ID}`
    """
    metrics = _first_query_row_as_dict(client, query)
    row_count = int(metrics["row_count"])
    distinct_feature_ids = int(metrics["distinct_feature_ids"])

    hard_failures = []
    if missing_columns:
        hard_failures.append(f"missing_columns={','.join(missing_columns)}")
    if row_count != distinct_feature_ids:
        hard_failures.append("feature_id_not_unique")
    if int(metrics["null_feature_ids"]) > 0:
        hard_failures.append("null_feature_ids")
    if int(metrics["null_dates"]) > 0:
        hard_failures.append("null_dates")
    if int(metrics["null_countries"]) > 0:
        hard_failures.append("null_countries")
    if int(metrics["null_protocols"]) > 0:
        hard_failures.append("null_protocols")
    if int(metrics["invalid_signal_rates"]) > 0:
        hard_failures.append("invalid_signal_rates")
    if int(metrics["invalid_quality_scores"]) > 0:
        hard_failures.append("invalid_quality_scores")
    if int(metrics["null_effective_stddev"]) > 0:
        hard_failures.append("null_baseline_signal_stddev_effective")
    if int(metrics["nonpositive_effective_stddev"]) > 0:
        hard_failures.append("nonpositive_baseline_signal_stddev_effective")

    return pd.DataFrame(
        [
            {
                "table_id": TABLE_ID,
                "status": "failed" if hard_failures else "passed",
                "hard_failures": ",".join(hard_failures),
                "row_count": row_count,
                "distinct_feature_ids": distinct_feature_ids,
                "low_sample_rows": int(metrics["low_sample_rows"]),
                "sparse_window_rows": int(metrics["sparse_window_rows"]),
                "zero_variance_rows": int(metrics["zero_variance_rows"]),
                "null_zscore_rows": int(metrics["null_zscore_rows"]),
                "null_anomaly_rows": int(metrics["null_anomaly_rows"]),
                "validated_at": datetime.now(timezone.utc),
            }
        ]
    )
