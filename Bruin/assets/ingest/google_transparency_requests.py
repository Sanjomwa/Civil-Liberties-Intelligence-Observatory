"""@bruin
tags:
  - raw_dev
  - dataset_google_transparency_requests
name: raw.google_transparency_requests
type: python
image: python:3.12
connection: duckdb-parquet
description: Ingests Google Transparency removal requests CSV and exports as Parquet.

materialization:
  type: table
  strategy: create+replace

columns:
  - name: time_period
    type: STRING
    description: Reporting period
  - name: country
    type: STRING
    description: Country issuing request
  - name: cldr_territory
    type: STRING
    description: CLDR territory code
  - name: requestor
    type: STRING
    description: Entity making the request
  - name: product
    type: STRING
    description: Google product targeted
  - name: reason
    type: STRING
    description: Reason for takedown
  - name: number_of_requests
    type: INTEGER
    description: Number of requests
  - name: items_requested_removal
    type: INTEGER
    description: Items requested for removal
  - name: items_removed_legal
    type: INTEGER
    description: Items removed due to legal reasons
  - name: items_removed_policy
    type: INTEGER
    description: Items removed due to platform policy
  - name: extracted_at
    type: TIMESTAMP
    description: Pipeline extraction timestamp
@bruin"""

import os
import pandas as pd
from datetime import datetime
from pathlib import Path


def resolve_env(fallback: str = "dev") -> str:
    for k in ("BRUIN_ENV", "BRUIN_ENVIRONMENT", "BRUIN_PIPELINE_ENVIRONMENT"):
        v = os.getenv(k)
        if v and v.strip():
            return v.strip().lower()
    return fallback


def require_dev(env: str) -> None:
    if env != "dev":
        raise ValueError(f"This raw asset is dev-only. Got ENV={env!r}.")


ENV = resolve_env(fallback="dev")
require_dev(ENV)


def resolve_csv_file(base_path: Path) -> Path:
    # TD-89/TD-81 (2026-08-15): Google's export tool now nests the current-
    # format CSV under a dated bundle folder
    # (government-removals_<start>_<end>_en_v1/), not directly under
    # base_path -- glob for it rather than hardcoding one dated folder
    # name, since this will presumably change with each future export.
    # Bundle folder names embed non-zero-padded dates (e.g.
    # "government-removals_2025-7-1_2025-12-31_en_v1"), which do not sort
    # chronologically as plain strings -- pick by file mtime instead, so
    # the most recently-downloaded export bundle wins regardless of its
    # folder name's shape.
    candidates = sorted(
        base_path.glob("government-removals_*_en_v1/google-government-removal-requests.csv"),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No google-government-removal-requests.csv found under "
            f"{base_path}/government-removals_*_en_v1/"
        )
    return candidates[-1]


def materialize():
    base_path = Path("/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/google")
    csv_file = resolve_csv_file(base_path)
    parquet_out = base_path / "google_transparency_requests.parquet"

    print(f"📂 Reading Google requests CSV: {csv_file}")

    # TD-89/TD-81 (2026-08-15): Google's real current-format export uses
    # country_name/items_requested, not country/items_requested_removal --
    # confirmed against the file's own header row. Renamed back to CLIO's
    # existing column names immediately after reading, so this fix is
    # scoped to the read only; every downstream consumer (this asset's own
    # declared columns, stg.google_transparency_requests, and anything
    # reading that table) is untouched.
    df = pd.read_csv(csv_file)
    df = df.rename(columns={
        "country_name": "country",
        "items_requested": "items_requested_removal",
    })
    df = df[[
        "time_period", "country", "cldr_territory", "requestor", "product", "reason",
        "number_of_requests", "items_requested_removal",
        "items_removed_legal", "items_removed_policy"
    ]].copy()

    df["extracted_at"] = datetime.now()
    df.to_parquet(parquet_out, index=False, compression="snappy")

    print(f"✅ Ingested {len(df):,} rows → google_transparency_requests")
    return df
