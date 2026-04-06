"""@bruin
name: raw.ooni_conflict_measurements
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Converts filtered Kenya OONI raw JSONL files into a clean Parquet file.
  Runs best in dev environment.

materialization:
  type: table
  strategy: create+replace

columns:
  - name: measurement_id
    type: STRING
  - name: country
    type: STRING
  - name: asn
    type: INTEGER
  - name: test_name
    type: STRING
  - name: input
    type: STRING
  - name: start_time
    type: TIMESTAMP
  - name: status
    type: STRING
  - name: probe_cc
    type: STRING
  - name: probe_asn
    type: INTEGER
  - name: extracted_at
    type: TIMESTAMP
@bruin"""

import glob
import os
import pandas as pd
from datetime import datetime
from pathlib import Path


def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni"
    parquet_out = f"{base_path}/ooni_measurements.parquet"

    print("📂 Scanning raw OONI files...")
    files = sorted(glob.glob(f"{base_path}/**/*.jsonl.gz", recursive=True))
    print(f"Found {len(files):,} raw .jsonl.gz files (~4 GB)")

    if not files:
        raise FileNotFoundError("No raw files found in data/dev/ooni. Please copy the downloaded data first.")

    start_ts = pd.Timestamp("2023-06-01")
    end_ts = pd.Timestamp("2025-06-30")

    dfs = []

    for i, fpath in enumerate(files, 1):
        if i % 50 == 0 or i == 1 or i == len(files):
            print(f"Processing {i:,}/{len(files):,} → {os.path.basename(fpath)}")

        try:
            for chunk in pd.read_json(fpath, lines=True, chunksize=120_000, compression="gzip"):
                if chunk.empty or "start_time" not in chunk.columns:
                    continue

                chunk["start_time"] = pd.to_datetime(chunk["start_time"], errors="coerce")
                mask = (chunk["start_time"] >= start_ts) & (chunk["start_time"] <= end_ts)
                filtered = chunk[mask].copy()

                if filtered.empty:
                    continue

                # Robust OONI column handling
                filtered["measurement_id"] = filtered.get("measurement_uid") or filtered.get("id")
                if "probe_asn" not in filtered.columns and "asn" in filtered.columns:
                    filtered["probe_asn"] = filtered["asn"]

                filtered["status"] = "ok"
                if "anomaly" in filtered.columns:
                    filtered.loc[filtered["anomaly"] == True, "status"] = "anomaly"
                if "confirmed" in filtered.columns:
                    filtered.loc[filtered["confirmed"] == True, "status"] = "confirmed"
                if "failure" in filtered.columns:
                    filtered.loc[filtered["failure"] == True, "status"] = "failure"

                keep_cols = ["measurement_id", "country", "asn", "test_name", "input",
                             "start_time", "probe_cc", "probe_asn", "status"]
                
                for col in keep_cols:
                    if col not in filtered.columns:
                        filtered[col] = None

                dfs.append(filtered[keep_cols].copy())

                if len(dfs) >= 15:
                    df_temp = pd.concat(dfs, ignore_index=True)
                    dfs = [df_temp]

        except Exception as e:
            print(f"⚠️ Error in {os.path.basename(fpath)}: {e}")
            continue

    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    print(f"\n✅ Loaded {len(df):,} measurements.")

    df["extracted_at"] = datetime.now()
    df = df.reindex(columns=["measurement_id", "country", "asn", "test_name", "input",
                             "start_time", "status", "probe_cc", "probe_asn", "extracted_at"])

    df.to_parquet(parquet_out, index=False, compression="snappy")
    print(f"✅ Parquet file created successfully: {parquet_out}")

    # ==================== CLEANUP RAW FILES ====================
    cleanup = input("\nDelete all raw .jsonl.gz files to free ~4GB? (yes/no): ").strip().lower()
    if cleanup in ["yes", "y"]:
        print("🗑️ Deleting raw files...")
        for f in files:
            try:
                os.remove(f)
            except:
                pass
        print("✅ Raw files deleted. Space freed.")
    else:
        print("Raw files kept.")

    return df