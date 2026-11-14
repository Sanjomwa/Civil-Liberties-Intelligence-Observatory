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
3. **Association.** An event study, specified in advance, using weekly outcome windows around daily-dated episodes: does the outcome move around episodes more than around matched placebo windows? It uses shift-permutation p-values and a minimum effect to be stated in a frozen registration before any verdict-capable run. "Cannot tell with this corpus" is a valid published result. Analyses with ACLED outcomes are run by the maintainer outside any AI session, under the project's interim practice for ACLED's terms of use (not reviewed by ACLED).

## Transition

This step is additive. `rolling_pressure_corr`, its labels and the tables that read them stay unchanged for now; no published number changes. The next step labels them "retired pending removal" wherever they are shown. Their removal is a later, separate decision.

## Consequences

- Kenya alone yields only a few documented episodes, so Kenya results are descriptive; tests need more countries.
- The detector is built for multi-day blocks of an app. A one-day or partial block may not cross its thresholds. A flag is a candidate event, not a confirmed block, and never a statement about cause.
- A connectivity failure (a cable fault, for example) can still produce an app-specific flag if it reaches one app's measurements first; the flag only partly separates the two.

## Step 2 notes (2026-11-14)

- The frozen Kenya episode list v1.0 is loaded as `features.shutdown_episodes_v1_0` (4 episodes: 2 included, 2 ambiguous). It is the exposure input for step 3.
- The app-specific flag has been checked for Telegram only: in one run specified in advance, it flagged both documented exam-period Telegram blocks from their first day. That is two events, not a detection rate. The WhatsApp (9 days) and Signal (4 days) app-specific flags have not been checked against any known event and must not be reported as findings until they are.
- `rolling_pressure_corr` is labelled retired pending removal in the docs and dashboard. Removal waits until a replacement display exists, the pages that read it are updated, and any related review is complete.

## Step 3 notes (2026-11-14)

- A first Kenya run of the event study was made on 2026-11-14. The maintainer ran it himself; no AI system was given ACLED data. The analysis code was written with AI assistance and tested on synthetic data only, and only summary output was returned to an AI session. This is the project's interim practice under ACLED's terms of use; ACLED has not reviewed it.
- Data: ACLED aggregated weekly data (Armed Conflict Location & Event Data, acleddata.com), the release covering weeks up to 2026-03-14, Kenya, aggregated by CLIO into weekly national series; and the frozen episode list v1.0.
- The analysis code and the episode list were fixed and hashed before the run. One setting was not: the analysis period (2016 onwards, the years the episode search covered) was chosen after a trial run on the full history had been seen. The estimates were the same in both.
- Outcome windows are weekly because the aggregated data is weekly; episodes are dated to the day. "Daily grain" in the Decision section was wrong and is corrected.
- With two exam-period episodes, the Kenya run is descriptive by design. It gives no verdict, and none is reported. Two episodes are too few to say anything about effects in either direction.
- Corrections to earlier text in this ADR:
  - "Pre-registered": the plan was specified in advance through dated decisions, a hashed script and a hashed episode list. It has not yet been frozen as a single registration, and the analysis period was set after the trial run.
  - "A minimum effect stated in advance": none has yet been stated for ACLED outcomes. The only minimum effect on record is for the Telegram anomaly rate.
  - The episode list v1.0 contains network restrictions only, not offline events, and came from a partial search of the sources its procedure names.
  - The retired label is on the two dashboard pages that display the measure, in three documents, and (from this change) on the Methodology page and in the README.
- Tests that can give a verdict wait for a frozen registration and the regional episode lists.
