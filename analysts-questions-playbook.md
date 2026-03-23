# Verification & Debug
run:
  - Schema discovery: list all fact + dim tables with row counts.
  - Data freshness: latest extracted_at timestamp.
  - Quality checks: confirm no NULLs in key columns.
  - Lineage awareness: trace mart dependencies back to raw.
  - Simple aggregation: count events per dims.event_type.


## 1.Censorship Regime Analysis (Crown Jewel)
Question
```
What is the current censorship regime in Kenya?
Show me the classification, severity score,
percentage of blocked domains across OONI tests,
and a narrative summary.
```
→ Hits fact_censorship_tests + dims.country.
→ Output: single row with regime, score, % blocked, narrative.
→ Screenshot: censorship_regime_analysis.png.

## 2. Top Platforms by Legal Requests
Question
```
Show me the top 10 platforms targeted by takedown requests,
with request type (legal vs platform),
confidence level, and total request count.
```
→ Hits fact_lumen_platforms + dims.platform.
→ Screenshot: top_platform_requests.png.

## 3. Conflict Trend (Shows Data Depth)  
Question:
```
How have conflict events evolved over the last 90 days?
Show me the distribution of event types and
the current trend direction.
```
→ Hits fact_conflict_events + dims.event_type.
→ Screenshot: conflict_distribution.png.

## 4. Top/Bottom Requesting Countries in Africa   
Question:
```
What are the top 5 countries issuing takedown requests
and the bottom 5 over the past year?
Include request counts and platforms targeted.
```
→ Hits takedown_requests + platforms_targeted.
→ Screenshot: top_requesting_countries.png.

### X Posts
## 5. Cross‑Category Comparison
Question
```
Compare censorship severity between conflict‑heavy countries,
high‑request countries, and low‑request countries.
Which category shows the strongest suppression signals?
```
→ Joins conflict + takedown facts.
→ Screenshot: category_comparison.png.

## 6. Volume Anomalies (Whale Detection Equivalent)
Question
```
Which platforms have abnormally high takedown requests
relative to their user base? Show any with a ratio above 0.3.
```
→ Hits fact_lumen_platforms.
→ Screenshot: platform_anomalies.png.

## 7. Contrarian Signal
Question
```
Are there any countries with rising censorship tests
while conflict events are declining?
This would indicate contrarian suppression patterns.
```
→ Joins censorship + conflict facts.
→ Screenshot: contrarian_signals.png.

## 8. Dominance Shift
Question
```
Show me the breakdown of takedown requests by platform.
What percentage is controlled by mega‑platforms
versus smaller services combined?
```
→ Hits fact_lumen_platforms + dims.platform.
→ Screenshot: platform_dominance.png.

### 📁File Naming Convention

```
docs/ai_analyst_screenshots/
├── censorship_regime_analysis.png
├── top_platform_requests.png
├── conflict_distribution.png
├── top_requesting_countries.png
├── category_comparison.png
├── platform_anomalies.png
├── contrarian_signals.png
└── platform_dominance.png
```
