/* @bruin
name: fact.censorship_tests
type: sql
connection: duckdb-mart
description: Fact table for OONI censorship measurements
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: overwrite
depends:
    - stg.ooni
    - dims.country
columns:
    - name: measurement_id
      type: STRING
      description: Unique OONI measurement identifier
      primary_key: true
      checks: [not_null, unique]
    - name: country
      type: STRING
      description: Standardized country name
      checks: [not_null]
    - name: test_name
      type: STRING
      description: OONI test type
    - name: input
      type: STRING
      description: Input domain or URL tested
    - name: start_time
      type: TIMESTAMP
      description: When the test started
      checks: [not_null]
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
      query: "SELECT COUNT(*) FROM fact.censorship_tests WHERE status NOT IN ('ok','anomaly','blocked')"
      value: 0
@bruin */

SELECT
    o.measurement_id,
    c.country,
    o.test_name,
    o.input,
    o.start_time,
    o.status,
    o.probe_asn,
    o.extracted_at
FROM stg.ooni o
JOIN dims.country c
  ON LOWER(TRIM(o.country)) = LOWER(TRIM(c.country));
