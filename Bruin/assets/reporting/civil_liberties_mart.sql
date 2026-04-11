/* @bruin
name: civil_liberties_mart
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Final reporting mart for Kenya Civil Liberties & Censorship Observatory
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT 
    d.full_date,
    d.year,
    d.half_year,
    d.protest_season_flag,
    
    -- Censorship metrics
    c.test_category,
    c.test_name,
    COUNT(DISTINCT c.measurement_id) AS censorship_events,
    COUNT(DISTINCT CASE WHEN c.censorship_status IN ('anomaly','confirmed') THEN c.measurement_id END) AS confirmed_blocks,
    
    -- Conflict metrics
    SUM(e.events) AS total_conflict_events,
    SUM(e.fatalities) AS total_fatalities,
    COUNT(DISTINCT e.event_id) AS distinct_conflict_events,
    
    -- Takedown metrics
    SUM(t.number_of_requests) AS total_takedown_requests,
    COUNT(DISTINCT t.reason) AS distinct_takedown_reasons,
    
    -- Combined insight
    COUNT(DISTINCT CASE WHEN c.measurement_date = e.measurement_date THEN c.measurement_id END) AS days_with_both_censorship_and_conflict,
    
    e.region,
    e.admin1,
    e.disorder_type,
    t.reason AS takedown_reason

FROM {{ ref('fact_censorship_impact') }} c
LEFT JOIN {{ ref('dim_dates') }} d 
    ON c.measurement_date = d.full_date
LEFT JOIN {{ ref('fact_conflict_events') }} e 
    ON c.measurement_date = e.measurement_date
LEFT JOIN {{ ref('fact_takedown_requests') }} t 
    ON c.measurement_date = t.measurement_date
WHERE d.full_date BETWEEN DATE '2023-06-01' AND DATE '2025-06-30'
GROUP BY ALL
ORDER BY d.full_date DESC;
