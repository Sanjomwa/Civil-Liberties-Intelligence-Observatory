## Project Walkthrough

This project is a Bruin-orchestrated civil-liberties intelligence platform that reconstructs censorship pressure and digital repression indicators in Kenya using network measurements, political-pressure signals, and statistical intelligence layers.
The system combines:
• OONI network measurement evidence
• ACLED political/conflict indicators
• Google Transparency reporting signals
• legal/platform pressure modeling
• protocol-level intelligence features
• explainable analytical guardrails
The result is a governed analytical pipeline that transforms raw internet observability data into interpretable intelligence outputs.

---

## Architecture Overview

The platform follows a layered analytical architecture:
Raw Sources
↓
Ingestion Layer
↓
Staging Layer
↓
Intermediate Interpretation Layer
↓
Facts & Dimensions
↓
Feature Engineering Layer
↓
Intelligence Layer
↓
Reporting & Streamlit Dashboard
Core principle:
• facts capture evidence
• features produce stable analytical signals
• intelligence interprets relationships
• reporting exposes product-safe outputs

---

## Data Sources

### OONI

Used for:
• DNS anomaly detection
• TCP connectivity failures
• TLS handshake disruptions
• HTTP interference patterns
• protocol-level censorship indicators

### ACLED

Used for:
• protest activity
• political unrest
• conflict escalation
• state-pressure indicators

### Google Transparency Signals

Used for:
• government request visibility
• platform/legal restriction context
• transparency-event overlays

### Legal / Platform Pressure Signals

Modeled into:
• legal pressure scores
• institutional pressure indicators
• composite repression signals

---

## Bruin Pipeline Usage

Bruin orchestrates the full analytical workflow:
• Python ingestion assets
• SQL transformation assets
• validation and quality checks
• dependency management
• feature and intelligence materialization
• reporting marts
• BigQuery execution orchestration

### The repository includes:

• staging assets
• intermediate assets
• marts
• feature engineering layers
• intelligence layers
• reporting assets
• Streamlit analytical services

---

## Key Analytical Layers

1. Feature Layer
   Example:
   features.protocol_daily_signals
   This layer computes:
   • protocol signal rates
   • anomaly scores
   • rolling baselines
   • confidence-weighted interference
   • sparsity flags
   • low-sample guards
   • statistical quality metrics
   The feature layer intentionally avoids making intelligence claims.

---

2. Intelligence Layer
   Example:
   intelligence.protocol_relationships
   This layer computes:
   • protocol-pressure relationships
   • lag analysis
   • synchronized escalation states
   • divergence states
   • relationship confidence
   • regime classifications
   Outputs are explainable and confidence-weighted.

---

## Dashboard Walkthrough

### National Stress Observatory

High-level national observability surface showing:
• censorship pressure windows
• protocol instability
• pressure escalation periods
• historical stress trends
What it demonstrates
A country-scale analytical overview built from governed feature marts.

---

### Protocol Regime Monitor

Tracks protocol-specific behavior across:
• DNS
• HTTP
• TCP
• TLS
Shows:
• anomaly shifts
• regime classifications
• signal volatility
• protocol escalation periods
What it demonstrates
Protocol-level intelligence modeling rather than simple aggregate dashboards.

---

### ASN Behavioral Intelligence

Analyzes network/operator-level behavior:
• anomalous ASNs
• interference concentration
• behavioral shifts
• confidence-weighted protocol observations
What it demonstrates
Network-level analytical decomposition and operator observability.

---

### Protocol-Repression Correlation Engine

Explores:
• lag relationships
• synchronized escalation
• divergence states
• pressure/censorship alignment
Includes statistical guardrails:
• sparse-window flags
• confidence scoring
• non-causality warnings
• sample-quality controls
What it demonstrates
Explainable intelligence modeling with methodological safeguards.

---

### Finance Bill 2024 Incident Reconstruction

A case-study reconstruction of digital-pressure dynamics during the Kenya Finance Bill protests.
Combines:
• protocol anomalies
• pressure escalation
• temporal alignment
• analytical interpretation
What it demonstrates
Real-world applicability of the platform during major civic events.

---

### Methodological Guardrails

The platform intentionally avoids overstating certainty.
Important principles:
• correlation is not causation
• OONI anomalies are probabilistic signals
• low-sample windows are confidence-adjusted
• sparse observations are explicitly flagged
• rolling metrics include statistical safeguards
• protocol observations are weighted separately from measurements
The goal is explainable observability, not unverifiable certainty claims.

---

Live Demo
Streamlit deployment:
https://civil-liberties-and-censorship-analysis-with-bruin-toafjdj5xoc.streamlit.app/
Live Dashboard

---

### Why This Project Matters

Internet censorship and digital repression are often opaque, fragmented, and difficult to interpret in real time.
This project explores how reproducible data engineering, observability pipelines, and explainable intelligence layers can help reconstruct pressure dynamics from heterogeneous evidence sources while maintaining methodological transparency.

By combining network measurements, political indicators, and transparency signals into a governed analytical workflow, we can produce interpretable intelligence outputs that inform civil liberties advocacy, policy analysis, and public awareness.
The project also serves as a case study for how Bruin can orchestrate complex analytical pipelines that integrate multiple data sources, transformation layers, and reporting outputs while maintaining explainability and methodological rigor.
