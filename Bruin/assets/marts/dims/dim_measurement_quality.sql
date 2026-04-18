/* @bruin
name: dim_measurement_quality
type: bq.sql
connection: bigquery-default
description: Quality scoring model for OONI measurements used in weighting censorship confidence.
materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT * FROM UNNEST([
    STRUCT('HIGH' AS quality_level, 0.3 AS weight, 'Complete measurement with full metadata'),
    STRUCT('MEDIUM' AS quality_level, 0.2 AS weight, 'Partial metadata or minor gaps'),
    STRUCT('LOW' AS quality_level, 0.1 AS weight, 'Incomplete or noisy measurement'),
    STRUCT('FAILED' AS quality_level, 0.0 AS weight, 'Measurement failure / unusable data')
])
