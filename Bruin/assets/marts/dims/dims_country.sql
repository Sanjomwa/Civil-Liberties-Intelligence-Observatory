/* @bruin
name: dims.country
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-mart

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Dimension table for standardized country names
owner: civil-liberties-pipeline

materialization:
    type: table
    strategy: create+replace

depends:
    - stg.acled
    - stg.ooni
    - stg.google_transparency
    - stg.lumen

columns:
    - name: country_id
      type: STRING
      description: Surrogate key for country
      primary_key: true
      checks:
        - name: not_null
        - name: unique
    - name: country_code
      type: STRING
      description: ISO-style country code
      checks:
        - name: not_null
    - name: country_name
      type: STRING
      description: Standardized country name
      checks:
        - name: not_null
@bruin */

WITH acled_countries AS (
    SELECT DISTINCT UPPER(TRIM(country)) AS country_code
    FROM stg.acled
    WHERE country IS NOT NULL
),
ooni_countries AS (
    SELECT DISTINCT UPPER(TRIM(country)) AS country_code
    FROM stg.ooni
    WHERE country IS NOT NULL
),
google_countries AS (
    SELECT DISTINCT UPPER(TRIM(country)) AS country_code
    FROM stg.google_transparency
    WHERE country IS NOT NULL
),
lumen_countries AS (
    SELECT DISTINCT UPPER(TRIM(country)) AS country_code
    FROM stg.lumen
    WHERE country IS NOT NULL
),
unioned AS (
    SELECT country_code FROM acled_countries
    UNION
    SELECT country_code FROM ooni_countries
    UNION
    SELECT country_code FROM google_countries
    UNION
    SELECT country_code FROM lumen_countries
),
normalized AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY country_code) AS country_id,
        country_code,
        INITCAP(country_code) AS country_name
    FROM unioned
)

SELECT * FROM normalized;
