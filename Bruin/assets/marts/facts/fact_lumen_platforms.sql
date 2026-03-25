/* @bruin
name: fact.lumen_platforms
type: sql
connection: duckdb-lumen
description: Fact table for Lumen takedown requests, joined with platform dimension
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: overwrite
depends:
    - stg.lumen
    - dims.platform
columns:
    - name: request_id
      type: STRING
      description: Unique request identifier
      primary_key: true
      checks:
        - name: not_null
        - name: unique
    - name: platform_id
      type: STRING
      description: Normalized platform identifier
      checks:
        - name: not_null
    - name: country
      type: STRING
      description: Country issuing request
    - name: sender
      type: STRING
      description: Entity sending request
    - name: date_submitted
      type: TIMESTAMP
      description: When request was submitted
    - name: reason
      type: STRING
      description: Reason for takedown
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp
@bruin */

WITH joined AS (
    SELECT
        s.request_id,
        d.platform_id,
        s.country,
        s.sender,
        s.date_submitted,
        s.reason,
        s.extracted_at
    FROM stg.lumen s
    LEFT JOIN dims.platform d
      ON s.recipient = d.platform_name
)

SELECT * FROM joined;
