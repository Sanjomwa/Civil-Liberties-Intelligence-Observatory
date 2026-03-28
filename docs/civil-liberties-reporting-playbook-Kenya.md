# 📔Civil Liberties Reporting Playbook

## 1. Conflict & Civil Liberties (ACLED)  
Question:
```
Show me monthly fatalities in Kenya from conflict events over the last 3 years.
```
→ Uses fact_conflict_events (group by year, month).
→ Output: time‑series line chart.

## 2. Distribution
```
Show me the distribution of conflict event types in Kenya (protests, battles, violence against civilians).
```
→ Uses fact_conflict_events + dims.event_type.
→ Output: categorical bar chart.

## 3. Heatmap  
Question:
```
Show me conflict intensity by region (admin1) within Kenya, measured by fatalities and event counts.
```
→ Uses fact_conflict_events.
→ Output: geo heatmap.

## 4. Internet Censorship (OONI)
 Question:
```
Show me the number of censorship tests vs blocked outcomes in Kenya over time.
```
→ Uses fact_censorship_tests.
→ Output: dual line chart.

## 5. Blocked platforms
Question:
```
Show me the breakdown of blocked platforms in Kenya (social media, messaging apps, news sites).
```
→ Uses fact_censorship_tests + classification of input.
→ Output: pie chart.

## 6. Top URLs/apps
Question:
```
Show me the top 10 URLs/apps blocked in Kenya.
```
→ Uses fact_censorship_tests.
→ Output: ranked table.

## 7. Government Takedown Requests (Google Transparency)
Question:
```
Show me takedown requests in Kenya by type (court order vs government request).
```
→ Uses fact_takedown_requests.
→ Output: bar chart.

## 8. Content types 
Question:
```
Show me content types targeted in Kenya (YouTube, Search, Blogger).
```
→ Uses fact_takedown_requests.
→ Output: stacked bar chart.

## 9. Growth
Question:
```
Show me the growth in takedown requests in Kenya over time.
```
→ Uses fact_takedown_requests.
→ Output: line chart.

## 10. Legal Requests (Lumen)  
Question:
```
Show me legal requests in Kenya by sender type (government, corporations, individuals).
```
→ Uses fact_lumen_platforms.
→ Output: bar chart.

## 11. Most targeted platforms 
Question:
```
Show me the platforms most targeted by legal requests in Kenya.
```
→ Uses fact_lumen_platforms + dims.platform.
→ Output: pie chart.

## 12. Notable legal request
Question:
```
Show me a sample of notable legal requests filed in Kenya.
```
→ Uses fact_lumen_platforms.
→ Output: table.

## 13. Cross‑Dataset Insights
 Question:
```
Show me conflict fatalities vs blocked censorship tests in Kenya over the same timeline.
```
→ Joins fact_conflict_events + fact_censorship_tests.
→ Output: dual line chart.

## 14. Correlation scatter plot:  
Question:
```
Show me the correlation between takedown requests and censorship tests in Kenya.
```
→ Joins fact_takedown_requests + fact_censorship_tests.
→ Output: scatter plot.

## 15. Composite dashboard tile:  
Question:
```
Show me a monthly summary for Kenya including conflict events, fatalities, blocked tests, takedown requests, and legal requests.
```
→ Uses mart.civil_liberties.
→ Output: summary tile.

### 🔹 How the Mart Supports This
Country filter → dashboards can filter to Kenya easily.
Year + Month keys → all visuals can be time‑series.
Measures aligned in one table → cross‑dataset comparisons are straightforward.
Dims (event type,platform e.t.c.) → allow drill‑downs and breakdown charts.

# SQL QUERIES FOR CROSS-REFERENCE

## 1. Monthly fatalities in Kenya (last 3 years)
```
SELECT year, month, SUM(fatalities) AS total_fatalities
FROM fact.conflict_events
WHERE country = 'Kenya'
  AND year >= strftime(current_date, '%Y')::INT - 3
GROUP BY year, month
ORDER BY year, month;
```

## 2. Distribution of conflict event types
```
SELECT event_type, SUM(event_count) AS total_events
FROM fact.conflict_events
WHERE country = 'Kenya'
GROUP BY event_type
ORDER BY total_events DESC;
```

## 3. Conflict intensity by region
```
SELECT admin1, SUM(event_count) AS total_events, SUM(fatalities) AS total_fatalities
FROM fact.conflict_events
WHERE country = 'Kenya'
GROUP BY admin1
ORDER BY total_events DESC;
```

