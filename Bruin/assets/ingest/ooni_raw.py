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


def first_existing_column(df: pd.DataFrame, candidates: list[str]):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def coerce_bool_series(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    col = first_existing_column(df, candidates)
    if col is None:
        return pd.Series(False, index=df.index, dtype="bool")

    series = df[col]

    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes", "y"])
    )


def any_true_or_nonempty(df: pd.DataFrame, include_tokens: list[str]) -> pd.Series:
    cols = [
        c for c in df.columns
        if all(token in c.lower() for token in include_tokens)
    ]
    if not cols:
        return pd.Series(False, index=df.index, dtype="bool")

    out = pd.Series(False, index=df.index, dtype="bool")
    for col in cols:
        series = df[col]
        if pd.api.types.is_bool_dtype(series):
            out = out | series.fillna(False)
        else:
            values = series.astype(str).str.strip().str.lower()
            out = out | values.isin(["true", "1", "yes", "y"]) | (
                values.notna()
                & (values != "")
                & (values != "none")
                & (values != "nan")
                & (values != "null")
            )
    return out


def print_test_debug(chunk: pd.DataFrame, test_name: str) -> None:
    test_df = chunk[chunk["test_name"] == test_name].copy()
    if test_df.empty:
        return

    interesting_cols = sorted(
        c for c in test_df.columns
        if c.startswith("test_keys.") and any(
            token in c.lower()
            for token in [
                "failure",
                "blocked",
                "blocking",
                "anomaly",
                "confirm",
                "accessible",
                "success",
                "match",
                "consistent",
                "reachable",
            ]
        )
    )

    core_cols = [
        c for c in [
            "measurement_uid",
            "id",
            "test_name",
            "input",
            "probe_cc",
            "probe_asn",
            "start_time",
        ]
        if c in test_df.columns
    ]

    sample_cols = core_cols + interesting_cols[:60]
    sample_cols = [c for c in sample_cols if c in test_df.columns]

    print(f"\n=== TEST DEBUG: {test_name} ===")
    print(f"Rows in inspected chunk for {test_name}: {len(test_df)}")
    print(
        f"Interesting columns ({len(interesting_cols)}): {interesting_cols[:120]}")
    print("Sample row:")
    print(test_df[sample_cols].head(1).to_dict(orient="records"))

    non_null_cols = []
    sample_row = test_df.head(1)
    if not sample_row.empty:
        row_dict = sample_row.iloc[0].to_dict()
        for col in interesting_cols:
            val = row_dict.get(col)
            if pd.notna(val):
                non_null_cols.append((col, val))
    print(f"Non-null interesting fields in sample row: {non_null_cols[:40]}")


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

    debug_only = os.getenv("OONI_DEBUG_ONLY", "0").strip() == "1"
    debug_tests = [
        "web_connectivity",
        "dnscheck",
        "whatsapp",
        "telegram",
        "signal",
        "facebook_messenger",
        "tor",
        "psiphon",
    ]
    seen_tests = set()

    start_ts = pd.Timestamp("2023-06-01")
    end_ts = pd.Timestamp("2025-06-30 23:59:59")

    dfs = []

    for fpath in files:
        print(f"Reading file: {fpath}")
        for chunk in pd.read_json(fpath, lines=True, chunksize=80_000, compression="gzip"):
            chunk = pd.json_normalize(chunk.to_dict(orient="records"), sep=".")

            if "test_start_time" in chunk.columns and "start_time" not in chunk.columns:
                chunk = chunk.rename(columns={"test_start_time": "start_time"})

            if "start_time" not in chunk.columns or "test_name" not in chunk.columns:
                continue

            if debug_only:
                for test_name in debug_tests:
                    if test_name not in seen_tests and (chunk["test_name"] == test_name).any():
                        print_test_debug(chunk, test_name)
                        seen_tests.add(test_name)

                if seen_tests == set(debug_tests):
                    raise SystemExit(
                        "Debug-only run complete after inspecting target test families.")

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

            measurement_id_col = first_existing_column(
                filtered, ["measurement_uid", "id"])
            filtered["measurement_id"] = (
                filtered[measurement_id_col] if measurement_id_col else None
            )

            if "probe_asn" not in filtered.columns and "asn" in filtered.columns:
                filtered["probe_asn"] = filtered["asn"]

            filtered["anomaly"] = (
                coerce_bool_series(
                    filtered, ["anomaly", "test_keys.anomaly", "scores.anomaly"])
                | any_true_or_nonempty(filtered, ["blocked"])
                | any_true_or_nonempty(filtered, ["blocking"])
            )

            filtered["confirmed"] = coerce_bool_series(
                filtered,
                ["confirmed", "test_keys.confirmed", "scores.confirmed"],
            )

            filtered["failure"] = (
                coerce_bool_series(
                    filtered,
                    [
                        "failure",
                        "test_keys.failure",
                        "test_keys.control_failure",
                        "test_keys.experiment_failure",
                        "scores.failure",
                    ],
                )
                | any_true_or_nonempty(filtered, ["failure"])
            )

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

    if debug_only:
        missing = [t for t in debug_tests if t not in seen_tests]
        raise SystemExit(
            f"Debug-only run finished. Tests inspected: {sorted(seen_tests)}. Missing: {missing}"
        )

    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(
        columns=[
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
    )

    print("Final status distribution:")
    if not df.empty:
        print(df["status"].value_counts(dropna=False).to_dict())
        print(
            {
                "anomaly_true": int(df["anomaly"].fillna(False).sum()),
                "confirmed_true": int(df["confirmed"].fillna(False).sum()),
                "failure_true": int(df["failure"].fillna(False).sum()),
            }
        )

    df["extracted_at"] = datetime.now()
    df = df.reindex(
        columns=[
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
        ]
    )

    parquet_out = f"{base_path}/ooni_measurements.parquet"
    df.to_parquet(parquet_out, index=False, compression="snappy")
    return df
