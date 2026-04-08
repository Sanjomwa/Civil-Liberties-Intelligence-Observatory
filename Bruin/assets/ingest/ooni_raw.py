"""@bruin
name: raw.ooni_conflict_measurements
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Final production version - correctly handles test_start_time + date filter.

materialization:
  type: table
  strategy: create+replace

columns:
  - name: measurement_id
    type: STRING
    description: Unique OONI measurement ID
  - name: country
    type: STRING
    description: Country code
  - name: asn
    type: INTEGER
    description: Autonomous System Number
  - name: test_name
    type: STRING
    description: OONI test type
  - name: input
    type: STRING
    description: Domain or URL tested
  - name: start_time
    type: TIMESTAMP
    description: Measurement start time
  - name: status
    type: STRING
    description: Result status
  - name: probe_cc
    type: STRING
    description: Probe country code
  - name: probe_asn
    type: INTEGER
    description: Probe ASN
  - name: extracted_at
    type: TIMESTAMP
    description: Timestamp when ingested
@bruin"""

import glob
import os
import pandas as pd
from datetime import datetime
from pathlib import Path
import gzip
import json


def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni"
    data_root = os.path.join(base_path, "ooni-kenya-censorship")

    Path(base_path).mkdir(parents=True, exist_ok=True)
    Path(data_root).mkdir(parents=True, exist_ok=True)
    Path("data/dev").mkdir(parents=True, exist_ok=True)

    print(f"📂 Searching in: {data_root}")

    files = sorted(glob.glob(f"{data_root}/**/*.jsonl.gz", recursive=True))
    print(f"Found {len(files):,} raw .jsonl.gz files")

    if not files:
        raise FileNotFoundError("No files found.")

    start_ts = pd.Timestamp("2023-06-01")
    end_ts = pd.Timestamp("2025-06-30")

    dfs = []
    total_read = 0
    total_kept = 0

    # Show the actual field name and value from the first file
    print("\n--- SAMPLE raw start_time from first file ---")
    try:
        with gzip.open(files[0], 'rt', encoding='utf-8') as f:
            line = f.readline().strip()
            if line:
                record = json.loads(line)
                print("Available keys:", list(record.keys()))
                print("start_time value     :", record.get("start_time"))
                print("test_start_time value:", record.get("test_start_time"))
    except Exception as e:
        print(f"Could not read sample: {e}")
    print("--- End of sample ---\n")

    for i, fpath in enumerate(files, 1):
        if i % 50 == 0 or i == 1 or i == len(files):
            print(
                f"Processing {i:,}/{len(files):,} → {os.path.basename(fpath)}")

        try:
            for chunk in pd.read_json(fpath, lines=True, chunksize=80_000, compression="gzip"):
                total_read += len(chunk)

                # === FIX: handle both possible column names ===
                if "test_start_time" in chunk.columns:
                    chunk = chunk.rename(
                        columns={"test_start_time": "start_time"})
                if "start_time" not in chunk.columns:
                    continue

                # Parse the date
                chunk["start_time"] = pd.to_datetime(
                    chunk["start_time"].astype(str),
                    errors="coerce",
                    utc=True,
                    format='mixed'
                ).dt.tz_localize(None)

                mask = (chunk["start_time"] >= start_ts) & (
                    chunk["start_time"] <= end_ts)
                filtered = chunk[mask].copy()

                if not filtered.empty:
                    total_kept += len(filtered)

                    filtered["measurement_id"] = filtered.get(
                        "measurement_uid") or filtered.get("id")
                    if "probe_asn" not in filtered.columns and "asn" in filtered.columns:
                        filtered["probe_asn"] = filtered["asn"]

                    filtered["status"] = "ok"
                    if "anomaly" in filtered.columns:
                        filtered.loc[filtered["anomaly"]
                                     == True, "status"] = "anomaly"
                    if "confirmed" in filtered.columns:
                        filtered.loc[filtered["confirmed"]
                                     == True, "status"] = "confirmed"
                    if "failure" in filtered.columns:
                        filtered.loc[filtered["failure"]
                                     == True, "status"] = "failure"

                    keep_cols = ["measurement_id", "country", "asn", "test_name", "input",
                                 "start_time", "probe_cc", "probe_asn", "status"]

                    for col in keep_cols:
                        if col not in filtered.columns:
                            filtered[col] = None

                    dfs.append(filtered[keep_cols].copy())

        except Exception as e:
            print(f"⚠️ Error in {os.path.basename(fpath)}: {e}")
            continue

    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    print(f"\n=== SUMMARY ===")
    print(f"Total rows read               : {total_read:,}")
    print(f"Rows kept after date filter   : {total_kept:,}")
    print(f"Final rows in Parquet         : {len(df):,}")
    print("===============")

    df["extracted_at"] = datetime.now()
    df = df.reindex(columns=["measurement_id", "country", "asn", "test_name", "input",
                             "start_time", "status", "probe_cc", "probe_asn", "extracted_at"])

    parquet_out = f"{base_path}/ooni_measurements.parquet"
    df.to_parquet(parquet_out, index=False, compression="snappy")

    print(f"\n✅ Parquet created: {parquet_out} with {len(df):,} rows")

    print("\nRAW FILES WERE NOT DELETED.")
    print("You can manually delete the 'ooni-kenya-censorship' folder when ready.")

    return df
