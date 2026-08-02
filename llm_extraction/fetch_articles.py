"""
fetch_articles.py — OTF-04 LLM extraction prototype

Reproducibility helper: for any article in source_articles_manifest.json
that isn't already present in source_articles_cache/ (gitignored, never
committed — see .gitignore for why), fetch its real body text from the
manifest's `url` and write it into the cache in the same ===BODY===-
delimited format the two seed articles already use.

This does NOT re-fetch articles already present in the cache -- the two
articles this prototype ships with were fetched and transcribed once
(2026-08-02) and are treated as a fixed, offline-testable fixture. This
script exists so a future contributor without that cache can reproduce it,
not so every run silently re-hits the network.

After fetching, the body text's SHA-256 is checked against the manifest's
recorded sha256_body. A mismatch does NOT auto-overwrite -- these are live
news pages that could be edited or taken down after 2026-08-02, and a
silent overwrite would corrupt the fixture the grounding-check tests
depend on. It prints a loud warning and leaves the fetched copy under a
`.mismatch` suffix for manual review instead.

Hashing convention (must match tests/test_grounding_check.py's _load() and
extract_openai.py's source-text loading exactly): the SHA-256 is computed
over `raw_file_text.split("===BODY===", 1)[1].strip()` -- the body only,
not the header block, whitespace-stripped at both ends.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys

MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "source_articles_manifest.json")
CACHE_DIR = os.path.join(os.path.dirname(__file__), "source_articles_cache")


def _hash_body(body_text: str) -> str:
    return hashlib.sha256(body_text.strip().encode("utf-8")).hexdigest()


def _html_to_text(html: str) -> str:
    """Minimal, dependency-light HTML-to-text fallback. Real extraction
    quality depends on the target site's markup; this is a best-effort
    fetch path, not a scraping framework -- the shipped cache is the
    reliable path, this is the reproducibility fallback."""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    import html as html_module

    text = html_module.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_and_cache(entry: dict) -> None:
    import requests

    article_id = entry["article_id"]
    cache_path = os.path.join(CACHE_DIR, f"{article_id}.txt")

    if os.path.exists(cache_path):
        print(f"[skip] {article_id} already cached at {cache_path}")
        return

    print(f"[fetch] {article_id} <- {entry['url']}")
    resp = requests.get(entry["url"], timeout=30, headers={"User-Agent": "Mozilla/5.0 (CLIO OTF-04 research fetch)"})
    resp.raise_for_status()
    body_text = _html_to_text(resp.text)

    actual_hash = _hash_body(body_text)
    expected_hash = entry.get("sha256_body")

    os.makedirs(CACHE_DIR, exist_ok=True)

    header = (
        f"SOURCE: {entry['outlet']}\n"
        f"URL: {entry['url']}\n"
        f"TITLE: {entry['title']}\n"
        f"PUBLISHED: {entry['published']}\n\n"
        f"===BODY===\n\n"
    )

    if expected_hash and actual_hash != expected_hash:
        mismatch_path = cache_path + ".mismatch"
        with open(mismatch_path, "w", encoding="utf-8") as f:
            f.write(header + body_text + "\n")
        print(
            f"[WARNING] {article_id}: fetched body SHA-256 ({actual_hash}) does not "
            f"match manifest ({expected_hash}). The live page may have changed since "
            f"{entry.get('fetched_utc', 'the manifest date')}. NOT overwriting the "
            f"trusted cache -- wrote the fetched copy to {mismatch_path} for manual review."
        )
        return

    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(header + body_text + "\n")
    print(f"[ok] {article_id} cached, hash verified ({actual_hash[:12]}...)")


def ensure_all_cached() -> None:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    missing = [
        entry for entry in manifest
        if not os.path.exists(os.path.join(CACHE_DIR, f"{entry['article_id']}.txt"))
    ]
    if not missing:
        print(f"All {len(manifest)} manifest articles already cached in {CACHE_DIR}.")
        return

    for entry in missing:
        fetch_and_cache(entry)


if __name__ == "__main__":
    try:
        ensure_all_cached()
    except Exception as exc:
        print(f"[fatal] fetch_articles.py failed: {exc}", file=sys.stderr)
        sys.exit(1)
