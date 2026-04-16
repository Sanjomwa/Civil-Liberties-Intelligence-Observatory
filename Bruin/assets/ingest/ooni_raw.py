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

materialization:
  type: table
  strategy: create+replace
@bruin"""

# pyright: reportMissingImports=false

import glob
import gzip
import json
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

# --- PATCH: Pylance-safe _env import ---
if TYPE_CHECKING:
    from _env import resolve_env, require_dev
else:
    try:
        from _env import resolve_env, require_dev
    except ImportError:
        def resolve_env(fallback: str = "dev") -> str:
            return fallback

        def require_dev(env: str) -> None:
            if env != "dev":
                print(f"⚠️ Running in non-dev env: {env}")
# --- END PATCH ---

ENV = resolve_env(fallback="dev")
require_dev(ENV)

BASE_PATH = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni"
DATA_ROOT = os.path.join(BASE_PATH, "ooni-kenya-censorship")
OUT_FILE = os.path.join(BASE_PATH, "ooni_measurements.parquet")

START_TS = pd.Timestamp("2023-06-01")
END_TS = pd.Timestamp("2025-06-30")


def derive_blocking_fields(row: dict) -> dict:
    test = str(row.get("test_name", "")).lower()
    tk = {k: v for k, v in row.items() if k.startswith("test_keys.")}

    tg_http = bool(tk.get("test_keys.telegram_http_blocking", False) or False)
    tg_tcp = bool(tk.get("test_keys.telegram_tcp_blocking", False) or False)

    wa_ep_blocked = bool(
        tk.get("test_keys.whatsapp_endpoints_blocked", False) or False)
    wa_dns_incons = bool(
        tk.get("test_keys.whatsapp_endpoints_dns_inconsistent", False) or False)
    wa_web_fail = tk.get("test_keys.whatsapp_web_failure")

    sig_failure = tk.get("test_keys.signal_backend_failure")

    tor_dir = tk.get("test_keys.dir_port_accessible")
    tor_obfs4 = tk.get("test_keys.obfs4_accessible")
    tor_or = tk.get("test_keys.or_port_accessible")

    psi_failure = tk.get("test_keys.failure")

    anomaly = bool(row.get("anomaly", False) or False)
    confirmed = bool(row.get("confirmed", False) or False)
    failure = row.get("failure")

    is_blocked = False
    is_confirmed_block = False
    has_failure = False
    signal_type = "none"

    if test == "telegram":
        is_blocked = tg_http or tg_tcp
        is_confirmed_block = is_blocked
        has_failure = failure is not None
        if is_blocked:
            parts = []
            if tg_http:
                parts.append("http")
            if tg_tcp:
                parts.append("tcp")
            signal_type = f"telegram_blocking({'|'.join(parts)})"

    elif test == "whatsapp":
        is_blocked = wa_ep_blocked or wa_dns_incons
        is_confirmed_block = wa_ep_blocked
        has_failure = wa_web_fail is not None
        if wa_ep_blocked:
            signal_type = "whatsapp_endpoints_blocked"
        elif wa_dns_incons:
            signal_type = "whatsapp_dns_inconsistent"
        elif wa_web_fail:
            signal_type = f"whatsapp_web_failure({wa_web_fail})"

    elif test == "signal":
        is_blocked = sig_failure is not None
        is_confirmed_block = False
        has_failure = sig_failure is not None
        if sig_failure:
            signal_type = f"signal_backend_failure({sig_failure})"

    elif test == "tor":
        is_blocked = (tor_or is not None and int(tor_or) == 0)
        is_confirmed_block = False
        has_failure = failure is not None
        if is_blocked:
            signal_type = f"tor_disruption(dir={tor_dir},obfs4={tor_obfs4},or={tor_or})"

    elif test == "psiphon":
        is_blocked = isinstance(psi_failure, str) and len(psi_failure) > 0
        is_confirmed_block = False
        has_failure = is_blocked
        if is_blocked:
            signal_type = f"psiphon_failure({psi_failure})"

    elif test == "web_connectivity":
        is_blocked = anomaly or confirmed
        is_confirmed_block = confirmed
        has_failure = failure is not None
        if confirmed:
            signal_type = "web_confirmed"
        elif anomaly:
            signal_type = "web_anomaly"
        elif failure:
            signal_type = f"web_failure({failure})"

    else:
        is_blocked = failure is not None
        is_confirmed_block = False
        has_failure = failure is not None
        if failure:
            signal_type = f"generic_failure({failure})"

    return {
        "telegram_http_blocking": tg_http,
        "telegram_tcp_blocking": tg_tcp,
        "signal_backend_failure": sig_failure,
        "whatsapp_endpoints_blocked": wa_ep_blocked,
        "whatsapp_endpoints_dns_inconsistent": wa_dns_incons,
        "whatsapp_web_failure": wa_web_fail,
        "tor_dir_port_accessible": tor_dir,
        "tor_obfs4_accessible": tor_obfs4,
        "tor_or_port_accessible": tor_or,
        "psiphon_failure": psi_failure,
        "is_blocked": is_blocked,
        "is_confirmed_block": is_confirmed_block,
        "has_measurement_failure": has_failure,
        "blocking_signal_type": signal_type,
    }


OUTPUT_COLS = [
    "measurement_id", "probe_cc", "asn", "probe_asn",
    "test_name", "input", "start_time",
    "telegram_http_blocking", "telegram_tcp_blocking",
    "signal_backend_failure",
    "whatsapp_endpoints_blocked", "whatsapp_endpoints_dns_inconsistent", "whatsapp_web_failure",
    "tor_dir_port_accessible", "tor_obfs4_accessible", "tor_or_port_accessible",
    "psiphon_failure",
    "is_blocked", "is_confirmed_block", "has_measurement_failure", "blocking_signal_type",
    "extracted_at",
]


def process_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    if "test_start_time" in chunk.columns and "start_time" not in chunk.columns:
        chunk = chunk.rename(columns={"test_start_time": "start_time"})

    if "start_time" not in chunk.columns:
        return pd.DataFrame()

    chunk["start_time"] = pd.to_datetime(
        chunk["start_time"].astype(str),
        errors="coerce",
        utc=True,
        format="mixed",
    ).dt.tz_localize(None)

    chunk = chunk[(chunk["start_time"] >= START_TS)
                  & (chunk["start_time"] <= END_TS)]
    if chunk.empty:
        return chunk

    chunk["measurement_id"] = chunk.get("measurement_uid", chunk.get("id"))

    if "probe_asn" not in chunk and "asn" in chunk:
        chunk["probe_asn"] = chunk["asn"]
    if "asn" not in chunk and "probe_asn" in chunk:
        chunk["asn"] = chunk["probe_asn"]

    derived = chunk.apply(lambda r: pd.Series(
        derive_blocking_fields(r.to_dict())), axis=1)
    chunk = pd.concat([chunk, derived], axis=1)

    chunk["extracted_at"] = datetime.now()

    return chunk[[c for c in OUTPUT_COLS if c in chunk.columns]]


def materialize():
    Path(BASE_PATH).mkdir(parents=True, exist_ok=True)

    files = sorted(glob.glob(f"{DATA_ROOT}/**/*.jsonl.gz", recursive=True))
    if not files:
        raise FileNotFoundError(f"No OONI files found under {DATA_ROOT}")

    dfs = []

    for fpath in files:
        try:
            for chunk in pd.read_json(fpath, lines=True, chunksize=80_000, compression="gzip"):
                processed = process_chunk(chunk)
                if not processed.empty:
                    dfs.append(processed)
        except Exception as e:
            print(f"⚠️ Error in {os.path.basename(fpath)}: {e}")

    if not dfs:
        raise ValueError("No rows passed the date filter.")

    df = pd.concat(dfs, ignore_index=True)
    df.to_parquet(OUT_FILE, index=False, compression="snappy")

    print(f"✅ Parquet written: {OUT_FILE} ({len(df):,} rows)")
    return df
