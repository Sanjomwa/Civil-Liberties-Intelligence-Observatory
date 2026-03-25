/* @bruin
name: view.narrative_summary
type: duckdb.sql
connection: duckdb-mart

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Narrative-style summary view combining takedowns, censorship, and conflict events
owner: civil-liberties-pipeline

materialization:
    type: view

depends:
    - mart.civil_liberties

columns:
    - name: country
      type: STRING
      description: Standardized country name
    - name: period
      type: STRING
      description: Reporting period (YYYY-MM)
    - name: half_year_label
      type: STRING
      description: Human-readable half-year label
    - name: summary_text
      type: STRING
      description: Narrative summary of civil liberties signals
@bruin */

SELECT
    country,
    period,
    half_year_label,
    CONCAT(
        'In ', country, ' during ', half_year_label, ': ',
        'There were ', COALESCE(conflict_events, 0), ' conflict events resulting in ',
        COALESCE(fatalities, 0), ' fatalities. ',
        'OONI recorded ', COALESCE(censorship_tests, 0), ' censorship tests. ',
        'Google Transparency reported ', COALESCE(takedown_requests, 0), ' takedown requests, ',
        'while Lumen recorded ', COALESCE(lumen_requests, 0), ' requests. ',
        'Overall, this period reflects ', 
        CASE 
            WHEN COALESCE(conflict_events,0) > 50 OR COALESCE(censorship_tests,0) > 100 THEN 'heightened civil liberties pressures.'
            WHEN COALESCE(takedown_requests,0) + COALESCE(lumen_requests,0) > 50 THEN 'significant takedown activity.'
            ELSE 'moderate activity across all signals.'
        END
    ) AS summary_text
FROM mart.civil_liberties;
