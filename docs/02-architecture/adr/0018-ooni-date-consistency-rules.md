# ADR-0018: Apply OONI's date-consistency rules, using the archive hour as receive time and fetching exact `measurement_uid` only where the hour cannot decide

**Status:** Proposed, 2026-11-23. Accepted when the fix session's before-and-after figures are reviewed.
**Related:** ADR-0017 (OONI's zero-accuracy rules), TD-161.

## Context

ADR-0017 adopted OONI's current zero-accuracy rules (`ooni/backend` `fastpath/fastpath/core.py`, commit `27f2b28`) but could not apply two of them. `flag_measurements_with_wrong_date` sets accuracy to 0 when OONI's receive time, read from `measurement_uid`, is more than an hour *before* the measurement's start time ("from the future"), or more than a year *after* it ("too old"). OONI applies this to every measurement, whatever the test.

A read-only check on 2026-11-23 found:
1. **CLIO's ingestion is not at fault.** It keeps the whole record, and it would use `measurement_uid` as its own `measurement_id` if records carried one.
2. **OONI's `raw/` archive does not include `measurement_uid`.** Nor does it include `scores`, `anomaly` or `confirmed`: OONI's backend adds them after receipt. OONI's processed `jsonl/` prefix carries `measurement_uid`, but it ends in October 2020.
3. **The archive's hour folder, recorded in each row's `source_file`, contains OONI's receive time** for 360 of 360 measurements checked against `measurement_uid` from OONI's API.
4. **Over CLIO's corpus, the hour alone decides the rules for all but 2,813 measurements:**
   - 47 are definitely too old;
   - 480 are definitely from the future;
   - 2,813 fall in a one-hour band where the hour can't decide.

## Decision

1. **Receive time.** For every OONI measurement, the archive hour `[bucket_start, bucket_start + 3599 s]` is parsed from `source_file` and recorded as OONI's receive interval. The 360-of-360 validation is recorded with it.
2. **Exact receive time where needed.** For measurements in the undetermined band only, `measurement_uid` is fetched once from OONI's public API (one request per distinct `report_id`, rate-limited). It is stored in a reviewable lookup keyed by `report_id` and `input`, with the retrieval time.
3. **Rules.** OONI's two date rules, GEN-F (future) and GEN-O (too old), are added to `marts.dim_ooni_zero_accuracy_rules` as adopted, **for all six tests, DNSCheck included.** A wrong device clock makes a measurement's timing unreliable, whatever the test. That differs from ADR-0017's decision not to adopt DNSCheck's unsupported-test branch, which concerned the absence of a scorer, not data quality.
4. **Three outcomes per measurement:**
   - the rule is met, so the measurement is excluded exactly as under ADR-0017, at both levels;
   - the rule is not met;
   - undetermined (band row with no exact time), which is kept and counted, not excluded.
5. **Rebuild** only through `Bruin/scripts/safe_run/safe_materialize.py`, with before-and-after figures.

## Consequences

- About 527 measurements are excluded on the hour alone, plus however many band rows the exact time confirms. Most are DNSCheck.
- Published figures may move slightly. Any change to a figure stated in public text (for example "271 remain classified BLOCKED") is reported, and that text is corrected in a separate, approved pass.
- `stg.ooni_measurements` is not changed. Receive time is derived downstream.
- The `measurement_uid` lookup is a one-off snapshot. Measurements ingested later need the same band check.

## Alternatives considered

- **Fetch `measurement_uid` for every measurement.** Rejected for now: about 1.35 million rows, roughly 15 days at OONI's rate limit, for rules the hour already decides on 99.8% of rows.
- **Hour only, leaving the band undetermined.** Rejected: the band holds real cases (one WhatsApp measurement with its start time 66 minutes after receipt), and resolving it costs under an hour of API calls.
- **Switch ingestion to a source with backend fields.** Not available for 2023–25: OONI's processed prefix ends in 2020.
