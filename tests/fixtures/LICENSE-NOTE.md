# Licence note for test fixtures

The code in this repository is under the MIT licence (see `LICENSE` at the repository root). Some files in this folder are not CLIO's own work: they hold data, or values derived from data, that come from third-party sources. Those files stay under their source's terms, not under MIT.

## OONI data: CC BY-NC-SA 4.0

These files contain OONI measurement data or identifiers (for example `report_id`, measurement IDs, probe ASNs, measurement dates and OONI's own verdict fields), or counts aggregated from OONI measurements. They are OONI data, licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Source: Open Observatory of Network Interference (OONI), ooni.org.

- `ooni_dnscheck_bootstrap_classification/`
- `ooni_signal_probe_version_discard/`
- `ooni_whatsapp_endpoints_blocked_count_removed/`
- `ooni_whatsapp_registration_accessible_classification/`
- `ooni_whatsapp_web_accessible_classification/`
- `ooni_weekly_golden/` (weekly counts aggregated from OONI measurements)

## ACLED-derived labels: ACLED's terms

These files contain weekly regime labels, bands and related fields that CLIO's classifier derived from ACLED's weekly aggregated data. They are subject to ACLED's terms of use (free for non-commercial use with registration; commercial use needs a separate licence from ACLED). Source: Armed Conflict Location & Event Data (ACLED), acleddata.com.

- `acled_regimes_golden/`

## Why the files are here

The tests in `tests/` depend on these fixtures, so they are kept in place. Reusing them outside this repository means following the source terms above, including OONI's NonCommercial and ShareAlike conditions.
