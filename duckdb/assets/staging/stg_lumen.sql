/* @bruin
name: stg.lumen
type: sql
connection: duckdb-lumen
description: Cleaned Lumen takedown requests
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: overwrite
depends:
    - raw.lumen_requests
columns:
    - name: request_id
      type: STRING
      description: Unique request identifier
      primary_key: true
      checks:
          - name: not_null
          - name: unique
    - name: country
      type: STRING
      description: Country issuing request
      checks:
          - name: not_null
    - name: sender
      type: STRING
      description: Entity sending request
    - name: recipient
      type: STRING
      description: Platform or service targeted
      checks:
          - name: not_null
    - name: date_submitted
      type: TIMESTAMP
      description: When request was submitted
      checks:
          - name: not_null
    - name: reason
      type: STRING
      description: Reason for takedown
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp
custom_checks:
    - name: valid_date_range
      description: Ensure requests fall within 2024–2026
      query: "SELECT COUNT(*) FROM stg.lumen WHERE strftime(date_submitted, '%Y') NOT BETWEEN '2024' AND '2026'"
      value: 0
@bruin */

WITH raw AS (
    SELECT * FROM raw.lumen_requests
)
SELECT
    request_id,
    country,
    sender,
    recipient,
    date_submitted,
    reason,
    extracted_at
FROM raw
WHERE CAST(strftime(date_submitted, '%Y') AS INTEGER) BETWEEN 2024 AND 2026
  AND country IS NOT NULL;
