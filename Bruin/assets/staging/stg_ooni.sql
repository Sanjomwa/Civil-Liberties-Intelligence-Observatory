/* @bruin
name: stg.ooni
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-ooni

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
    - name: period
      type: STRING
      description: Reporting period (YYYY-MM)
      checks:
          - name: not_null
    - name: half_year_label
      type: STRING
      description: Human-readable half-year (e.g. Jan-Jun 2023)
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
    - name: valid_date_range
      description: Ensure measurements fall within Jun 2023–Jun 2025
      query: "SELECT COUNT(*) FROM stg.ooni WHERE start_time < DATE '2023-06-01' OR start_time > DATE '2025-06-30'"
      value: 0
@bruin */

WITH raw AS (
    SELECT
        measurement_id,
        probe_cc AS country,
        test_name,
        input,
        CAST(start_time AS TIMESTAMP) AS start_time,
        -- normalize to YYYY-MM
        strftime(CAST(start_time AS DATE), '%Y-%m') AS period,
        -- derive half-year label
        CASE
            WHEN strftime(CAST(start_time AS DATE), '%m') IN ('01','02','03','04','05','06')
                 THEN 'Jan-Jun ' || strftime(CAST(start_time AS DATE), '%Y')
            WHEN strftime(CAST(start_time AS DATE), '%m') IN ('07','08','09','10','11','12')
                 THEN 'Jul-Dec ' || strftime(CAST(start_time AS DATE), '%Y')
        END AS half_year_label,
        status,
        probe_asn,
        extracted_at
    FROM raw.ooni_raw
    WHERE CAST(start_time AS DATE) BETWEEN DATE '2023-06-01' AND DATE '2025-06-30'
      AND probe_cc IS NOT NULL
)

SELECT * FROM raw;