## 4. Censorship tests vs blocked outcomes
```
SELECT strftime(start_time, '%Y-%m') AS month,
       COUNT(*) AS total_tests,
       SUM(CASE WHEN status IN ('blocked','anomaly') THEN 1 ELSE 0 END) AS blocked_tests
FROM fact.censorship_tests
WHERE country = 'Kenya'
GROUP BY month
ORDER BY month;
```

## 5. Breakdown of blocked platforms
```
SELECT CASE
           WHEN LOWER(input) LIKE '%facebook%' OR LOWER(input) LIKE '%twitter%' OR LOWER(input) LIKE '%tiktok%' THEN 'Social Media'
           WHEN LOWER(input) LIKE '%whatsapp%' OR LOWER(input) LIKE '%telegram%' THEN 'Messaging Apps'
           WHEN LOWER(input) LIKE '%news%' OR LOWER(input) LIKE '%bbc%' OR LOWER(input) LIKE '%cnn%' THEN 'News Sites'
           ELSE 'Other'
       END AS platform_category,
       COUNT(*) AS blocked_count
FROM fact.censorship_tests
WHERE country = 'Kenya' AND status IN ('blocked','anomaly')
GROUP BY platform_category
ORDER BY blocked_count DESC;
```

## 6. Top 10 URLs/apps blocked
```
SELECT input, COUNT(*) AS blocked_count
FROM fact.censorship_tests
WHERE country = 'Kenya' AND status IN ('blocked','anomaly')
GROUP BY input
ORDER BY blocked_count DESC
LIMIT 10;
```

## 7. Takedown requests by type
```
SELECT request_type, SUM(request_count) AS total_requests
FROM fact.takedown_requests
WHERE country = 'Kenya'
GROUP BY request_type;
```

## 8. Content types targeted
```
SELECT content_type, SUM(item_count) AS total_items
FROM fact.takedown_requests
WHERE country = 'Kenya'
GROUP BY content_type
ORDER BY total_items DESC;
```

## 9. Growth in takedown requests
```
SELECT period, SUM(request_count) AS total_requests
FROM fact.takedown_requests
WHERE country = 'Kenya'
GROUP BY period
ORDER BY period;
```

## 10. Legal requests by sender type
```
SELECT sender, COUNT(*) AS total_requests
FROM fact.lumen_platforms
WHERE country = 'Kenya'
GROUP BY sender
ORDER BY total_requests DESC;
```

## 11. Platforms most targeted
```
SELECT recipient AS platform, COUNT(*) AS total_requests
FROM fact.lumen_platforms
WHERE country = 'Kenya'
GROUP BY recipient
ORDER BY total_requests DESC;
```

## 12. Sample of notable legal requests
```
SELECT request_id, sender, recipient, date_submitted, reason
FROM fact.lumen_platforms
WHERE country = 'Kenya'
ORDER BY date_submitted DESC
LIMIT 10;
```

## 13. Conflict fatalities vs blocked tests
```
SELECT cf.year, cf.month,
       SUM(cf.fatalities) AS total_fatalities,
       SUM(CASE WHEN ct.status IN ('blocked','anomaly') THEN 1 ELSE 0 END) AS blocked_tests
FROM fact.conflict_events cf
LEFT JOIN fact.censorship_tests ct
  ON cf.country = ct.country
 AND cf.year = strftime(ct.start_time, '%Y')::INT
 AND cf.month = strftime(ct.start_time, '%m')::INT
WHERE cf.country = 'Kenya'
GROUP BY cf.year, cf.month
ORDER BY cf.year, cf.month;
```

## 14. Correlation scatter plot
```
SELECT td.request_count AS takedown_requests,
       COUNT(ct.measurement_id) AS censorship_tests
FROM fact.takedown_requests td
JOIN fact.censorship_tests ct
  ON td.country = ct.country
WHERE td.country = 'Kenya'
GROUP BY td.request_count;
```

## 15. Monthly summary (mart)
```
SELECT year, month,
       SUM(conflict_events) AS conflict_events,
       SUM(fatalities) AS fatalities,
       SUM(censorship_tests) AS censorship_tests,
       AVG(blocked_pct) AS blocked_pct,
       SUM(takedown_requests) AS takedown_requests,
       SUM(lumen_requests) AS legal_requests
FROM mart.civil_liberties
WHERE country = 'Kenya'
GROUP BY year, month
ORDER BY year, month;
```
