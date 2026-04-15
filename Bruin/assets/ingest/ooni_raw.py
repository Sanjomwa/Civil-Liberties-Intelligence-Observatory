"""@bruin
tags:
  - raw_dev
  - dataset_ooni_conflict_measurements
name: raw.ooni_conflict_measurements
type: python
image: python:3.12
connection: duckdb-parquet
description: Dev-only ingest. Produces canonical parquet used by load assets.

materialization:
  type: table
  strategy: create+replace
@bruin"""

import glob
import os
from datetime import datetime
from pathlib import Path

import pandas as pd


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


def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni"
    data_root = os.path.join(base_path, "ooni-kenya-censorship")
    Path(base_path).mkdir(parents=True, exist_ok=True)
    Path(data_root).mkdir(parents=True, exist_ok=True)

    files = sorted(glob.glob(f"{data_root}/**/*.jsonl.gz", recursive=True))
    if not files:
        raise FileNotFoundError(f"No files found under {data_root}")

    start_ts = pd.Timestamp("2023-06-01")
    end_ts = pd.Timestamp("2025-06-30 23:59:59")

    dfs = []
    for fpath in files:
        for chunk in pd.read_json(fpath, lines=True, chunksize=80_000, compression="gzip"):
            if "test_start_time" in chunk.columns:
                chunk = chunk.rename(columns={"test_start_time": "start_time"})
            if "start_time" not in chunk.columns:
                continue

            chunk["start_time"] = pd.to_datetime(
                chunk["start_time"].astype(str),
                errors="coerce",
                utc=True,
                format="mixed",
            ).dt.tz_localize(None)

            filtered = chunk[
                (chunk["start_time"] >= start_ts) & (
                    chunk["start_time"] <= end_ts)
            ].copy()
            if filtered.empty:
                continue

            filtered["measurement_id"] = filtered.get(
                "measurement_uid", filtered.get("id"))

            if "probe_asn" not in filtered.columns and "asn" in filtered.columns:
                filtered["probe_asn"] = filtered["asn"]

            # Preserve original OONI signal fields instead of collapsing them away.
            for col in ["anomaly", "confirmed", "failure"]:
                if col not in filtered.columns:
                    filtered[col] = False
                filtered[col] = filtered[col].fillna(False).astype(bool)

            filtered["status"] = "ok"
            filtered.loc[filtered["anomaly"], "status"] = "anomaly"
            filtered.loc[filtered["confirmed"], "status"] = "confirmed"
            filtered.loc[filtered["failure"], "status"] = "failure"

            keep = [
                "measurement_id",
                "country",
                "asn",
                "test_name",
                "input",
                "start_time",
                "probe_cc",
                "probe_asn",
                "status",
                "anomaly",
                "confirmed",
                "failure",
            ]

            for c in keep:
                if c not in filtered.columns:
                    filtered[c] = None

            dfs.append(filtered[keep].copy())

    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(columns=[
        "measurement_id",
        "country",
        "asn",
        "test_name",
        "input",
        "start_time",
        "probe_cc",
        "probe_asn",
        "status",
        "anomaly",
        "confirmed",
        "failure",
    ])

    df["extracted_at"] = datetime.now()
    df = df.reindex(columns=[
        "measurement_id",
        "country",
        "asn",
        "test_name",
        "input",
        "start_time",
        "status",
        "anomaly",
        "confirmed",
        "failure",
        "probe_cc",
        "probe_asn",
        "extracted_at",
    ])

    parquet_out = f"{base_path}/ooni_measurements.parquet"
    df.to_parquet(parquet_out, index=False, compression="snappy")
    return df
