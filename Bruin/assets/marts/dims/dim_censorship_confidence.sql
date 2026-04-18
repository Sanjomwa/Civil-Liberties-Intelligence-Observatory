/* @bruin
tags:
  - marts_bq
name: dim_censorship_confidence
type: bq.sql
connection: bigquery-default
description: Confidence levels for censorship detection across datasets.

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT *
FROM UNNEST([

    STRUCT('LOW' AS confidence_level, 1 AS weight, 'Weak signal / possible measurement failure' AS description),
    STRUCT('MEDIUM' AS confidence_level, 2 AS weight, 'Probable censorship signal' AS description),
    STRUCT('HIGH' AS confidence_level, 3 AS weight, 'Strong confirmed censorship signal' AS description),
    STRUCT('NONE' AS confidence_level, 0 AS weight, 'No evidence of censorship' AS description)

]);
