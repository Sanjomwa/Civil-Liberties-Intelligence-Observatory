#!/usr/bin/env python3
"""
Validate CLIO's TLS extraction/classification against OONI's own live API.

Written 2026-08-01 (fifth session) to close a gap flagged by a Fable critique
pass: sessions 3 (TD-72, handshake_success) and 4 (TD-71, TLS confidence
tiering) were both verified internally against CLIO's own BigQuery tables,
never against OONI's own independent record. This script re-parses raw OONI
measurement JSON for sampled rows and checks CLIO's stored extraction against
it directly, at the same layer both of today's earlier bugs lived in.

Doubles as an early prototype of the OONI-comparison collector discussed
earlier today -- kept reasonably clean, not thrown away after this run.

Join key: report_id (CLIO's raw table has no measurement_uid -- confirmed
earlier today). Position within a report's tls_handshakes[] array is CLIO's
own tls_offset column (the literal UNNEST ... WITH OFFSET index used at
extraction time in stg.ooni_tls_observations.sql) -- exact positional
matching, not fuzzy IP/port matching (which turned out to be unusable: see
the ip_address/port finding in this run's report -- both columns are 100%
NULL for every row in stg.ooni_tls_observations, an extraction bug unrelated
to today's scope, discovered as a byproduct of building this script).

Usage:
    python3 ooni_api_validation.py meta <report_id>
    python3 ooni_api_validation.py full <report_id>

Designed to be imported and driven from a orchestration script/notebook
rather than run standalone per-row; see the driver logic used for this
session's own four strata (not included here to keep this file a reusable
library, not a one-off batch script).
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

CACHE_DIR = os.environ.get("OONI_API_CACHE_DIR", os.path.expanduser("~/.cache/clio_ooni_validation"))
os.makedirs(CACHE_DIR, exist_ok=True)

BASE_URL = "https://api.ooni.org/api/v1/measurement_meta"
USER_AGENT = "CLIO-validation/1.0 (+https://github.com/Sanjomwa/Civil-Liberties-Intelligence-Observatory)"

_last_request_time = [0.0]
MIN_INTERVAL_SECONDS = 1.05  # ~1 req/sec, with a small safety margin


def _cache_path(report_id, full):
    safe = report_id.replace("/", "_")
    suffix = "full" if full else "meta"
    return os.path.join(CACHE_DIR, f"{safe}.{suffix}.json")


def _rate_limit():
    elapsed = time.monotonic() - _last_request_time[0]
    if elapsed < MIN_INTERVAL_SECONDS:
        time.sleep(MIN_INTERVAL_SECONDS - elapsed)
    _last_request_time[0] = time.monotonic()


def fetch_measurement_meta(report_id, full=False, max_retries=3):
    """Fetch (and disk-cache) OONI's measurement_meta for a report_id.

    Returns a dict with keys: ok (bool), status (int or None), data (dict or
    None), error (str or None). Never raises -- callers check `ok`.
    """
    cache_path = _cache_path(report_id, full)
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return json.load(f)

    url = f"{BASE_URL}?report_id={urllib.parse.quote(report_id)}"
    if full:
        url += "&full=true"

    result = {"ok": False, "status": None, "data": None, "error": None}
    for attempt in range(max_retries):
        _rate_limit()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.load(resp)
                result = {"ok": True, "status": resp.status, "data": data, "error": None}
                break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            result = {"ok": False, "status": e.code, "data": None, "error": str(e)}
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            result = {"ok": False, "status": None, "data": None, "error": str(e)}
            break

    with open(cache_path, "w") as f:
        json.dump(result, f)
    return result


def get_tls_handshake_at_offset(report_id, tls_offset):
    """Fetch full raw JSON for report_id and return the tls_handshakes[]
    entry at the given offset, or an error dict if unavailable."""
    result = fetch_measurement_meta(report_id, full=True)
    if not result["ok"]:
        return {"ok": False, "error": f"fetch failed: {result['error']}"}
    raw_measurement = result["data"].get("raw_measurement")
    if raw_measurement is None:
        return {"ok": False, "error": "no raw_measurement in response"}
    try:
        parsed = json.loads(raw_measurement) if isinstance(raw_measurement, str) else raw_measurement
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"raw_measurement not valid JSON: {e}"}
    handshakes = (parsed.get("test_keys") or {}).get("tls_handshakes")
    if handshakes is None:
        return {"ok": False, "error": "no test_keys.tls_handshakes in raw measurement"}
    tls_offset = int(tls_offset)
    if tls_offset >= len(handshakes):
        return {"ok": False, "error": f"tls_offset {tls_offset} out of range (array len {len(handshakes)})"}
    return {"ok": True, "handshake": handshakes[tls_offset], "array_len": len(handshakes)}
