/* @bruin
name: dim_measurement_quality
type: bq.sql
connection: bigquery-default
description: Measurement reliability classification across OONI-style datasets.

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT *
FROM UNNEST([

    STRUCT('SUCCESS' AS quality_level, 'Measurement completed successfully' AS description),
    STRUCT('TIMEOUT' AS quality_level, 'Connection timeout (ambiguous signal)' AS description),
    STRUCT('FAILURE' AS quality_level, 'Technical failure during measurement' AS description),
    STRUCT('INCONCLUSIVE' AS quality_level, 'Cannot determine censorship state' AS description)

]);
