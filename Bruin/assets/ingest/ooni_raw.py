# =========================================================
# OONI RAW INGEST - CLEAN PRODUCTION VERSION
# =========================================================

import glob
import os
from datetime import datetime
from pathlib import Path

import pandas as pd


# =========================================================
# ENV HANDLING (FIX: removes _env dependency completely)
# =========================================================
def resolve_env() -> str:
    return (
        os.getenv("TARGET_ENV")
        or os.getenv("BRUIN_ENV")
        or os.getenv("BRUIN_ENVIRONMENT")
        or "dev"
    )


def require_dev(env: str):
    if env != "dev":
        print(f"⚠️ Running in {env} mode")


ENV = resolve_env()
require_dev(ENV)


# =========================================================
# PATHS
# =========================================================
BASE_PATH = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni"
DATA_ROOT = os.path.join(BASE_PATH, "ooni-kenya-censorship")
OUT_FILE = os.path.join(BASE_PATH, "ooni_measurements.parquet")

START_TS = pd.Timestamp("2023-06-01")
END_TS = pd.Timestamp("2025-06-30")


# =========================================================
# SIGNAL DERIVATION
# =========================================================
def derive_blocking_fields(row: dict) -> dict:
    test = str(row.get("test_name", "")).lower()
    tk = {k: v for k, v in row.items() if k.startswith("test_keys.")}

    # ---------------- TELEGRAM ----------------
    tg_http = bool(tk.get("test_keys.telegram_http_blocking", False))
    tg_tcp = bool(tk.get("test_keys.telegram_tcp_blocking", False))

    # ---------------- WHATSAPP ----------------
    wa_blocked = bool(tk.get("test_keys.whatsapp_endpoints_blocked", False))
    wa_dns = bool(
        tk.get("test_keys.whatsapp_endpoints_dns_inconsistent", False))
    wa_web = tk.get("test_keys.whatsapp_web_failure")
    wa_reg = tk.get("test_keys.registration_server_failure")

    # ---------------- SIGNAL ----------------
    sig_failure = tk.get("test_keys.signal_backend_failure")

    # ---------------- TOR ----------------
    tor_or = tk.get("test_keys.or_port_accessible")
    tor_obfs4 = tk.get("test_keys.obfs4_accessible")

    # ---------------- PSIPHON ----------------
    psi_failure = tk.get("test_keys.failure")

    is_blocked = False
    is_confirmed_block = False
    has_failure = False
    signal_type = "none"

    # =====================================================
    # TELEGRAM
    # =====================================================
    if test == "telegram":
        is_blocked = tg_http or tg_tcp
        is_confirmed_block = is_blocked
        has_failure = bool(tk.get("test_keys.failure"))
        if is_blocked:
            signal_type = f"telegram_block(http={tg_http},tcp={tg_tcp})"

    # =====================================================
    # WHATSAPP
    # =====================================================
    elif test == "whatsapp":
        is_blocked = wa_blocked
        is_confirmed_block = wa_blocked
        has_failure = any([wa_web, wa_reg, wa_dns])

        if wa_blocked:
            signal_type = "whatsapp_endpoints_blocked"
        elif wa_dns:
            signal_type = "whatsapp_dns_inconsistent"
        elif wa_web:
            signal_type = f"whatsapp_web_failure({wa_web})"
        elif wa_reg:
            signal_type = f"whatsapp_registration_failure({wa_reg})"

    # =====================================================
    # SIGNAL (DISRUPTION ONLY)
    # =====================================================
    elif test == "signal":
        has_failure = sig_failure is not None
        is_blocked = False
        is_confirmed_block = False

        if sig_failure:
            signal_type = f"signal_backend_failure({sig_failure})"

    # =====================================================
    # TOR (REACHABILITY MODEL)
    # =====================================================
    elif test == "tor":
        try:
            or_access = int(tor_or) if tor_or is not None else None
        except Exception:
            or_access = None

        has_failure = True

        if or_access == 0:
            signal_type = "tor_or_unreachable"
        elif tor_obfs4 == 0:
            signal_type = "tor_obfs4_unreachable"
        else:
            signal_type = "tor_partial_reachability"

    # =====================================================
    # PSIPHON
    # =====================================================
    elif test == "psiphon":
        has_failure = psi_failure is not None
        if psi_failure:
            signal_type = f"psiphon_failure({psi_failure})"

    # =====================================================
    # GENERIC
    # =====================================================
    else:
        failure = row.get("failure")
        is_blocked = failure is not None
        has_failure = failure is not None
        if failure:
            signal_type = f"generic_failure({failure})"

    return {
        "telegram_http_blocking": tg_http,
        "telegram_tcp_blocking": tg_tcp,

        "signal_backend_failure": sig_failure,

        "whatsapp_endpoints_blocked": wa_blocked,
        "whatsapp_endpoints_dns_inconsistent": wa_dns,
        "whatsapp_web_failure": wa_web,

        "tor_or_port_accessible": tor_or,
        "tor_obfs4_accessible": tor_obfs4,

        "psiphon_failure": psi_failure,

        "is_blocked": is_blocked,
        "is_confirmed_block": is_confirmed_block,
        "has_measurement_failure": has_failure,
        "blocking_signal_type": signal_type,
    }


# =========================================================
# PROCESSING
# =========================================================
def process_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    if "test_start_time" in chunk.columns and "start_time" not in chunk.columns:
        chunk = chunk.rename(columns={"test_start_time": "start_time"})

    # FIX: safe timestamp handling (prevents INT64 DATE crash later)
    chunk["start_time"] = pd.to_datetime(
        chunk.get("start_time"),
        errors="coerce",
        utc=True,
    ).dt.tz_localize(None)

    chunk = chunk.dropna(subset=["start_time"])

    chunk = chunk[
        (chunk["start_time"] >= START_TS) &
        (chunk["start_time"] <= END_TS)
    ].copy()

    if chunk.empty:
        return chunk

    if "measurement_uid" in chunk.columns:
        chunk["measurement_id"] = chunk["measurement_uid"]
    elif "id" in chunk.columns:
        chunk["measurement_id"] = chunk["id"]

    derived = chunk.apply(
        lambda r: pd.Series(derive_blocking_fields(r.to_dict())),
        axis=1,
    )

    chunk = pd.concat([chunk, derived], axis=1)
    chunk["extracted_at"] = datetime.now()

    return chunk


# =========================================================
# MATERIALIZE
# =========================================================
def materialize():
    Path(BASE_PATH).mkdir(parents=True, exist_ok=True)

    files = sorted(glob.glob(f"{DATA_ROOT}/**/*.jsonl.gz", recursive=True))
    print(f"Found {len(files):,} files")

    dfs = []

    for f in files:
        try:
            for chunk in pd.read_json(
                f,
                lines=True,
                chunksize=80_000,
                compression="gzip",
            ):
                processed = process_chunk(chunk)
                if not processed.empty:
                    dfs.append(processed)

        except Exception as e:
            print(f"Skip {f}: {e}")

    df = pd.concat(dfs, ignore_index=True)

    df.to_parquet(OUT_FILE, index=False, compression="snappy")

    print(f"Saved: {OUT_FILE} ({len(df):,} rows)")
    return df
