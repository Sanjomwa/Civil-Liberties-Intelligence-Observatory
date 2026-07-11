# components/trust.py

import pandas as pd
import streamlit as st


def render_trust_strip(
    reporting_version=None,
    feature_version=None,
    intelligence_version=None,
    snapshot_at=None,
    max_date=None
):

    with st.container():

        st.caption(
            f"""
Reporting: {reporting_version or "—"} |
Features: {feature_version or "—"} |
Intelligence: {intelligence_version or "—"} |
Snapshot: {snapshot_at or "—"} |
Data through: {max_date or "—"}
"""
        )


def insufficient_history_notice():

    st.warning(
        "Insufficient historical baseline for statistical reliability."
    )


def zero_variance_notice():

    st.info(
        "Signal variance too low for correlation inference."
    )


def synthetic_data_notice(sources):
    """
    TD-01: sources is a list of source names (e.g. ["Lumen"]) currently
    contributing synthetic/fabricated data to what's displayed. Callers
    gate this on a real per-row/per-date flag from the dataframe, not a
    hardcoded True -- it stops firing on its own once real data replaces
    the fabricated set.
    """

    if not sources:
        return

    joined = ", ".join(sources)

    st.warning(
        f"Contains fabricated data: {joined} figures on this page are "
        "synthetic (generated for development, not sourced from a real "
        "export) and should not be cited as evidence."
    )


# ============================================================
# TD-63: SOURCE ATTRIBUTION
# ============================================================
# Separate from synthetic_data_notice above: that discloses data
# *authenticity* (is this real or fabricated), this discloses source
# *provenance and license terms* (whose data this is, under what terms).
# Neither should be merged into the other.

ATTRIBUTION_SOURCES = {
    "ACLED": {
        "name": "ACLED (Armed Conflict Location & Event Data Project)",
        "url": "https://acleddata.com",
    },
    "OONI": {
        "name": "OONI (Open Observatory of Network Interference)",
        "url": "https://ooni.org",
        "license_name": "CC BY-NC-SA 4.0",
        "license_url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    },
}


def _format_access_date(value):
    if value is None:
        return None

    ts = pd.Timestamp(value)

    if pd.isna(ts):
        return None

    return ts.strftime("%Y-%m-%d")


def attribution_footer(sources, snapshot_at=None):
    """
    TD-63 / ADR-0007: renders source attribution for ACLED- and/or
    OONI-derived data shown on this page, satisfying ACLED's Attribution
    Policy (source name, link, access date) and OONI's CC BY-NC-SA 4.0
    Section 3(a) (attribution to the licensor, license name + link,
    indication of changes made to the licensed material -- CLIO's
    aggregation/classification is that indication).

    `sources` is a list that may contain "ACLED" and/or "OONI"; any other
    value is ignored (e.g. Google Transparency Report attribution is a
    separate, not-yet-resolved question -- TD-64 -- and deliberately not
    claimed here). `snapshot_at` should be the same per-page freshness
    value already passed to render_trust_strip, so the access date is
    real, not invented.
    """

    known = [s for s in sources if s in ATTRIBUTION_SOURCES]

    if not known:
        return

    # Real <a> tags, not markdown [text](url) syntax: this renders inside
    # a raw HTML wrapper div (for the .clio-attribution styling), and
    # Streamlit does not run markdown-link parsing on text already inside
    # an unsafe_allow_html block -- markdown syntax there would render as
    # literal, unparsed text instead of a link.
    parts = []

    for key in known:
        src = ATTRIBUTION_SOURCES[key]
        piece = f'<a href="{src["url"]}" target="_blank">{src["name"]}</a>'

        if "license_name" in src:
            piece += (
                f', licensed <a href="{src["license_url"]}" target="_blank">'
                f'{src["license_name"]}</a>'
            )

        parts.append(piece)

    segments = ["<b>Data attribution:</b> " + " · ".join(parts)]

    access_date = _format_access_date(snapshot_at)

    if access_date:
        segments.append(f"Data refreshed: {access_date}")

    segments.append(
        "CLIO aggregates and classifies this data into attributed, "
        "confidence-qualified findings — it does not redistribute the "
        "underlying source datasets."
    )

    with st.container():
        st.markdown(
            f'<div class="clio-attribution">{" | ".join(segments)}</div>',
            unsafe_allow_html=True,
        )
