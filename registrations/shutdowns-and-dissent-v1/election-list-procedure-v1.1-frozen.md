---
title: "Election list: build procedure v1.1 (frozen)"
date: 2026-11-15
status: FROZEN 2026-11-15 21:43 EAT, together with registration-v1. Private: planning workspace.
incorporates: Fable review of 2026-11-15 (M3, M6, M7, M9, M10, S3–S6, S8, S9) and Sam's scope decision (Stage A now; the agreement rate as a protocol result)
---

# Election list: build procedure v1.1 (frozen)

## 1. Who builds it, and blind conditions
- **Two independent builds**, each by one builder model, the same across all of that build's chats. Each chat is new, with memory off, no folder attached and web search on. It receives only §2–8 of this procedure, the empty template, its country list and `stop_africa_extract.csv` (the Africa rows of Access Now's public STOP sheet, with download date and SHA-256; public exposure data, nothing from CLIO). Builders never see CLIO, the registration, the feasibility counts, or each other's work. They read no ACLED data.
- **At most six countries per chat.** The number of chats follows from that, roughly nine per build. Model names go in the file names.
- **Two stages.**
  - **Stage A (now):** all countries. Election dates (sources 1a/1b), STOP (source 2) and OONI (source 3) only. Every election is classified provisionally.
  - **Stage B (deferred):** the full eight-source check, only for countries where either build found a candidate L in Stage A, plus the countries secondary run 1 needs.

## 2. Scope
- **Countries:** exactly the `COUNTRY` names supplied. Sam prints them from the ACLED file with one command that outputs only the distinct values (metadata).
- **Elections:** direct national votes: presidential, legislative (lower house), general, or a national referendum. Polling days from 2016-01-30 to 2026-02-14.
  - Indirect elections are out. A territory that is not a `COUNTRY` value has no row.
  - Staggered or multi-day polling: anchor on the first day. A postponed election: anchor on the day it was held. An annulled election still counts. Concurrent votes are one row, typed by the highest office.
  - **Polling days in one country less than 56 days apart are one election,** anchored on the first; record the later dates in `note`.
- **Restrictions:** any documented internet restriction in force on any day from 30 days before to 30 days after polling day.

## 3. Sources
1. a. EISA election calendar and archive; b. IFES ElectionGuide. Record both dates. **If they fall in the same Saturday-to-Friday week, use IFES.** Otherwise the electoral commission's own record decides; if none is found, mark the row `ambiguous` with `date_disputed = yes`.
2. Access Now STOP: the supplied extract (search by country and year).
3. OONI: Explorer findings and reports (ooni.org/post).
4. IODA reports and records. *(Stage B)*
5. Cloudflare Radar outage centre and quarterly summaries, 2022 onwards. *(Stage B)*
6. NetBlocks (secondary only). *(Stage B)*
7. Press: international, and at least one named national outlet per country. *(Stage B)*
8. Official records (regulator, government, operator, court), wherever cited. *(Stage B)*

**Coverage table (required):** one row per country, one column per source used in the stage. Values: `searched`, `nothing found`, `unavailable`, `not applicable` (the source does not cover that date) or `not searched` (explain each in the summary).

## 4. Search terms (minimum per country and election)
`<country> internet shutdown <year>`; `<country> election internet <year>`; `<country> social media blocked <year>`; `<country> WhatsApp OR Facebook OR X blocked election`; `<country> internet throttling election`; and the same in French, Portuguese or Arabic where those are official languages. Every search is logged.

## 5. Classification
For each election, take the restriction nearest polling day.

| Condition | `class` | `status` | `timing` |
|---|---|---|---|
| A restriction **started more than 7 days before** polling day and is **in force** on any day from 7 days before to 14 days after it (a standing restriction), and no new restriction starts in the L window | L | ambiguous | standing |
| A restriction starts from 7 days before to polling day (inclusive), meets the evidence standard (§6), and its scope is national or covers networks serving most users | L | included | pre |
| The same, starting 1–14 days after polling day (or after the last polling day of a merged election) | L | included | post |
| A restriction in either window, but the evidence standard or the scope rule is not met | L | ambiguous | pre or post |
| **No documented restriction in force** on any day from 30 days before to 30 days after polling day | C | included | (blank) |
| A restriction in force 15–30 days either side, or STOP could not be checked, or OONI could not be checked for a date it covers | C | ambiguous | (blank) |

- If a standing restriction and a new one in the window coexist, the new one decides; note the standing one.
- **`type`, exactly one of:** `full outage`, `mobile outage`, `regional outage`, `throttling`, `platform block`. If several applied from 7 days before to 27 days after polling day, record the first in that order and list the others in `note`. `throttling` means documented slowing without loss of access. Blocks of news sites or VPNs alone are not restrictions for this study.
- **`scope`:** national / regional (name the regions) / some networks (name them; state whether they serve most users). Regional-only restrictions are `ambiguous`.
- **Duration** in hours, where known, in `note`.
- For C rows, `type` and `timing` are blank. For L rows, a blank or unknown `type` stops the analysis code.
- `anchor_date` is the (first) polling day; `results_date` where found; `stratum` is the country name. `start_date`/`end_date`: for L, the restriction's; for C, polling day −28 to +27 days.

## 6. Evidence standard
An L row is `included` only with **two independent sources, at least one primary.**
- **Primary:** an OONI finding or report; an IODA or Cloudflare report describing the event; a regulator, government, operator or court record.
- A graph or measurement count without a report is not primary.
- **A STOP row and any item it cites are one source.** A STOP row is primary only if the item it cites is primary, or the row records a government or operator acknowledgement with a link.
- Press and NetBlocks are secondary. Two items quoting the same NetBlocks post are one source.

In Stage A, where only STOP and OONI are searched, an L candidate that lacks a second independent source is recorded as `ambiguous` with `status_reason = stage A: second source pending`.

## 7. What is recorded (per chat)
- `elections_<model>_<chat>.csv` in the template columns, one row per election.
- `rejected_<model>_<chat>.csv`: restrictions found outside the ±30 days or not tied to an election, with sources.
- `search_log_<model>_<chat>.csv` and `coverage_<model>_<chat>.csv`.
- A summary: counts by class, status and timing; what was not checked; the grid actually run against §4.

## 8. Comparison, source check and freeze (planning session)
1. When both builds' Stage A chats are complete and saved, merge each build's chats and compare.
2. **Reconciliation:** disagreements are settled from the sources, and Sam decides where they don't. Only afterwards is the list compared with the 2026-11-14 feasibility counts, and differences are examined, not adopted.
3. **Source check** of every `included` L row's sources (archived copies), and a STOP re-check for every `included` C row.
4. Freeze `elections_v1.0-stageA.csv` with a SHA-256 and file time in the decision log.

## 9. The agreement rate (a protocol result, defined before the builds)
Reported from the two builds **before reconciliation**:
- **Election coverage:** elections found by both builds, by one only (by which), and the share found by both.
- **Polling-day agreement:** the share of jointly found elections with the same date, and with the same Saturday-to-Friday week.
- **Classification agreement** over jointly found elections: L-included / L-ambiguous / C-included / C-ambiguous. Raw agreement, and Cohen's kappa with a 95% interval.
- **Timing and type agreement** over elections both builds class as L.
- **Per source:** how often each build's coverage table marked STOP or OONI `unavailable`.
- Every disagreement is listed, with its resolution afterwards.

These figures are reported whatever they show, as evidence of how reproducible documented-restriction lists are.

## 10. Not settled here
- The P list needs its own procedure.
- C means "no documented restriction", not "no restriction". This is stated with every result.
