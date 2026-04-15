"""@bruin
tags:
  - raw_dev
  - dataset_ooni
name: raw.ooni_conflict_measurements
type: python
image: python:3.12
connection: duckdb-parquet
description: |
  DEV ONLY.
  Reads raw OONI .jsonl.gz files for Kenya (Jun 2023–Jun 2025).
  Extracts test-specific blocking fields from test_keys.* rather than
  relying on generic anomaly/confirmed/failure flags.

  Normalized output columns added:
    - telegram_http_blocking, telegram_tcp_blocking
    - signal_backend_failure
    - whatsapp_endpoints_blocked, whatsapp_endpoints_dns_inconsistent, whatsapp_web_failure
    - tor_dir_port_accessible, tor_obfs4_accessible, tor_or_port_accessible
    - psiphon_failure
    - is_blocked         (test-specific logic)
    - is_confirmed_block (stricter subset of is_blocked)
    - has_measurement_failure (any network-level error)
    - blocking_signal_type (human-readable source of the block determination)


materialization:
  type: table
  strategy: create+replace
@bruin"""

import glob
import gzip
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from _env import resolve_env, require_dev

ENV = resolve_env(fallback="dev")
require_dev(ENV)

BASE_PATH  = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni"
DATA_ROOT  = os.path.join(BASE_PATH, "ooni-kenya-censorship")
OUT_FILE   = os.path.join(BASE_PATH, "ooni_measurements.parquet")

START_TS = pd.Timestamp("2023-06-01")
END_TS   = pd.Timestamp("2025-06-30")


# ── Test-specific blocking logic ──────────────────────────────────────────────

