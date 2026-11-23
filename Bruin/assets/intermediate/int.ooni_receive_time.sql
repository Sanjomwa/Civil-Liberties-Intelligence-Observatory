/* @bruin
name: int.ooni_receive_time
type: bq.sql
connection: bigquery-default

tags:
  - int_bq
  - dataset_ooni
  - ooni_verdict_phase_2

description: |
  ADR-0018 (2026-11-23). One row per OONI measurement in
  stg.ooni_measurements: OONI's receive time for it, and whether OONI's
  date-consistency rules (ooni/backend fastpath/fastpath/core.py,
  flag_measurements_with_wrong_date, lines 1634-1652 at commit 27f2b28)
  give it zero accuracy.

  OONI reads the receive time from measurement_uid
  (strptime(msmt_uid[:22], "%Y%m%d%H%M%S.%f_")), sets
  delta = receive_time - measurement_start_time in seconds, and gives
  accuracy 0 if delta < -3600 (GEN-F, "from the future") or, otherwise,
  delta > 31536000 (GEN-O, "too old"). OONI's raw/ archive, which CLIO
  ingests, carries no measurement_uid. Two sources are used instead:

  - ARCHIVE_HOUR: the archive hour folder, parsed from source_file
    (10 digits before "_<CC>_"). It contained OONI's receive time for 360
    of 360 measurements checked against measurement_uid from OONI's API
    (2026-11-23). The receive time lies in [bucket_start,
    bucket_start + 3600 s). With whole-second start times (true of every
    row, checked 2026-11-23), the rule is decided for every receive time in
    the hour when:
      GEN_O:   start < bucket_start - 31536000 s
      GEN_F:   start >= bucket_start + 7200 s
      NEITHER: bucket_start + 3600 s - 31536000 s <= start
               AND start <= bucket_start + 3600 s
    Anything else is the band where the hour cannot decide. These are the
    item-43 definitions with an exclusive end of hour; on 2026-11-23 the
    two give identical counts (no start time falls on the one second where
    they differ).
  - MEASUREMENT_UID: for band rows only, measurement_uid fetched once from
    OONI's API (int.ooni_measurement_uid_band_lookup, match_state =
    'MATCHED'), parsed as OONI does. OONI's exact rule is then applied.

  date_rule_state: GEN_F, GEN_O, NEITHER, or UNDETERMINED (a band row with
  no usable measurement_uid; kept and counted, not excluded).
  int.ooni_zero_accuracy_measurements reads GEN_F / GEN_O rows.

  Reads only small typed columns of stg.ooni_measurements (no
  raw_measurement); stg.ooni_measurements itself is not changed.

depends:
  - stg.ooni_measurements
  - int.ooni_measurement_uid_band_lookup

materialization:
  type: table
  strategy: create+replace

custom_checks:
  - name: measurement_uid_receive_time_within_archive_hour
    description: |
      ADR-0018 Decision 1 rests on the archive hour containing OONI's
      receive time. Every receive time read from measurement_uid must lie
      in its row's archive hour. Must stay 0.
    query: |
      SELECT COUNT(*)
      FROM `{{ var.project_id }}.int.ooni_receive_time`
      WHERE receive_time_source = 'MEASUREMENT_UID'
        AND (uid_receive_time < bucket_start
             OR uid_receive_time >= TIMESTAMP_ADD(bucket_start, INTERVAL 3600 SECOND))
    value: 0
  - name: every_row_has_an_archive_hour
    description: An unparsed source_file would make a row UNDETERMINED silently. Must stay 0.
    query: |
      SELECT COUNT(*)
      FROM `{{ var.project_id }}.int.ooni_receive_time`
      WHERE bucket_start IS NULL
    value: 0

columns:
  - name: measurement_id
    type: string
    checks:
      - name: not_null
      - name: unique
  - name: bucket_start
    type: timestamp
    description: Start of the OONI archive hour (from source_file), UTC.
  - name: uid_receive_time
    type: timestamp
    description: OONI's receive time from measurement_uid; NULL unless fetched and MATCHED.
  - name: receive_time_source
    type: string
    checks:
      - name: not_null
      - name: accepted_values
        value: [MEASUREMENT_UID, ARCHIVE_HOUR]
  - name: date_rule_state
    type: string
    checks:
      - name: not_null
      - name: accepted_values
        value: [GEN_F, GEN_O, NEITHER, UNDETERMINED]
@bruin */

WITH measurements AS (
  SELECT
    measurement_id,
    test_name,
    test_version,
    report_id,
    input,
    measurement_start_time,
    source_file,
    PARSE_TIMESTAMP(
      '%Y%m%d%H',
      REGEXP_EXTRACT(source_file, r'(\d{10})_[A-Z]{2}_')
    ) AS bucket_start
  FROM `{{ var.project_id }}.stg.ooni_measurements`
),

-- OONI: if not msmt_uid.startswith("20") or len(msmt_uid) < 20: return;
-- a uid[:22] that does not parse as "%Y%m%d%H%M%S.%f_" also returns.
-- NULLIF guards a seed loader that writes an empty CSV cell as ''.
uids AS (
  SELECT
    report_id,
    COALESCE(input, '') AS input_key,
    NULLIF(measurement_uid, '') AS measurement_uid,
    IF(
      STARTS_WITH(measurement_uid, '20') AND LENGTH(measurement_uid) >= 20,
      SAFE.PARSE_TIMESTAMP('%Y%m%d%H%M%E*S_', SUBSTR(measurement_uid, 1, 22)),
      NULL
    ) AS uid_receive_time
  FROM `{{ var.project_id }}.int.ooni_measurement_uid_band_lookup`
  WHERE match_state = 'MATCHED'
),

joined AS (
  SELECT
    m.*,
    u.measurement_uid,
    u.uid_receive_time,
    TIMESTAMP_DIFF(u.uid_receive_time, m.measurement_start_time, MICROSECOND) / 1e6
      AS uid_delta_seconds
  FROM measurements AS m
  LEFT JOIN uids AS u
    ON u.report_id = m.report_id
    AND u.input_key = COALESCE(m.input, '')
)

SELECT
  measurement_id,
  test_name,
  test_version,
  report_id,
  input,
  measurement_start_time,
  bucket_start,
  measurement_uid,
  uid_receive_time,
  uid_delta_seconds,
  IF(uid_receive_time IS NOT NULL, 'MEASUREMENT_UID', 'ARCHIVE_HOUR') AS receive_time_source,
  CASE
    -- OONI's exact rule (if / elif order kept).
    WHEN uid_receive_time IS NOT NULL THEN
      CASE
        WHEN uid_delta_seconds < -3600 THEN 'GEN_F'
        WHEN uid_delta_seconds > 31536000 THEN 'GEN_O'
        ELSE 'NEITHER'
      END
    WHEN bucket_start IS NULL THEN 'UNDETERMINED'
    WHEN measurement_start_time < TIMESTAMP_SUB(bucket_start, INTERVAL 31536000 SECOND) THEN 'GEN_O'
    WHEN measurement_start_time >= TIMESTAMP_ADD(bucket_start, INTERVAL 7200 SECOND) THEN 'GEN_F'
    WHEN measurement_start_time <= TIMESTAMP_ADD(bucket_start, INTERVAL 3600 SECOND)
      AND measurement_start_time >= TIMESTAMP_SUB(
        TIMESTAMP_ADD(bucket_start, INTERVAL 3600 SECOND), INTERVAL 31536000 SECOND)
      THEN 'NEITHER'
    ELSE 'UNDETERMINED'
  END AS date_rule_state,
  CURRENT_TIMESTAMP() AS int_extracted_at
FROM joined
