/* @bruin
name: stg.ooni
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-ooni

# For staging & prod environments, override the type
environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Cleaned and filtered OONI censorship measurements
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: create+replace
depends:
    - raw.ooni_raw
columns:
    - name: measurement_id
      type: STRING
      description: Unique OONI measurement identifier
      primary_key: true
      checks:
          - name: not_null
          - name: unique
    - name: country
      type: STRING
      description: Country code of probe
      checks:
          - name: not_null
    - name: test_name
      type: STRING
      description: OONI test type
    - name: input
      type: STRING
      description: Input domain or URL tested
    - name: start_time
      type: TIMESTAMP
      description: When the test started
      checks:
          - name: not_null
    - name: status
      type: STRING
      description: Result status (ok, anomaly, blocked)
    - name: probe_asn
      type: INTEGER
      description: Autonomous system number of probe
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp
custom_checks:
    - name: valid_status_values
      description: Ensure status is one of ok/anomaly/blocked
      query: "SELECT COUNT(*) FROM {{ this }} WHERE status NOT IN ('ok','anomaly','blocked')"
      value: 0
@bruin */

WITH raw AS (
    SELECT * FROM raw.ooni_raw
)
SELECT
    measurement_id,
    probe_cc AS country,
    test_name,
    input,
    start_time,
    status,
    probe_asn,
    extracted_at
FROM raw
WHERE CAST(strftime(start_time, '%Y') AS INTEGER) BETWEEN 2024 AND 2026
  AND country IS NOT NULL;