def derive_blocking_fields(row: dict) -> dict:
    """
    Given a flat dict (after json_normalize or equivalent), derive the
    canonical blocking columns based on the actual test_keys.* structure
    observed in the Kenya OONI dataset.

    Returns a dict of derived columns to merge into the row.
    """
    test = str(row.get("test_name", "")).lower()
    tk   = {k: v for k, v in row.items() if k.startswith("test_keys.")}

    # ── Telegram ─────────────────────────────────────────────────────────────
    tg_http = bool(tk.get("test_keys.telegram_http_blocking", False) or False)
    tg_tcp  = bool(tk.get("test_keys.telegram_tcp_blocking",  False) or False)

    # ── WhatsApp ──────────────────────────────────────────────────────────────
    wa_ep_blocked  = bool(tk.get("test_keys.whatsapp_endpoints_blocked",          False) or False)
    wa_dns_incons  = bool(tk.get("test_keys.whatsapp_endpoints_dns_inconsistent", False) or False)
    wa_web_fail    = tk.get("test_keys.whatsapp_web_failure")  # string or None

    # ── Signal ────────────────────────────────────────────────────────────────
    sig_failure = tk.get("test_keys.signal_backend_failure")   # string or None

    # ── Tor ───────────────────────────────────────────────────────────────────
    tor_dir    = tk.get("test_keys.dir_port_accessible")   # integer count
    tor_obfs4  = tk.get("test_keys.obfs4_accessible")      # integer count
    tor_or     = tk.get("test_keys.or_port_accessible")    # integer count

    # ── Psiphon ───────────────────────────────────────────────────────────────
    psi_failure = tk.get("test_keys.failure")  # string or None (psiphon only uses generic failure)

    # ── Web connectivity (generic OONI fields still valid here) ───────────────
    anomaly   = bool(row.get("anomaly",   False) or False)
    confirmed = bool(row.get("confirmed", False) or False)
    failure   = row.get("failure")   # top-level failure string

    # ── Derive normalized fields ──────────────────────────────────────────────
    is_blocked         = False
    is_confirmed_block = False
    has_failure        = False
    signal_type        = "none"

    if test == "telegram":
        is_blocked         = tg_http or tg_tcp
        is_confirmed_block = is_blocked
        has_failure        = failure is not None
        if is_blocked:
            parts = []
            if tg_http: parts.append("http")
            if tg_tcp:  parts.append("tcp")
            signal_type = f"telegram_blocking({'|'.join(parts)})"

    elif test == "whatsapp":
        is_blocked         = wa_ep_blocked or wa_dns_incons
        is_confirmed_block = wa_ep_blocked          # endpoints_blocked = stronger
        has_failure        = wa_web_fail is not None
        if wa_ep_blocked:
            signal_type = "whatsapp_endpoints_blocked"
        elif wa_dns_incons:
            signal_type = "whatsapp_dns_inconsistent"
        elif wa_web_fail:
            signal_type = f"whatsapp_web_failure({wa_web_fail})"

    elif test == "signal":
        is_blocked         = sig_failure is not None   # disruption counts as blocked
        is_confirmed_block = False                     # never confirmed for signal
        has_failure        = sig_failure is not None
        if sig_failure:
            signal_type = f"signal_backend_failure({sig_failure})"

    elif test == "tor":
        # or_port_accessible = 0 means none of the OR ports worked — disruption
        is_blocked         = (tor_or is not None and int(tor_or) == 0)
        is_confirmed_block = False
        has_failure        = failure is not None
        if is_blocked:
            signal_type = (
                f"tor_disruption(dir={tor_dir},obfs4={tor_obfs4},or={tor_or})"
            )

    elif test == "psiphon":
        is_blocked         = (
            (isinstance(psi_failure, str) and len(psi_failure) > 0)
        )
        is_confirmed_block = False
        has_failure        = is_blocked
        if is_blocked:
            signal_type = f"psiphon_failure({psi_failure})"

    elif test == "web_connectivity":
        is_blocked         = anomaly or confirmed
        is_confirmed_block = confirmed
        has_failure        = failure is not None
        if confirmed:
            signal_type = "web_confirmed"
        elif anomaly:
            signal_type = "web_anomaly"
        elif failure:
            signal_type = f"web_failure({failure})"

    else:
        # Generic fallback for dnscheck, http_requests, etc.
        is_blocked         = failure is not None
        is_confirmed_block = False
        has_failure        = failure is not None
        if failure:
            signal_type = f"generic_failure({failure})"

    return {
        # Test-specific raw flags (preserved for downstream analysis)
        "telegram_http_blocking":              tg_http,
        "telegram_tcp_blocking":               tg_tcp,
        "signal_backend_failure":              sig_failure,
        "whatsapp_endpoints_blocked":          wa_ep_blocked,
        "whatsapp_endpoints_dns_inconsistent": wa_dns_incons,
        "whatsapp_web_failure":                wa_web_fail,
        "tor_dir_port_accessible":             tor_dir,
        "tor_obfs4_accessible":                tor_obfs4,
        "tor_or_port_accessible":              tor_or,
        "psiphon_failure":                     psi_failure,
        # Normalized canonical fields
        "is_blocked":                          is_blocked,
        "is_confirmed_block":                  is_confirmed_block,
        "has_measurement_failure":             has_failure,
        "blocking_signal_type":                signal_type,
    }


# ── Keep columns ──────────────────────────────────────────────────────────────
BASE_COLS = [
    "measurement_uid", "id",
    "test_name", "input",
    "probe_cc", "probe_asn", "asn",
    "test_start_time", "start_time",
    "anomaly", "confirmed", "failure",
    # test_keys we need for derive_blocking_fields
    "test_keys.telegram_http_blocking",
    "test_keys.telegram_tcp_blocking",
    "test_keys.signal_backend_failure",
    "test_keys.whatsapp_endpoints_blocked",
    "test_keys.whatsapp_endpoints_dns_inconsistent",
    "test_keys.whatsapp_web_failure",
    "test_keys.dir_port_accessible",
    "test_keys.obfs4_accessible",
    "test_keys.or_port_accessible",
    "test_keys.failure",
]

OUTPUT_COLS = [
    "measurement_id", "probe_cc", "asn", "probe_asn",
    "test_name", "input", "start_time",
    # raw test-specific flags
    "telegram_http_blocking", "telegram_tcp_blocking",
    "signal_backend_failure",
    "whatsapp_endpoints_blocked", "whatsapp_endpoints_dns_inconsistent", "whatsapp_web_failure",
    "tor_dir_port_accessible", "tor_obfs4_accessible", "tor_or_port_accessible",
    "psiphon_failure",
    # normalized canonical fields
    "is_blocked", "is_confirmed_block", "has_measurement_failure", "blocking_signal_type",
    "extracted_at",
]


