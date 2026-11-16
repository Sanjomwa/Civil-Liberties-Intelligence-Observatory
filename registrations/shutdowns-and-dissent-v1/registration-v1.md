---
title: "Registration v1: election-timed internet restrictions and recorded dissent and repression, Africa 2016–2026"
date: 2026-11-15
status: FROZEN 2026-11-15 21:43 EAT. Private: planning workspace. At freezing it becomes registration-v1.md with a SHA-256; the hash goes into a public commit; the full text is published with the first verdict-capable results.
supersedes: prereg-draft.md (2026-09-26); registration-v1-DRAFT-exam-superseded-2026-11-14.md; registration-v1-DRAFT-pre-review-2026-11-15.md
incorporates: Fable review of 2026-11-15 (M1–M13, S1–S14) and Sam's decisions of 2026-11-15
code: shutdowns_study.py v0.5.1, SHA-256 2d7ef48bb0218380e84eff8dc9cc359114dd9ff3e1e788c0e1d0b604e83fb80e (make_fixture c03bbddd…7381; test_on_fixture 0de7a36b…e962, 40/40; calibrate 33f1fd5f…963c)
---

# Registration v1 (frozen)

Every choice that could change a result is fixed here before any outcome data for this study is read. Once frozen, changes are allowed only as dated amendments, each with its reason, made before the run it affects.

## 0. What has already been seen (disclosure)
- **Kenya outcomes, 2016–2026, have been read.** On 2026-11-14, `shutdowns_study.py` v0.3.0 ran on ACLED for Kenya around two exam-period Telegram blocks and two protest-period disruptions: a 1997-onwards rehearsal, then three descriptive runs from 2016. The analysis period was chosen after the rehearsal had been seen. Kenya has no restricted election in the period, so it never enters the primary run (§6). It enters only secondary run 1, if the covariate strata place it.
- **Exposure has been seen; outcomes have not.** Fable's feasibility counts of 2026-11-14 used Access Now STOP and web sources, with no ACLED. The analysis code, its windows and its test were written on 2026-11-14 by an AI session that had read the STOP rows, and so knew which elections were restricted; it had read no outcome data. Decisions 1–7 (2026-11-15) were taken with that knowledge of exposure.
- No ACLED outcome data for any country other than Kenya has been analysed in this study.

## 1. Purpose, and how this serves the verification protocol
CLIO's deliverable is a **verification protocol for internet-freedom evidence** (OTF ICRP #23253). This study is a test bed for it, not the deliverable.

| Study component | Protocol step it exercises |
|---|---|
| Election lists from two blind builds, with mandatory sources, an evidence standard, comparison, source checks, freeze and hash | Independent corroboration with an explicit evidence standard; tamper-evident freezing |
| **The agreement rate between the two blind builds** (§14) | **Reproducibility of documented-restriction evidence: a direct protocol result** |
| This registration, the one-primary-run rule and declared secondaries | Pre-specification that limits analytic flexibility |
| Suppression unclaimable from outage runs, association-only wording, the misuse note | Claim calibration: a finding is reported at the strength the evidence supports |
| "AI writes, Sam runs"; contract-only output | Licence-compliant, auditable AI-assisted analysis |
| Corrections logged publicly (ADR-0016, 2026-11-14) | Public correction of overstated claims |

CLIO's own detector is not used in this study. Its positive control (two documented Kenyan Telegram blocks) is separate protocol evidence. The Objective 4 audit-protocol run (100 matched pairs, external evaluator) remains the main deliverable.

## 2. Question and hypotheses
Around national elections in Africa, how do recorded protest, riots and repression change when the internet is restricted, compared with elections in the same country with no documented restriction? This is association only: no causal claim, and no claim about who ordered a restriction.

| ID | Name | Prediction | Primary test |
|---|---|---|---|
| H1 | Backfire | Peaceful protest rises after polling | T1 (Y1), upward |
| H2 | Suppression | Peaceful protest falls after polling | T1 (Y1), downward; see §7.5 |
| H3 | Substitution | The riot share rises | T2 (riot share) |
| H4 | Cover for repression | Protest met with force rises | T3 (Y2) |
| H0 | No association | None of the above beyond the checks | — |

