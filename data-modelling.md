# Data Modelling Documentation

## Overview
This project integrates multiple datasets (Google Transparency, Lumen, OONI, ACLED) into a unified civil liberties mart. The modelling ensures examiner-friendly reproducibility, temporal alignment, and standardized dimensions.

## Fact Tables
- **fact.takedown_requests** → Google Transparency requests
- **fact.lumen_platforms** → Lumen takedown requests
- **fact.censorship_tests** → OONI censorship measurements
- **fact.conflict_events** → ACLED conflict events

Each fact table:
- Normalized on `country`, `period`, `half_year_label`
- Includes `extracted_at` for pipeline provenance
- Enforces custom checks (valid ranges, non-null, uniqueness)

## Dimension Tables
- **dims.country** → harmonized ISO-style country codes/names
- **dims.platform** → unified platform identifiers (Google + Lumen)
- **dims.event_type** → conflict + censorship event types
- **dims.reasons** → takedown request reasons (Google + Lumen)
- **dims.periods** → standardized reporting periods (Jun 2023–Jun 2025)

## Civil Liberties Mart
- Combines all facts + dims
- Aligns by `country` and `period`
- Aggregates takedown requests, censorship tests, conflict events, fatalities
- Provides examiner-friendly schema for dashboards

## Analytical Views
- **Top Platforms by Requests**
- **Conflict vs Takedowns**
- **Censorship vs Requests**
- **Narrative Summary**

These views simplify analysis and storytelling.