def process_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    # Normalise column name for timestamp
    if "test_start_time" in chunk.columns and "start_time" not in chunk.columns:
        chunk = chunk.rename(columns={"test_start_time": "start_time"})

    # Parse timestamps
    if "start_time" in chunk.columns:
        chunk["start_time"] = pd.to_datetime(
            chunk["start_time"].astype(str),
            errors="coerce",
            utc=True,
            format="mixed",
        ).dt.tz_localize(None)
    else:
        return pd.DataFrame()

    # Date filter
    mask = (chunk["start_time"] >= START_TS) & (chunk["start_time"] <= END_TS)
    chunk = chunk[mask].copy()
    if chunk.empty:
        return chunk

    # measurement_id: prefer measurement_uid, fall back to id
    if "measurement_uid" in chunk.columns:
        chunk["measurement_id"] = chunk["measurement_uid"]
    elif "id" in chunk.columns:
        chunk["measurement_id"] = chunk["id"]
    else:
        chunk["measurement_id"] = None

    # asn fallback
    if "probe_asn" not in chunk.columns and "asn" in chunk.columns:
        chunk["probe_asn"] = chunk["asn"]
    if "asn" not in chunk.columns and "probe_asn" in chunk.columns:
        chunk["asn"] = chunk["probe_asn"]

    # Derive blocking fields row-by-row
    derived = chunk.apply(
        lambda row: pd.Series(derive_blocking_fields(row.to_dict())),
        axis=1,
    )
    chunk = pd.concat([chunk, derived], axis=1)

    chunk["extracted_at"] = datetime.now()

    # Return only output columns that exist
    present = [c for c in OUTPUT_COLS if c in chunk.columns]
    return chunk[present]


def materialize():
    Path(BASE_PATH).mkdir(parents=True, exist_ok=True)

    files = sorted(glob.glob(f"{DATA_ROOT}/**/*.jsonl.gz", recursive=True))
    print(f"Found {len(files):,} raw .jsonl.gz files")
    if not files:
        raise FileNotFoundError(f"No OONI files found under {DATA_ROOT}")

    # Quick schema preview from first file
    print("\n── Schema preview from first file ──")
    try:
        with gzip.open(files[0], "rt", encoding="utf-8") as f:
            sample = json.loads(f.readline())
        tk_keys = [k for k in sample.get("test_keys", {}).keys()]
        print(f"test_name: {sample.get('test_name')}")
        print(f"test_keys fields ({len(tk_keys)}): {tk_keys[:20]}")
    except Exception as e:
        print(f"Preview failed: {e}")
    print()

    dfs = []
    total_read = total_kept = 0

    for i, fpath in enumerate(files, 1):
        if i == 1 or i % 50 == 0 or i == len(files):
            print(f"Processing {i:,}/{len(files):,} → {os.path.basename(fpath)}")
        try:
            for chunk in pd.read_json(
                fpath, lines=True, chunksize=80_000, compression="gzip"
            ):
                total_read += len(chunk)
                processed = process_chunk(chunk)
                if not processed.empty:
                    total_kept += len(processed)
                    dfs.append(processed)
        except Exception as e:
            print(f"⚠️  Error in {os.path.basename(fpath)}: {e}")

    if not dfs:
        raise ValueError("No rows passed the date filter — check your data path and date range.")

    df = pd.concat(dfs, ignore_index=True)

    # Summary statistics
    print(f"\n{'='*50}")
    print(f"Total rows read         : {total_read:,}")
    print(f"Rows kept (date filter) : {total_kept:,}")
    print(f"Final output rows       : {len(df):,}")
    print(f"\nBlocking summary by test:")
    if "test_name" in df.columns and "is_blocked" in df.columns:
        summary = (
            df.groupby("test_name")
              .agg(
                  total=("measurement_id", "count"),
                  blocked=("is_blocked", "sum"),
                  confirmed=("is_confirmed_block", "sum"),
              )
              .assign(block_rate=lambda x: (x.blocked / x.total * 100).round(1))
              .sort_values("blocked", ascending=False)
        )
        print(summary.to_string())
    print(f"\nBlocking signal type distribution:")
    if "blocking_signal_type" in df.columns:
        print(df["blocking_signal_type"].value_counts().head(20).to_string())
    print("="*50)

    df.to_parquet(OUT_FILE, index=False, compression="snappy")
    print(f"\n✅ Parquet written: {OUT_FILE} ({len(df):,} rows)")

    return df
