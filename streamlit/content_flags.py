# streamlit/content_flags.py
#
# Content switches for the public dashboard.
#
# ACLED_CONTENT_ENABLED (2026-11, item 48): ACLED-based pages, sections and
# queries are switched off while CLIO's use of ACLED data is reviewed. With
# the flag False, ACLED-derived pages are not listed in st.navigation (so
# their URLs do not route), ACLED-derived page sections do not render, and
# the ACLED-derived query functions in services/marts.py return an empty
# DataFrame without running a query. Do not set this to True without the
# project owner's decision.

ACLED_CONTENT_ENABLED = False

ACLED_WITHDRAWN_NOTICE = (
    "ACLED-based content has been withdrawn while CLIO's use of ACLED data "
    "is reviewed."
)
