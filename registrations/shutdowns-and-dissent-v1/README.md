# Shutdowns and dissent: registration v1 (frozen 2026-11-15)

These files were frozen on 2026-11-15, before any outcome data for the election analysis was read. Their SHA-256 hashes were published the same day in ADR-0016 (Step 4 notes). Check them with `sha256sum *`. The files are published unchanged, so their headers still describe their status at freezing ("Private: planning workspace").

| File | SHA-256 |
|---|---|
| registration-v1.md | 7efc4b805179a5dae70ecdfb1cb9fad920b9ac6bd1557d574b4391a5bd9c1a4a |
| election-list-procedure-v1.1-frozen.md | 8f9a8c2172eec38d0b0290beba562e7f3528f33f2b99a48fc71eff7467e929c8 |
| shutdowns_study.py (v0.5.1) | 2d7ef48bb0218380e84eff8dc9cc359114dd9ff3e1e788c0e1d0b604e83fb80e |
| make_fixture.py | c03bbdddc5ab3e69309692ce1abdfdde653355433162afbe69ed9ac9f93d7381 |
| test_on_fixture.py | 0de7a36b7d2689195e95d5d8edbb7e4183ee62313c9b81be2695b1144c9de962 |
| calibrate.py | 33f1fd5f7637a0ce821ffa740f259a3192acd122a1dee286990a2204994a963c |

**Status: parked (2026-11-16).** No election list has been built and no outcome analysis has been run. See ADR-0016, Step 5 notes.

The code runs on any CSV with ACLED's aggregated weekly columns. It was written and tested on synthetic data only: `python3 make_fixture.py --out fixture.csv --episodes-out episodes_fixture.csv && python3 test_on_fixture.py`. It prints summary statistics only, never weekly series. No ACLED data is included here.

The code was written with AI assistance (Anthropic models), and the registration was reviewed by them; the same model family wrote and reviewed it. Real-data runs are made by the maintainer outside any AI session.
