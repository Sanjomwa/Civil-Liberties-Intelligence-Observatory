📊 Data Sources

This project integrates multiple open, public-interest datasets to analyze censorship, conflict, and civil liberties trends. Each source is used in accordance with its licensing and attribution requirements.

🌐 1. OONI (Open Observatory of Network Interference)

Provider: Open Observatory of Network Interference (OONI)
Website: https://ooni.org

Data Access: https://ooni.org/data/

📌 Description

OONI provides global measurements of internet censorship, blocking, and network interference. Data is collected via distributed probes running standardized tests.

📦 Dataset Used
OONI raw measurements (DNS, HTTP, TCP connectivity tests)
Derived into:
fact_ooni_censorship_signals
fact_network_blocking_daily
🔍 Key Fields Used
measurement_id
start_time
country
asn / probe_asn
test_name
input
blocking_signal_type
is_blocked
blocking_confidence
⚙️ Transformations
Normalization of blocking signals into binary is_blocked
Aggregation into:
daily blocking rates
network-level interference signals
Feature engineering:
block_rate
network_block_signals
⚖️ License & Attribution

OONI data is open and publicly available, but attribution is required:

“Data from OONI Explorer (https://explorer.ooni.org/)”

⚔️ 2. ACLED (Armed Conflict Location & Event Data Project)

Provider: ACLED
Website: https://acleddata.com

Data Access: https://acleddata.com/data-export-tool/

📌 Description

ACLED provides real-time data on political violence and protest events worldwide.

📦 Dataset Used
Filtered ACLED dataset (Kenya-focused)
Transformed into:
fact_conflict_events
🔍 Key Fields Used
event_date
country
event_type
sub_event_type
event_count
fatalities
population_exposure
is_censorship_trigger_event
severity_level
⚙️ Transformations
Aggregation to country × date grain
Derived metrics:
conflict_events
fatalities
Used as contextual signal (not causal inference)
⚖️ License & Attribution

ACLED requires explicit attribution:

“Armed Conflict Location & Event Data Project (ACLED); www.acleddata.com”

⚠️ Important:

ACLED data must not be redistributed raw
Only aggregated/derived outputs are used in this project
🏛️ 3. Google Transparency Report

Provider: Google
Website: https://transparencyreport.google.com

📌 Description

Google Transparency Report provides data on government requests for content removal and platform-level moderation actions.

📦 Dataset Used
Summary + detailed reports
Transformed into:
fact_country_pressure_daily
fact_takedown_trends
🔍 Key Fields Used
year, month
request_records
total_requests
total_items_targeted
reason_group
platforms_affected
⚙️ Transformations
Time normalization (monthly → daily alignment where needed)
Aggregation into:
takedown_requests
items_removed
google_requests
⚖️ License & Attribution

Data is publicly available via Google Transparency:

“Source: Google Transparency Report”

📢 4. Lumen Database (Mock / Structured Integration)

Provider: Lumen (Harvard University’s Berkman Klein Center)
Website: https://lumendatabase.org

📌 Description

Lumen collects and analyzes legal complaints and takedown requests related to online content.

📦 Dataset Used
Structured / mock dataset (for pipeline completeness)
Integrated into:
fact_country_pressure_daily
fact_takedown_requests
🔍 Key Fields Used
notice_type
platform
request_origin
items_requested_removal
⚙️ Transformations
Normalized into platform-level takedown metrics
Combined with Google data to form pressure signals
⚖️ License & Attribution

When using real Lumen data:

“Data from the Lumen Database (https://lumendatabase.org/)”

🌍 5. Derived / Analytical Datasets

These are not external sources, but transformations created within this project:

📊 Core Fact Tables
fact_network_blocking_daily
fact_conflict_events
fact_country_pressure_daily
fact_takedown_requests
📈 Reporting Tables
reporting.civil_liberties_mart
reporting.platform_censorship_mart
🔧 Purpose
Harmonize multiple sources into:
Country-level repression signals
Platform-level censorship intelligence
Enable:
dashboards
time-series analysis
suppression pattern detection
⚠️ Data Limitations
ASN data sparsity (OONI probes often missing ASN)
Temporal misalignment
OONI → near real-time
ACLED → event-based
Google → periodic reporting
No causal claims
Correlation ≠ causation
Geographic bias
Focus: Kenya
🧭 Summary
Source	Role	Signal Type
OONI	Network measurement	Technical censorship
ACLED	Conflict events	Political instability
Google Transparency	Platform pressure	Legal/content removal
Lumen	Legal complaints	Content moderation
Derived marts	Unified analytics	Composite indicators
📌 Final Note

This project is designed as a reproducible analytical observatory, not a definitive authority.
All outputs should be interpreted as signals and patterns, not ground truth.
