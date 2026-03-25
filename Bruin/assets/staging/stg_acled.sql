/* @bruin
name: stg.acled
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-acled

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Cleaned ACLED conflict events
owner: civil-liberties-pipeline

materialization:
    type: table
    strategy: create+replace

depends:
    - raw.acled_aggregated

columns:
    - name: country
      type: STRING
      description: Country of event
      checks:
        - name: not_null
    - name: admin1
      type: STRING
      description: First-level administrative division
    - name: event_type
      type: STRING
      description: Type of conflict event
      checks:
        - name: not_null
    - name: fatalities
      type: INTEGER
      description: Number of fatalities
      checks:
        - name: non_negative
    - name: event_count
      type: INTEGER
      description: Number of events aggregated
      checks:
        - name: non_negative
    - name: year
      type: INTEGER
      description: Event year
      checks:
        - name: not_null
    - name: month
      type: INTEGER
      description: Event month
    - name: period
      type: STRING
      description: Reporting period (YYYY-MM)
      checks:
        - name: not_null
    - name: half_year_label
      type: STRING
      description: Human-readable half-year (e.g. Jan-Jun 2023)
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp

custom_checks:
    - name: valid_date_range
      description: Ensure events fall within Jun 2023–Jun 2025
      query: "SELECT COUNT(*) FROM stg.acled WHERE DATE(year || '-' || month || '-01') < DATE '2023-06-01' OR DATE(year || '-' || month || '-01') > DATE '2025-06-30'"
      value: 0
@bruin */

WITH raw AS (
    SELECT
        country,
        admin1,
        event_type,
        fatalities,
        event_count,
        year,
        month,
        -- normalize to YYYY-MM
        year || '-' || LPAD(month, 2, '0') AS period,
        -- derive half-year label
        CASE
            WHEN month BETWEEN 1 AND 6 THEN 'Jan-Jun ' || year
            WHEN month BETWEEN 7 AND 12 THEN 'Jul-Dec ' || year
        END AS half_year_label,
        extracted_at
    FROM raw.acled_aggregated
    WHERE DATE(year || '-' || month || '-01') BETWEEN DATE '2023-06-01' AND DATE '2025-06-30'
)

SELECT * FROM raw;
