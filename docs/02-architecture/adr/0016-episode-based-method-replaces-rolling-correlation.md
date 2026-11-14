# ADR-0016: Replace the rolling OONI–pressure correlation with an episode-based method

- **Status:** Accepted (2026-11-14). Step 1 of 3 built (the detector); steps 2 and 3 to follow.
- **Date:** 2026-11-14
- **Deciders:** Sam (sole owner)
- **Supersedes / Superseded by:** none
- **Related:** TD-80, TD-138, TD-139, TD-140 (the correlation findings), ADR-0011 (OONI weekly aggregation), ADR-0012 (cascade-safe materialization)

---

## Context

`rolling_pressure_corr` relates OONI anomaly rates to the daily composite pressure score with a rolling Pearson correlation. Over its full two-year history it has never produced a STRONG or MODERATE reading. The recorded findings explain why: a confidence weight is applied twice (TD-138), the 31-day window has an effective sample of about five because the pressure series is a weekly broadcast (TD-139), and a per-network table is collapsed to one row per day by picking one network's view (TD-140). The composite itself is about 75–80% ACLED-driven, so the method compares network data against a relabelled conflict count. More fundamentally, information controls are rare, discrete events, and some have triggers unrelated to conflict (Kenya's exam-period Telegram blocks, for example). A continuous coupling score treats those as noise.

## Decision

Replace the coupling score with three separate, checkable parts.

1. **Detection.** `features.ooni_app_block_detector_daily` flags candidate app blocks from CLIO's own per-measurement verdicts, with a rule fixed in advance (baseline, z and excess thresholds in the asset's header), plus an app-specific flag that separates an app-level block from a general connectivity failure. It uses no OONI labels, findings or reports.
2. **Exposure.** A frozen, versioned and hashed list of documented episodes (blocks, outages, throttling, and offline events such as exam periods), built from public sources other than ACLED or CLIO under a written procedure: two independent builds, compared, source-checked, then frozen. It will be loaded as a warehouse table.
3. **Association.** A pre-registered event study at daily grain: does the outcome move around episodes more than around matched placebo windows? It uses shift-permutation p-values and a minimum effect stated in advance. "Cannot tell with this corpus" is a valid published result. Analyses with ACLED outcomes are run by the maintainer outside any AI session, in line with ACLED's terms.

## Transition

This step is additive. `rolling_pressure_corr`, its labels and the tables that read them stay unchanged for now; no published number changes. The next step labels them "retired pending removal" wherever they are shown. Their removal is a later, separate decision.

## Consequences

- Kenya alone yields only a few documented episodes, so Kenya results are descriptive; tests need more countries.
- The detector is built for multi-day blocks of an app. A one-day or partial block may not cross its thresholds. A flag is a candidate event, not a confirmed block, and never a statement about cause.
- A connectivity failure (a cable fault, for example) can still produce an app-specific flag if it reaches one app's measurements first; the flag only partly separates the two.
