-- TD-136 Option E acceptance diagnostic. Run after the shadow columns are live.
SELECT
  country,
  COUNT(*) AS total_rows,
  COUNTIF(signal_valid = FALSE AND shadow_global_conditions_valid = TRUE) AS flipped_rows,
  -- superset invariant: must be 0 for every country. Shadow must never be
  -- NULL where the live column is non-NULL, and never a different value.
  COUNTIF(
    (protest_pressure_z IS NOT NULL AND (shadow_protest_pressure_z IS NULL OR shadow_protest_pressure_z != protest_pressure_z))
    OR (violence_pressure_z IS NOT NULL AND (shadow_violence_pressure_z IS NULL OR shadow_violence_pressure_z != violence_pressure_z))
    OR (suppression_z IS NOT NULL AND (shadow_suppression_z IS NULL OR shadow_suppression_z != suppression_z))
  ) AS superset_invariant_violations
FROM `features.acled_pressure_signals`
GROUP BY country
ORDER BY country;
