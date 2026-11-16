#!/usr/bin/env python3
"""False-verdict calibration for shutdowns_study.py on null synthetic fixtures (nothing planted
beyond the rise every election carries). Synthetic data only.
Run: python3 calibrate.py [runs] [lc]     ("lc" runs the election case only)"""
import collections
import contextlib
import io
import subprocess
import sys

import pandas as pd

import make_fixture as F
import shutdowns_study as S

RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
ONLY_LC = len(sys.argv) > 2 and sys.argv[2] == "lc"
EIGHT = ",".join(list(F.COUNTRIES) + list(F.MORE_COUNTRIES))
# The registered primary command's settings (registration section 6), on the election fixture.
PRIMARY = ["--country", EIGHT, "--primary-class", "LC", "--lc-design", "stratified", "--lc-filter", "timing=pre",
           "--loo", "strict", "--min-episodes", "10", "--mei-count", "1.5", "--mei-share", "0.10",
           "--start", "2016-01-01"]
CASES = {
    "elections in eight countries, L against C, the registered primary settings": (PRIMARY, ["--elections"], True),
    "one country, primary class P, matched placebo weeks":
        (["--country", "Synthia", "--primary-class", "P"], [], False),
    "one country, primary class E": (["--country", "Synthia", "--primary-class", "E"], [], False),
    "two countries, primary class E, with negative controls":
        (["--country", "Synthia,Fixtureland", "--primary-class", "E"], ["--two-country", "--negative-controls"], False),
}
WORDS = ("SUPPORTED", "CONTRADICTED", "DETECTED, BELOW", "NEGATIVE CONTROL MOVED")
for label, (study_args, fixture_args, election_list) in CASES.items():
    if ONLY_LC and not election_list:
        continue
    fired, raw, tests, runs_hit = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    for seed in range(1, RUNS + 1):
        subprocess.run([sys.executable, "make_fixture.py", "--out", "/tmp/cal.csv", "--episodes-out",
                        "/tmp/cal_ep.csv", "--seed", str(seed), "--no-effects", *fixture_args],
                       check=True, capture_output=True)
        if election_list:  # elections only, with the columns the registered list carries
            ep = pd.read_csv("/tmp/cal_ep.csv", dtype=str, keep_default_na=False)
            ep = ep[ep["class"].isin(["L", "C"])].copy()
            ep["status"] = "included"
            ep["timing"] = ep["class"].map({"L": "pre", "C": ""})
            ep.to_csv("/tmp/cal_ep.csv", index=False)
        with contextlib.redirect_stdout(io.StringIO()):
            r = S.main(["--input", "/tmp/cal.csv", "--episodes", "/tmp/cal_ep.csv", *study_args,
                        "--power-draws", "1"])
        hit = collections.Counter()
        for v in r["verdicts"]:
            g = v["group"]
            tests[g] += 1
            for word in WORDS:
                if v["result"].startswith(word):
                    fired[(g, word)] += 1
                    hit[g] += word != "DETECTED, BELOW"
            if "under-recording" in v["result"]:
                fired[(g, "UNDER")] += 1
            if v.get("p_two_sided", "n/a") != "n/a" and float(v["p_two_sided"]) <= 0.05:
                raw[g] += 1
        for g in hit:
            runs_hit[g] += hit[g] > 0
    print(f"\n{label}: {RUNS} null fixtures, script {S.VERSION}")
    for g in tests:
        print(f"  group {g}: tests {tests[g]}; unadjusted p <= 0.05: {raw[g]}; "
              f"supported {fired[(g, 'SUPPORTED')]}; contradicted {fired[(g, 'CONTRADICTED')]}; "
              f"detected below the minimum effect {fired[(g, 'DETECTED, BELOW')]}; "
              f"fall held back by the outage rule {fired[(g, 'UNDER')]}; "
              f"negative control moved {fired[(g, 'NEGATIVE CONTROL MOVED')]}; "
              f"runs with any false verdict {runs_hit[g]} of {RUNS}")
