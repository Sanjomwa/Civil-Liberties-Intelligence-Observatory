"""
@bruin
name: raw.ooni_conflict_measurements
type: python
image: python:3.12
connection: duckdb-parquet
description: |
  DEV ONLY.
  Reads raw OONI .jsonl.gz files for Kenya (Jun 2023 - Jun 2025).
  Follows the OONI Data Pipeline design: line-by-line JSON parsing,
  test_keys accessed as a dict (no json_normalize), raw_test_keys
  preserved as JSON string for full reproducibility.

  Produces canonical parquet at data/dev/ooni/ooni_measurements.parquet.

  Blocking fields extracted per test type:
    telegram  - telegram_http_blocking, telegram_tcp_blocking
    whatsapp  - whatsapp_endpoints_blocked, whatsapp_dns_inconsistent,
                whatsapp_web_failure
    signal    - signal_backend_failure
    tor       - tor_or_port_accessible, tor_obfs4_accessible,
                tor_dir_port_accessible
    psiphon   - psiphon_failure

  Full blocking derivation (is_blocked, is_confirmed_block, etc.)
  happens in stg.ooni, not here. Raw layer only extracts + preserves.

tags:
  - raw_dev
  - dataset_ooni

materialization:
  type: table
  strategy: create+replace
@bruin
"""

import gzip
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pandas as pd

# ---------------------------------------------------------------------------
# Allow _env import whether working dir is asset folder or project root
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _env import require_dev, resolve_env

ENV = resolve_env(fallback="dev")
require_dev(ENV)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
ROOT     = Path("data/dev/ooni/ooni-kenya-censorship")
OUT_DIR  = Path("data/dev/ooni")
OUT_FILE = OUT_DIR / "ooni_measurements.parquet"

START_DATE = "2023-06-01"
END_DATE   = "2025-06-30"


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def resolve_time(obj: Dict[str, Any]) -> pd.Timestamp:
    """
    Try multiple timestamp field names in priority order.
    OONI changed the field name across data versions.
    """
    ts = (
        obj.get("measurement_start_time")
        or obj.get("test_start_time")
        or obj.get("started_at")
    )
    return pd.to_datetime(ts, utc=True, errors="coerce")


def safe_bool(x) -> bool:
    """Convert any truthy representation to a Python bool."""
    if x is None:
        return False
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        return x.lower() in ("true", "1", "yes")
    return bool(x)


