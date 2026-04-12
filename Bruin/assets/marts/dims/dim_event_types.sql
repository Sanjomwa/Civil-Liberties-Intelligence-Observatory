/* @bruin
name: dim_event_types
type: bq.sql
connection: bigquery-default
description: |
  ACLED event and sub-event type taxonomy for Kenya conflict events.
  Includes a civil-liberties relevance flag to highlight events most
  likely to correlate with internet censorship spikes.
owner: civil-liberties-pipeline

depends:
  - stg.acled_conflict_events

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT DISTINCT
    event_type,
    sub_event_type,

    -- Group for dashboard top-level filtering
    CASE
        WHEN event_type IN ('Protests', 'Riots')            THEN 'Civil Unrest'
        WHEN event_type IN ('Violence against civilians')   THEN 'State Violence'
        WHEN event_type = 'Battles'                         THEN 'Armed Conflict'
        WHEN event_type = 'Explosions/Remote violence'      THEN 'Armed Conflict'
        ELSE 'Other'
    END                                                     AS event_group,

    -- Flag events that are most likely to trigger censorship responses
    CASE
        WHEN event_type IN ('Protests', 'Riots')            THEN TRUE
        WHEN sub_event_type LIKE '%demonstration%'          THEN TRUE
        WHEN sub_event_type LIKE '%march%'                  THEN TRUE
        ELSE FALSE
    END                                                     AS censorship_trigger_likely

FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.acled_conflict_events`
WHERE country = 'Kenya'
  AND event_type IS NOT NULL
ORDER BY event_type, sub_event_type
