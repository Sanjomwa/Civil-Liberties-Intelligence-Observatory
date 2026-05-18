from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


REPO_ROOT = Path(__file__).resolve().parents[2]
BRUIN_CONFIG_PATH = REPO_ROOT / "Bruin" / "config" / "observatory.yml"

load_dotenv(REPO_ROOT / ".env")


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _load_bruin_config() -> dict[str, Any]:
    if yaml is None or not BRUIN_CONFIG_PATH.exists():
        return {}

    with BRUIN_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


_CONFIG = _load_bruin_config()

DEFAULTS = {
    "project_id": "encoded-joy-485413-k5",
    "bucket": "civil-liberties-data",
    "location": "us-central1",
    "environment": "dev",
    "country": "Kenya",
    "iso2": "KE",
    "datasets": {
        "reporting": "reporting",
        "marts": "marts",
        "features": "features",
        "intelligence": "intelligence",
    },
    "dashboard": {
        "default_start": "2023-06-01",
        "default_end": "2025-06-30",
    },
}

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or _CONFIG.get("project_id") or DEFAULTS["project_id"]
GCS_BUCKET = os.getenv("GCS_BUCKET") or _CONFIG.get("bucket") or DEFAULTS["bucket"]
BQ_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION") or _CONFIG.get("location") or DEFAULTS["location"]
TARGET_ENV = os.getenv("TARGET_ENV") or os.getenv("BRUIN_ENV") or _CONFIG.get("environment") or DEFAULTS["environment"]
BRUIN_ENV = os.getenv("BRUIN_ENV") or TARGET_ENV
COUNTRY = os.getenv("COUNTRY") or _CONFIG.get("country") or DEFAULTS["country"]
ISO2 = os.getenv("ISO2") or _CONFIG.get("iso2") or DEFAULTS["iso2"]
DATASETS = _CONFIG.get("datasets", DEFAULTS["datasets"])
DEFAULT_START = _parse_date(
    os.getenv("DEFAULT_START")
    or _CONFIG.get("dashboard", {}).get("default_start")
    or DEFAULTS["dashboard"]["default_start"]
)
DEFAULT_END = _parse_date(
    os.getenv("DEFAULT_END")
    or _CONFIG.get("dashboard", {}).get("default_end")
    or DEFAULTS["dashboard"]["default_end"]
)