## 3. Elections and classes
**Election.** A direct popular vote: presidential, legislative (lower house) or general election, or national referendum. Indirect elections (for example Somalia's) are out. Staggered or multi-day polling is anchored on its first day. A postponed election is anchored on the day it was held. An annulled election still counts. Concurrent votes are one election, typed by the highest office. A territory that is not a `COUNTRY` value in the outcome file (Somaliland, Zanzibar) has no row. **Polling days in the same country less than 56 days apart are one election,** anchored on the first polling day; a restriction counts for it if it starts from 7 days before the first polling day to 14 days after the last. Polling days 56 or more days apart are separate elections.

| Class | Definition | Role |
|---|---|---|
| **L-pre** | A restriction starts between 7 days before the (first) polling day and that day, meets the evidence standard (§4), and has national scope or covers networks serving most users | **Primary treated set** |
| L-post | The same, starting after the (first) polling day and up to 14 days after the last | Secondary run 2, descriptive |
| L ambiguous | In either window, but the evidence standard or the scope rule is not met; or **a standing restriction** (started more than 7 days before polling day) is in force on any day from 7 days before to 14 days after polling day | Excluded from all runs |
| C | **No documented restriction in force on any day** from 30 days before to 30 days after polling day | Controls |
| C-doubtful | A restriction in force 15–30 days either side but not within −7/+14, or STOP could not be checked, or neither OONI nor IODA could be checked for a date they cover | Secondary run 4 only |

Where a standing restriction and a new pre-emptive one coexist, the new one decides the class and the standing one is noted. **Type** (the first that applies, in this order): full outage, mobile outage, regional outage, throttling, platform block. `platform block` therefore means no outage or throttling of any kind is documented from 7 days before to 27 days after polling day. Duration is recorded in hours where known; no minimum applies, and the number of L lasting under 24 hours is reported.

## 4. Election lists, evidence and period
- Built under `election-list-procedure-v1.1.md` (two blind builds in two stages), then compared, source-checked and frozen with a SHA-256 **after** this registration is frozen and **before** any outcome run.
- **Evidence standard for L:** two independent sources, at least one primary.
  - Primary: an OONI finding or report; an IODA or Cloudflare report that describes the event; a regulator, government, operator or court record.
  - A graph or measurement count without such a report is not primary.
  - **A STOP row and any item it cites are one source.** A STOP row is primary only if the item it cites is itself primary, or the row records a government or operator acknowledgement with a link; otherwise it is secondary.
  - Press and NetBlocks are secondary.
- **Covariates** (secondary run 1 only), from public sources, frozen with the list: the V-Dem Regimes of the World category for the year before the election; `executive` (presidential or general) or `other`; `incumbent` or `open`.
- **Period, fixed now:** the ACLED file already held, covering weeks to 2026-03-14 (`Africa_aggregated_data_up_to_week_of-2026-03-14.csv`, SHA-256 `1d8e4052c5027d8a7f9781471cb49aaaf3fb9d4cefe737ef868747764c92224f`; archived unmodified as the first vintage on 2026-11-15). Polling days from 2016-01-30 (the first with four lead weeks after `--start 2016-01-01`) to 2026-02-14 (27 days before the file's last week). A later release only by amendment before any outcome run. The period is enforced in code (`--anchor-from 2016-01-30 --anchor-to 2026-02-14`): rows outside it are left out of the run and listed. (The file would allow polling days to 2026-02-27; the stricter 2026-02-14 is kept.)

## 5. Outcomes (ACLED aggregated weekly; national series)
Y1 peaceful protest; Y2 protest with intervention plus excessive force against protesters; Y3 riots; Y4 abductions; Y5 arrests; Y6 regions with any Y1–Y3 event; the riot share Y3 / (Y1 + Y3). YB, armed clashes, is a reporting check with no verdict. Y3–Y6 are exploratory.

## 6. Estimator and the primary command
- Code `shutdowns_study.py` v0.5.1 (hash in the header). 4 lead weeks ending before the polling week; the "after" window is 4 weeks from the polling week; L and C are both anchored on the first polling day.
- Statistic: the mean change in log(1+count), L minus C, within country strata. Inference: L/C labels permuted within strata, enumerated exactly when there are at most 100,000 arrangements. Two-sided p, with direction printed.
- **Countries with no usable L-pre election contribute nothing to the primary run.** Of roughly 125 controls, only those in countries with an L-pre election are used.
- **Commands (fixed; every flag checked against v0.5.1 `--help` on 2026-11-15):**
  - Primary: `python3 shutdowns_study.py --input <ACLED file, hash per §4> --episodes elections_v1.0.csv --country <every country in the list> --primary-class LC --lc-design stratified --lc-filter timing=pre --loo strict --min-episodes 10 --mei-count 1.5 --mei-share 0.10 --anchor-from 2016-01-30 --anchor-to 2026-02-14 --start 2016-01-01`
  - Facts-only: the primary command plus `--facts-only`.
  - Power gate: the primary command plus `--power-only`.
  - All other options at v0.5.1 defaults: seed 20261111, 2,000 draws, 500 power draws.

## 7. Decision rules
1. **Supported / contradicted:** Holm-adjusted p (across T1–T3) ≤ 0.05; no same-sign pre-trend (rank test); strict leave-one-out (with each L-pre election dropped in turn, the same direction and p ≤ 0.05); and the minimum effect (§8). The code applies all four in v0.5.1. A result passing the first three but smaller than the minimum effect prints, and is reported as, "detected, below the minimum effect of interest".
2. **Minimum data:** at least 10 usable L-pre elections, counted as v0.5.1 counts them: included status, a complete window, and at least one usable C in the same country. C has no separate minimum: under the stratified design every stratum used has at least one C. v0.5.1 prints the usable L and C counts in the facts-only output; Sam records them before the primary run. Below 10: descriptive only.
3. **T3** can support H4 but in practice cannot contradict it (counts near zero cannot fall far). This is stated with the result.
4. **T1 and T2 are mechanically tied.** If T1 is supported upward and T2 is contradicted in the same run, T2 is reported as a consequence of T1, not as evidence against substitution; the Y3 row shows whether riots themselves changed.
5. **H2 (suppression) — Sam, 2026-11-15:** a downward T1 result is **never** reported as suppression from any run that includes outages; v0.5.1 enforces this in code. It is reported as: "recorded protest fell; this cannot be separated from under-recording." Suppression could be reported only from the platform-blocks-only run (secondary 3), and only if that run meets the full rule in its own right, YB's change there is ×0.80 or higher, and the vintage check passes. The code enforces the outage rule; **the YB and vintage conditions are applied by hand** and shown beside the printed result. **This route is expected to be closed:** the same minimum of 10 usable L applies, and the 2026-11-14 count suggests four or five platform-block elections, so that run will most likely print "descriptive only". Any downward T1 result carries this note: *"Full outages also cut the reporting this data depends on. This result does not show that shutdowns reduce dissent, and must not be cited as a justification for restricting the internet."*

## 8. Minimum effect and the power gate
- Minimum effect of interest: ×1.5 on count outcomes, meaning at least ×1.50 or at most ×0.67; ±0.10 on the riot share.
- **Power gate:** after the facts-only run, Sam runs the `--power-only` command. It prints the run facts and the power table only. The gate figure is **`L-C`, `T1`, rule `three conditions` (Holm, pre-trend, leave-one-out), column `x1.5`**, printed under "POWER GATE FIGURE". It is not the full rule because the full rule includes the minimum effect: an effect of exactly ×1.5 is estimated below the minimum about half the time, so full-rule power at ×1.5 cannot much exceed 0.5. The figure is a simulation estimate. With the fixed seed it is reproducible but not precise, and a reading within about 0.04 of 0.50 is effectively a coin toss. **The rule stands as written whatever the reading:** below 0.50 means descriptive. On a synthetic list shaped like the likely one, the gate figure was 0.50 (full rule 0.38). The run is slow (about eight minutes on that list). Below 0.50: the primary result is declared descriptive before the primary run. The power output may be returned to an AI session. Fable's synthetic test (0.45 with 12 L; 0.38 with 10 L) suggests the gate will probably declare the run descriptive; this is accepted in advance.

## 9. Declared secondary runs (each labelled; none can override the primary)
Each is the primary command with only the stated change.
1. **Covariate strata.** `--episodes elections_v1.0_covariate-strata.csv`: a derived list made at freezing by one rule. Countries with an included L-pre and no included C ("L-only"), and countries with included C and no included L ("C-only"), get `stratum` = RoW category | executive or other | incumbent or open. All other rows keep stratum = country. The derived list is hashed with the main list.
2. **L-post:** `--lc-filter timing=post --descriptive-only` in place of the primary filter.
3. **Platform blocks only:** add `--lc-filter "type=platform block"` (it combines with `timing=pre` by AND).
4. **C-doubtful included:** add `--include-ambiguous-controls` (promotes ambiguous C rows only; ambiguous L rows stay out).
5. **Without Kenya:** applies to run 1 only.

P (other political restrictions) is **not run** under this registration; it needs its own procedure and an amendment. No other combination of settings is run on real data. Running one is a deviation, reported as such.

## 10. Checks that run whatever the result
- Facts-only first; the file-level empty-week stop; Saturday-anchored weeks.
- **ACLED vintages:** from freezing, every ACLED download is archived with its date and never overwritten. The vintage check compares the same past weeks between two vintages taken at least 8 weeks apart. Without two vintages, the platform-only suppression route (§7.5) is closed.
- YB reporting check, pre-trend, strict leave-one-out.

## 11. Running and records
- "AI writes, Sam runs": Sam runs every real-data command himself, outside any AI session. Only contract output is returned.
- **One primary run.** Secondaries exactly as in §9.
- Every run's input hash, list hash and code hash are recorded. **Order is evidenced by file hashes and file times, not typed clock times.**

## 12. Reporting
- Association language only. ACLED attributed in every output.
- Every hypothesis is reported, including unsupported ones, with the permutation result and leave-one-out.
- The lead-week rows for L and for C are always reported. The absence of a flagged pre-trend is not reported as evidence of comparable trends.
- **What the controls are:** results are stated as "against elections with no *documented* restriction", never "elections without restrictions". The number of C elections is reported by period (2016–2018, 2019–2021, 2022 onwards), and by whether an OONI report or an Access Now election-watch entry exists for that country and year.
- The registration text is published with the first verdict-capable results; deviations are listed with dates.

## 13. Before freezing
1. ~~v0.5.1~~ **Done 2026-11-15:** hash inserted; flags confirmed against `--help`; gate figure in §8; planning check: hashes match, 40/40 rerun independently, no country literals.
2. Make `stop_africa_extract.csv` (Africa rows of the public STOP sheet, with download date and SHA-256) for the builders.
3. Start the ACLED vintage archive: keep one dated, unmodified copy of the current file and record its SHA-256.
4. **Done 2026-11-15 21:43 EAT:** frozen as `registration-v1.md`, record its SHA-256 and the file time, and put the hash in a public commit. At the same commit, add a "Step 4" note to public ADR-0016: the regional design compares elections with and without a restriction by permuting labels within countries; registration hash given.

## 14. Scope after freezing (Sam, 2026-11-15)
Only **Stage A** of the two blind builds runs now (procedure §1). Its **agreement rate** (procedure §9) is reported as a protocol result. Stage B, the covariates and every outcome run are deferred; work returns to the Objective 4 audit run.

## Amendments
*(None. Begins at freezing.)*