def extract_row(obj: Dict[str, Any], t: pd.Timestamp) -> Dict[str, Any]:
    """
    Build one output row from a parsed OONI measurement object.

    test_keys is accessed as a plain dict — no json_normalize, no column
    explosion, no field-name clashes from deeply nested tor targets.
    raw_test_keys is stored as a JSON string for full reproducibility so
    we can always re-derive signals without re-reading source files.
    """
    test_keys = obj.get("test_keys") or {}

    row = {
        # ── Identity ────────────────────────────────────────────────────────
        "measurement_id":   obj.get("measurement_uid") or obj.get("id"),
        "country":          obj.get("probe_cc"),
        "asn":              obj.get("asn"),
        "probe_cc":         obj.get("probe_cc"),
        "probe_asn":        obj.get("probe_asn"),
        "test_name":        obj.get("test_name"),
        "input":            obj.get("input"),

        # ── Time ────────────────────────────────────────────────────────────
        "start_time":   t,
        "part":         t.strftime("%Y-%m-%d"),
        "extracted_at": datetime.utcnow(),

        # ── Raw reproducibility (CRITICAL per OONI pipeline design) ─────────
        "raw_test_keys": json.dumps(test_keys, default=str),

        # ── Telegram ────────────────────────────────────────────────────────
        "telegram_http_blocking": safe_bool(
            test_keys.get("telegram_http_blocking")
        ),
        "telegram_tcp_blocking": safe_bool(
            test_keys.get("telegram_tcp_blocking")
        ),

        # ── WhatsApp ────────────────────────────────────────────────────────
        # endpoints_status == "blocked" is the strongest confirmed signal.
        # dns_consistent == False       is the DNS inconsistency signal.
        "whatsapp_endpoints_blocked": (
            test_keys.get("endpoints_status") == "blocked"
        ),
        "whatsapp_dns_inconsistent": (
            test_keys.get("dns_consistent") is False
        ),
        "whatsapp_web_failure": test_keys.get("web_failure"),

        # ── Signal ──────────────────────────────────────────────────────────
        "signal_backend_failure": test_keys.get("signal_backend_failure"),

        # ── Tor ─────────────────────────────────────────────────────────────
        # Integer counts: 0 means no reachable nodes of that type.
        # We do NOT flatten the per-target failure dict — too many dynamic
        # keys. Raw string preserved in raw_test_keys if needed.
        "tor_or_port_accessible":  test_keys.get("or_port_accessible"),
        "tor_obfs4_accessible":    test_keys.get("obfs4_accessible"),
        "tor_dir_port_accessible": test_keys.get("dir_port_accessible"),

        # ── Psiphon ─────────────────────────────────────────────────────────
        # Only the generic top-level failure field is available.
        "psiphon_failure": test_keys.get("failure"),

        # ── Minimal derived metadata (safe at raw layer) ─────────────────
        # Full blocking derivation (is_blocked etc.) belongs in stg.ooni.
        # We only note whether any top-level failure field was present.
        "has_failure": obj.get("failure") is not None,
    }

    # Deterministic row hash for dedup debugging.
    # Excludes extracted_at so reruns produce the same hash for the same
    # source measurement.
    hashable = {
        k: v for k, v in row.items()
        if k not in ("extracted_at", "row_hash")
    }
    row["row_hash"] = hash(
        json.dumps(hashable, sort_keys=True, default=str)
    )

    return row


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def materialize() -> pd.DataFrame:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    start = pd.to_datetime(START_DATE, utc=True)
    end   = pd.to_datetime(END_DATE,   utc=True)

    if not ROOT.exists():
        raise FileNotFoundError(
            f"OONI data root not found: {ROOT.resolve()}\n"
            "Download Kenya OONI data and place under:\n"
            "  data/dev/ooni/ooni-kenya-censorship/"
        )

    files = sorted(ROOT.rglob("*.jsonl.gz"))
    print(f"Found {len(files):,} .jsonl.gz files under {ROOT.resolve()}")
    if not files:
        raise FileNotFoundError(f"No .jsonl.gz files found under {ROOT}")

    rows          = []
    total_lines   = 0
    skipped_parse = 0
    skipped_date  = 0
    skipped_cc    = 0

    for i, f in enumerate(files, 1):
        if i == 1 or i % 100 == 0 or i == len(files):
            print(
                f"  [{i:,}/{len(files):,}] {f.name}"
                f"  (kept so far: {len(rows):,})"
            )

        try:
            with gzip.open(f, "rt", encoding="utf-8") as fh:
                for line in fh:
                    total_lines += 1
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        skipped_parse += 1
                        continue

                    t = resolve_time(obj)
                    if pd.isna(t) or t < start or t > end:
                        skipped_date += 1
                        continue

                    if obj.get("probe_cc") != "KE":
                        skipped_cc += 1
                        continue

                    rows.append(extract_row(obj, t))

        except Exception as e:
            print(f"  ⚠️  Error reading {f.name}: {e}")
            continue

    # ── Summary ─────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Total lines read         : {total_lines:,}")
    print(f"Skipped (parse error)    : {skipped_parse:,}")
    print(f"Skipped (out of date range): {skipped_date:,}")
    print(f"Skipped (non-KE)         : {skipped_cc:,}")
    print(f"Rows kept                : {len(rows):,}")

    if not rows:
        raise ValueError(
            "No rows passed the date + country filter.\n"
            f"  Date range : {START_DATE} -> {END_DATE}\n"
            f"  Country    : KE\n"
            "Verify your source files are in the correct directory."
        )

    df = (
        pd.DataFrame(rows)
          .sort_values("start_time")
          .reset_index(drop=True)
    )

    # ── Per-test signal summary ──────────────────────────────────────────────
    print(f"\nRows by test_name:")
    print(df["test_name"].value_counts().to_string())

    print(f"\nSignal counts:")
    tg_blocked = (df["telegram_http_blocking"] | df["telegram_tcp_blocking"])
    print(f"  Telegram any blocking     : {tg_blocked.sum():,}")
    print(f"  WhatsApp endpoints blocked: {df['whatsapp_endpoints_blocked'].sum():,}")
    print(f"  WhatsApp DNS inconsistent : {df['whatsapp_dns_inconsistent'].sum():,}")
    print(f"  Signal backend failures   : {df['signal_backend_failure'].notna().sum():,}")

    tor_mask = df["tor_or_port_accessible"].notna()
    if tor_mask.any():
        tor_blocked = (df.loc[tor_mask, "tor_or_port_accessible"] == 0).sum()
        print(f"  Tor OR port unreachable   : {tor_blocked:,}")

    print(f"  Psiphon failures          : {df['psiphon_failure'].notna().sum():,}")
    print("="*60)

    df.to_parquet(OUT_FILE, index=False, compression="snappy")
    print(f"\n✅ Written: {OUT_FILE.resolve()}  ({len(df):,} rows)")

    return df
