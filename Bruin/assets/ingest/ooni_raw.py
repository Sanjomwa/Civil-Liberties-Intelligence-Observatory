"""@bruin
name: raw.ooni_conflict_measurements
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Ingests OONI censorship measurement data from the public OONI S3 bucket.
  Syncs ONLY Kenya-specific JSONL files from June 2023–June 2025.
  Uses precise includes to avoid downloading any data from 2020–2022.

materialization:
  type: table
  strategy: create+replace

packages:
  - pandas

columns:
  - name: measurement_id
    type: STRING
    description: Unique OONI measurement ID
  - name: country
    type: STRING
    description: Country code (ISO two-letter)
  - name: asn
    type: INTEGER
    description: Autonomous System Number (network identifier)
  - name: test_name
    type: STRING
    description: OONI Probe test type (e.g. web_connectivity, whatsapp)
  - name: input
    type: STRING
    description: Domain or URL tested
  - name: start_time
    type: TIMESTAMP
    description: Measurement start time (UTC)
  - name: status
    type: STRING
    description: Result status (ok, anomaly, confirmed, failure)
  - name: probe_cc
    type: STRING
    description: Country code of probe
  - name: probe_asn
    type: INTEGER
    description: ASN of probe
  - name: extracted_at
    type: TIMESTAMP
    description: Timestamp when ingested
@bruin"""

import subprocess
import glob
import os
import pandas as pd
from datetime import datetime
from pathlib import Path


def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni"
    parquet_out = f"{base_path}/ooni_measurements.parquet"
    
    Path(base_path).mkdir(parents=True, exist_ok=True)

    # ==================== STEP 1: Precise S3 Sync (only June 2023 – June 2025) ====================
    files_already_present = glob.glob(f"{base_path}/**/*.jsonl.gz", recursive=True)
    
    # Skip sync if we already have a good number of files (makes re-runs fast)
    if len(files_already_present) > 200:
        print(f"✅ Skipping S3 sync — {len(files_already_present)} files already present.")
    else:
        print("🚀 Starting precise S3 sync for Kenya data (June 2023 – June 2025 only)...")
        print("   This should be much faster as it avoids scanning 2020–2022 data.")

        sync_cmd = [
            "aws", "s3", "--no-sign-request", "sync",
            "s3://ooni-data-eu-fra/raw/", base_path,
            "--exclude", "*",
            # Precise monthly includes — only what we need
            "--include", "202306*/KE/*.jsonl.gz",
            "--include", "202307*/KE/*.jsonl.gz",
            "--include", "202308*/KE/*.jsonl.gz",
            "--include", "202309*/KE/*.jsonl.gz",
            "--include", "202310*/KE/*.jsonl.gz",
            "--include", "202311*/KE/*.jsonl.gz",
            "--include", "202312*/KE/*.jsonl.gz",
            "--include", "2024*/KE/*.jsonl.gz",     # all of 2024
            "--include", "202501*/KE/*.jsonl.gz",   # Jan 2025
            "--include", "202502*/KE/*.jsonl.gz",
            "--include", "202503*/KE/*.jsonl.gz",
            "--include", "202504*/KE/*.jsonl.gz",
            "--include", "202505*/KE/*.jsonl.gz",
            "--include", "202506*/KE/*.jsonl.gz"
        ]
        
        try:
            result = subprocess.run(sync_cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print("Sync warnings:", result.stderr)
            print("✅ S3 sync completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"❌ S3 sync failed: {e}")
            if e.stderr:
                print(e.stderr)
            raise

    # ==================== STEP 2: Process files with chunked reading ====================
    print("📂 Discovering downloaded .jsonl.gz files...")
    files = sorted(glob.glob(f"{base_path}/**/*.jsonl.gz", recursive=True))
    print(f"Found {len(files)} JSONL files.")

    if not files:
        raise FileNotFoundError(f"No .jsonl.gz files found in {base_path}")

    start_date = pd.Timestamp("2023-06-01")
    end_date = pd.Timestamp("2025-06-30")

    dfs = []
    total_rows = 0

    for i, file_path in enumerate(files, 1):
        if i % 20 == 0 or i == 1 or i == len(files):
            print(f"Processing {i}/{len(files)}: {os.path.basename(file_path)}")

        try:
            for chunk in pd.read_json(file_path, lines=True, chunksize=100_000, compression="gzip"):
                if "start_time" not in chunk.columns:
                    continue

                chunk["start_time"] = pd.to_datetime(chunk["start_time"], errors="coerce")
                mask = (chunk["start_time"] >= start_date) & (chunk["start_time"] <= end_date)
                filtered = chunk[mask].copy()

                if not filtered.empty:
                    dfs.append(filtered)
                    total_rows += len(filtered)

                # Keep memory under control
                if len(dfs) >= 15:
                    df_temp = pd.concat(dfs, ignore_index=True)
                    dfs = [df_temp]

        except Exception as e:
            print(f"⚠️ Error processing {os.path.basename(file_path)}: {e}")
            continue

    if dfs:
        df = pd.concat(dfs, ignore_index=True)
    else:
        df = pd.DataFrame()

    print(f"✅ Filtered {len(df):,} measurements in the requested date range.")

    # ==================== STEP 3: Finalize ====================
    df["extracted_at"] = datetime.now()

    # Align with your declared columns
    keep_cols = ["measurement_id", "country", "asn", "test_name", "input",
                 "start_time", "probe_cc", "probe_asn"]
    
    for col in ["status"]:
        if col not in df.columns:
            df[col] = pd.NA

    df = df.reindex(columns=keep_cols + ["status", "extracted_at"], fill_value=None)

    df.to_parquet(parquet_out, index=False, compression="snappy")

    print(f"✅ Parquet saved: {len(df):,} rows → {parquet_out}")
    return df
