/* @bruin
name: dims.country
type: sql
connection: duckdb-mart
description: Dimension table for standardized country names
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: overwrite
depends:
    - stg.acled
    - stg.ooni
    - stg.google_transparency
    - stg.lumen
columns:
    - name: country
      type: STRING
      description: Standardized country name
      primary_key: true
      checks: [not_null, unique]
@bruin */

WITH countries AS (
    SELECT DISTINCT TRIM(LOWER(country)) AS country FROM stg.acled WHERE country IS NOT NULL
    UNION
    SELECT DISTINCT TRIM(LOWER(country)) FROM stg.ooni WHERE country IS NOT NULL
    UNION
    SELECT DISTINCT TRIM(LOWER(country)) FROM stg.google_transparency WHERE country IS NOT NULL
    UNION
    SELECT DISTINCT TRIM(LOWER(country)) FROM stg.lumen WHERE country IS NOT NULL
)
SELECT INITCAP(country) AS country
FROM countries;
