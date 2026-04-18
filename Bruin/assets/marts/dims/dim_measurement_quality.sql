/* @bruin
tags:
  - marts_bq
name: marts.dim_measurement_quality
type: bq.sql
connection: bigquery-default

description: |
  Data reliability scoring model for OONI measurements.
  Used to weight censorship confidence and downstream repression indices.

  This layer ensures noisy or incomplete measurements do not
  artificially inflate censorship signals.

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT * FROM UNNEST([

    STRUCT(
        'HIGH' AS quality_level,
        1.00 AS weight,
        'Complete measurement with full metadata and valid test outputs' AS description
    ),

    STRUCT(
        'MEDIUM' AS quality_level,
        0.75 AS weight,
        'Mostly complete measurement with minor metadata gaps or partial signals' AS description
    ),

    STRUCT(
        'LOW' AS quality_level,
        0.40 AS weight,
        'Incomplete or noisy measurement with missing fields or uncertain signals' AS description
    ),

    STRUCT(
        'FAILED' AS quality_level,
        0.00 AS weight,
        'Unusable measurement due to failure or missing critical data' AS description
    )

]);