/* @bruin
name: fact.lumen_platforms
type: sql
connection: duckdb-mart
description: Fact table for Lumen takedown requests (platform-level + legal requests)
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: overwrite
depends:
    - stg.lumen
    - dims.country
columns:
    - name: request_id
      type: STRING
      description: Unique request identifier
      primary_key: true
      checks: [not_null, unique]
    - name: country
      type: STRING
      description: Standardized country name
      checks: [not_null]
    - name: sender
      type: STRING
      description: Entity sending request
    - name: recipient
      type: STRING
      description: Platform or service targeted
      checks: [not_null]
    - name: date_submitted
      type: TIMESTAMP
      description: When request was submitted
      checks: [not_null]
    - name: reason
      type: STRING
      description: Reason for takedown
    - name: request_type
      type: STRING
      description: Request classification (platform-level vs legal)
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp
custom_checks:
    - name: valid_date_range
      description: Ensure requests fall within 2024–2026
      query: "SELECT COUNT(*) FROM fact.lumen_platforms WHERE strftime(date_submitted, '%Y') NOT BETWEEN '2024' AND '2026'"
      value: 0
@bruin */

SELECT
    l.request_id,
    c.country,
    l.sender,
    l.recipient,
    l.date_submitted,
    l.reason,
    CASE 
        WHEN LOWER(l.reason) LIKE '%court%' OR LOWER(l.reason) LIKE '%legal%' THEN 'legal'
        ELSE 'platform'
    END AS request_type,
    l.extracted_at
FROM stg.lumen l
JOIN dims.country c
  ON LOWER(TRIM(l.country)) = LOWER(TRIM(c.country));
