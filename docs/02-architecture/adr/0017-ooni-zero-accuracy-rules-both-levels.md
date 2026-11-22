# ADR-0017: Apply OONI's current zero-accuracy rules at both measurement and observation level

**Status:** Proposed, 2026-11-22. Accepted when the fix session's before-and-after figures are reviewed.
**Related:** ADR-0013 (agreement check against OONI's records), TD-160 (Signal 0.2.4 episode), `marts.dim_ooni_probe_version_accuracy`.

## Context

CLIO classifies OONI data at two levels: one verdict per measurement (`int.ooni_measurement_verdicts`), and one result per observation (`int.ooni_experiment_results`, one row per DNS, TCP, TLS or HTTP step). Read-only checks on 2026-11-22 found three problems.

1. **The two levels disagree.**
   - The measurement level already sets aside measurements that OONI's scoring treats as unreliable (`probe_accuracy_gate = DISCARDED_BAD_PROBE_VERSION`, 14,156 Signal measurements).
   - The observation level has no such gate. About 470,000 observation rows from those measurements are still counted, including 87 of the 361 TLS observations classified BLOCKED.
   - All four assets that count BLOCKED observations count them (`features.ooni_weekly_signals`, `features.protocol_daily_signals`, `reporting.mart_pressure_attribution_ooni_daily`, `marts.fact_protocol_blocking_summary`), and the dashboard reads those assets.
   - An August 2026 check had explained these rows against OONI's records, but they were never excluded from the counts.
2. **CLIO's copy of OONI's rules is out of date.**
   - `dim_ooni_probe_version_accuracy` was built from the archived `ooni/pipeline` repository (last changed March 2023).
   - OONI's live scoring code (`ooni/backend`, `fastpath/fastpath/core.py`, read at commit `27f2b28`) has further Signal rules: test version 0.2.4 is always scored at zero accuracy (ooni/probe#2636); versions up to 0.2.3 from 2023-11-07 (ooni/probe#2627); engine versions below 3.17.2 from 2023-05-02 (ooni/backend#679).
   - CLIO scores all 1,146 Signal 0.2.4 measurements as ANOMALOUS. This is the episode recorded in TD-160, which OONI's code now classifies as a known test breakage.
3. **OONI's stored scores and OONI's current code can disagree.**
   - For three Signal 0.2.4 measurements, OONI's API returns no accuracy score, although the current code would give zero. Newer rules appear not to have been applied back to older data.
   - OONI's code also has **no scorer for DNSCheck**. Its "unsupported test" branch gives every DNSCheck measurement zero accuracy. That reflects the absence of a scorer, not a judgement about data quality.

## Decision

1. **The reference is OONI's current scoring code, pinned to a commit.** Its rules become CLIO rules. OONI's stored per-measurement scores are used as a check, and every disagreement is listed in the documentation, never merged silently.
2. **One rules table drives both levels.** It records, for each rule: test, condition (test version, start time, engine version), source repository, commit, file line and issue link. It replaces the version-only logic of `dim_ooni_probe_version_accuracy`.
3. **Both levels apply it.**
   - At measurement level, matching measurements are set aside as today (NULL verdict, gate reason recorded).
   - At observation level, matching rows are kept but flagged with a new `exclusion_reason`, and every asset that counts observations leaves them out, numerators and denominators alike.
   - The existing `KNOWN_SIGNAL_ROOT_CA` exclusion keeps its current behaviour.
4. **Scope, from the read-only sweep:**
   - Signal rules SIG-B2 to SIG-B5 are adopted.
   - The two Tor measurements with no targets are adopted.
   - **DNSCheck's unsupported-test branch is not adopted as an exclusion.** It is recorded as "OONI gives no verdict for this test" and disclosed as a limit.
   - CLIO's 15 existing Signal exclusions that no current OONI rule covers are kept, with their reason documented.
   - OONI's two date-consistency rules can't be computed from CLIO's stored fields (they need `measurement_uid`). They are recorded as a limit.
5. **Rebuild only through `Bruin/scripts/safe_run/safe_materialize.py`**, with before-and-after figures for every changed asset.

## Consequences

- TLS observations classified BLOCKED fall from 361 to 271 (Signal's TLS BLOCKED rows from 133 to 43).
- 1,146 Signal measurements leave the ANOMALOUS count. Signal's weekly anomaly rate for December 2023 to February 2024 drops sharply, which resolves TD-160's open question in favour of a test artefact.
- Dashboard figures move. The README and methodology paper are corrected in the same pass, with the August explanation and the November correction both stated.
- The pinned OONI commit has to be reviewed when OONI changes its scoring code. A newer commit means a new rules-table version.

## Alternatives considered

- **OONI's stored API scores only.** Rejected as the rule: it needs an API lookup per measurement, it changes as OONI reprocesses, and it misses rules OONI has not applied back to old data. It is kept as the check.
- **Deleting excluded rows.** Rejected: flagged rows stay traceable.
- **Following OONI's code for DNSCheck as well.** Rejected: it would remove all DNSCheck evidence because OONI has no scorer for that test, not because its data were found unreliable.
