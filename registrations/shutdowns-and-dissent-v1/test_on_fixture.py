#!/usr/bin/env python3
"""Tests for shutdowns_study.py. Synthetic fixture only. Run: python3 test_on_fixture.py"""
import contextlib
import io
import itertools
import re
import subprocess
import sys

import numpy as np
import pandas as pd

import make_fixture as F
import shutdowns_study as S

PY = sys.executable


def run(args):
    # Checks 1 to 22 were written when class E was the default primary class; keep that for them.
    if "--primary-class" not in args:
        args = [*args, "--primary-class", "E"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = S.main(args)
    return res, buf.getvalue()


def make(out, extra=(), ep="/tmp/t_ep.csv"):
    subprocess.run([PY, "make_fixture.py", "--out", out, "--episodes-out", ep, *extra],
                   check=True, capture_output=True)


def stopped(args):
    """Run and return the stop message; fail if the run did not stop."""
    try:
        run(args)
    except SystemExit as e:
        return str(e)
    raise AssertionError("run did not stop")


def drop_weeks(src, dst, weeks):
    df = pd.read_csv(src, dtype=str)
    df[~df["WEEK"].isin(set(weeks))].to_csv(dst, index=False)


# Names and codes that must never appear in the analysis script (check 20). The invented
# fixture countries are included: the script may not name those either.
COUNTRY_LITERALS = [
    "Kenya", "Uganda", "Tanzania", "Rwanda", "Burundi", "Ethiopia", "Somalia", "Sudan", "Eritrea",
    "Djibouti", "Congo", "Nigeria", "Ghana", "Senegal", "Zambia", "Zimbabwe", "Malawi", "Mozambique",
    "Cameroon", "Egypt", "Algeria", "Morocco", "Tunisia", "Libya", "Mali", "Niger", "Chad", "Togo",
    "Benin", "Guinea", "Gabon", "Angola", "Namibia", "Botswana", "Lesotho", "Eswatini", "Madagascar",
    "Mauritania", "Gambia", "Liberia", "Sierra Leone", "Ivory Coast", "Burkina", "South Africa",
    "India", "Iran", "Iraq", "Syria", "Myanmar", "Pakistan", "Bangladesh", "Synthia", "Fixtureland",
]
COUNTRY_CODES = ["KE", "UG", "TZ", "RW", "BI", "ET", "SO", "SS", "SD", "ER", "DJ", "CD", "NG", "GH",
                 "KEN", "UGA", "TZA", "RWA", "BDI", "ETH", "SOM", "SSD", "SDN"]


def verdict(res, group, test):
    return next(v["result"] for v in res["verdicts"] if v["group"] == group and v["test"] == test)


def main():
    make("/tmp/t_fx.csv")
    make("/tmp/t_null.csv", ["--no-effects"])
    base = ["--episodes", "/tmp/t_ep.csv", "--country", "Synthia", "--draws", "1000", "--power-draws", "100"]

    # 1. planted effects are recovered in the class they were planted in, and not in the other
    # (effects are planted in class P, so P is made the primary class for this check)
    resp, _ = run(["--input", "/tmp/t_fx.csv", *base, "--primary-class", "P"])
    assert verdict(resp, "P", "T1").startswith("SUPPORTED: H1"), verdict(resp, "P", "T1")
    assert verdict(resp, "P", "T3").startswith("SUPPORTED: H4"), verdict(resp, "P", "T3")
    assert verdict(resp, "E", "T1").startswith("DESCRIPTIVE ONLY")
    # default: exam-timed class is primary; nothing was planted there, so nothing is supported,
    # and the other groups carry no verdict
    res, out = run(["--input", "/tmp/t_fx.csv", *base])
    assert not verdict(res, "E", "T1").startswith(("SUPPORTED", "CONTRADICTED"))
    assert not verdict(res, "E", "T3").startswith(("SUPPORTED", "CONTRADICTED"))
    assert verdict(res, "P", "T1").startswith("DESCRIPTIVE ONLY")
    assert verdict(res, "ALL", "T3").startswith("DESCRIPTIVE ONLY")
    assert res["facts"]["data_kind"] == "fixture"

    # 2. null fixture: nothing supported in the class-level tests
    for pc in ("E", "P"):
        res0, _ = run(["--input", "/tmp/t_null.csv", *base, "--primary-class", pc])
        for t in ("T1", "T2", "T3"):
            assert not verdict(res0, pc, t).startswith(("SUPPORTED", "CONTRADICTED")), (pc, t)

    # 3. output contract: no calendar dates outside the run-facts block, no long tables
    body = out.split("## EMPTY-WEEK CHECK")[1]
    assert not re.search(r"\b(19|20)\d{2}-\d{2}-\d{2}\b", body), "calendar date leaked into output tables"
    for block in body.split("\n## ")[1:]:
        assert len(block.strip().splitlines()) <= S.MAX_ROWS + 2, "table too long"

    # 4. the guard refuses weekly tables, date columns and level columns
    weekly = pd.DataFrame({"week": pd.date_range("2020-01-04", periods=5, freq="7D"), "x": range(5)})
    for bad in (weekly, weekly.rename(columns={"week": "w"}),
                pd.DataFrame({"events": [1, 2]}), pd.DataFrame({"k": ["2024-06-25"]}),
                pd.DataFrame({"rel": range(60)})):
        try:
            S.guard("bad", bad)
        except S.ContractViolation:
            continue
        raise AssertionError("guard let a forbidden table through")

    # 5. mixed synthetic and non-synthetic IDs are refused
    df = pd.read_csv("/tmp/t_fx.csv", dtype=str)
    df.loc[0, "ID"] = "X-1"
    df.to_csv("/tmp/t_mixed.csv", index=False)
    try:
        run(["--input", "/tmp/t_mixed.csv", *base])
        raise AssertionError("mixed IDs accepted")
    except SystemExit as e:
        assert "mixes" in str(e)

    # 6. non-Saturday weeks stop the run before analysis
    df = pd.read_csv("/tmp/t_fx.csv", dtype=str)
    df["WEEK"] = (pd.to_datetime(df["WEEK"]) + pd.Timedelta(days=2)).dt.strftime("%Y-%m-%d")
    df.to_csv("/tmp/t_monday.csv", index=False)
    try:
        run(["--input", "/tmp/t_monday.csv", *base])
        raise AssertionError("non-Saturday weeks accepted")
    except SystemExit as e:
        assert "Saturday" in str(e)

    # 7. below the minimum number of episodes, the verdict is descriptive only
    ep = pd.read_csv("/tmp/t_ep.csv", dtype=str)
    ep[ep["episode_id"].isin(["FX-P1", "FX-P2", "FX-E1"])].to_csv("/tmp/t_ep_few.csv", index=False)
    res2, out2 = run(["--input", "/tmp/t_fx.csv", "--episodes", "/tmp/t_ep_few.csv", "--country", "Synthia",
                      "--draws", "500", "--power-draws", "50", "--primary-class", "P"])
    assert "below the minimum" in verdict(res2, "P", "T1")
    assert not any(r["group"] == "E" for r in res2["leadlag"]), "lead/lag printed for a single episode"

    # 8. same seed, same output
    _, out_b = run(["--input", "/tmp/t_fx.csv", *base])
    assert out == out_b, "output is not reproducible for a fixed seed"

    # 9. --descriptive-only removes every verdict
    res3, _ = run(["--input", "/tmp/t_fx.csv", *base, "--descriptive-only"])
    assert all(v["result"].startswith("DESCRIPTIVE ONLY") for v in res3["verdicts"])

    # 10. an episode list with a status column: only "included" rows are used
    ep = pd.read_csv("/tmp/t_ep.csv", dtype=str)
    ep["status"] = ["included"] * (len(ep) - 2) + ["ambiguous", "excluded"]
    ep.to_csv("/tmp/t_ep_status.csv", index=False)
    res4, _ = run(["--input", "/tmp/t_fx.csv", "--episodes", "/tmp/t_ep_status.csv", "--country", "Synthia",
                   "--draws", "300", "--power-draws", "20"])
    assert res4["facts"]["episodes_listed"] == len(ep) and res4["facts"]["episodes_used"] == len(ep) - 2

    # 11. the sensitivity run adds ambiguous rows and never excluded ones
    res5, _ = run(["--input", "/tmp/t_fx.csv", "--episodes", "/tmp/t_ep_status.csv", "--country", "Synthia",
                   "--draws", "300", "--power-draws", "20", "--include-ambiguous"])
    assert res5["facts"]["episodes_used"] == len(ep) - 1 and res5["facts"]["include_ambiguous"] is True

    # ---------------------------------------------------------------- added for version 0.4.0
    # 12. an effect planted against the hypothesis returns "contradicted" (two-sided tests)
    make("/tmp/t_opp.csv", ["--opposite"])
    reso, _ = run(["--input", "/tmp/t_opp.csv", *base, "--primary-class", "P"])
    assert verdict(reso, "P", "T2").startswith("CONTRADICTED: H3"), verdict(reso, "P", "T2")
    assert verdict(reso, "P", "T1").startswith("SUPPORTED: H2 suppression (H1 backfire contradicted)"), \
        verdict(reso, "P", "T1")
    # T3's outcome is sparse, so a planted fall cannot be told apart (a floor effect; README 9.5).
    # The direction is still reported, and the rule must not call it supported.
    assert next(v for v in reso["verdicts"] if v["group"] == "P" and v["test"] == "T3")["direction"] == "down"
    assert not verdict(reso, "P", "T3").startswith("SUPPORTED")

    # 13. exact enumeration: rank and p match a brute-force count on a tiny case
    ep = pd.read_csv("/tmp/t_ep.csv", dtype=str)
    ep[ep["episode_id"].isin(["FX-E2", "FX-E3"])].to_csv("/tmp/t_ep_two.csv", index=False)
    tiny = ["--input", "/tmp/t_null.csv", "--episodes", "/tmp/t_ep_two.csv", "--country", "Synthia",
            "--start", "2016-01-01", "--power-draws", "50", "--min-episodes", "2"]
    rest, outt = run(tiny)
    pe = next(r for r in rest["placebo"] if r["group"] == "E")
    assert pe["method"].startswith("exact"), pe
    df, _ = S.load("/tmp/t_null.csv")
    d = df[(df["COUNTRY"] == "Synthia") & (df["WEEK"] >= "2016-01-01")]
    w0 = pd.Timestamp("2016-01-02")
    y, weeks, _, _ = S.build_series(d, w0, d["WEEK"].max())
    spans = [((pd.Timestamp(a) - w0).days // 7, (pd.Timestamp(b) - w0).days // 7)
             for a, b in [("2021-10-05", "2021-10-22"), ("2023-10-10", "2023-10-27")]]
    eng = S.Engine(y, len(weeks), spans)
    cands = [eng.placebo_starts(a, b - a + 1, "E") for a, b in spans]
    durs = [b - a + 1 for a, b in spans]
    assert int(pe["possible_sets"]) == len(cands[0]) * len(cands[1])
    for test, key in (("T1", ("Y1", "after")), ("T3", ("Y2", "da"))):
        def val(i, x):
            return eng.adjusted(x, durs[i], is_real=(x == spans[i][0]))[0][key]
        obs = (val(0, spans[0][0]) + val(1, spans[1][0])) / 2
        allv = [(val(0, a) + val(1, b)) / 2 for a, b in itertools.product(*cands)]
        brute = sum(abs(v) >= abs(obs) - 1e-12 for v in allv)
        row = next(v for v in rest["verdicts"] if v["group"] == "E" and v["test"] == test)
        assert row["rank"] == f"{brute} of {len(allv)}", (row["rank"], brute, len(allv))
        assert row["p_two_sided"] == f"{brute / len(allv):.4f}"
    # exact results do not depend on the seed
    rest2, _ = run(tiny + ["--seed", "7"])
    assert [v["p_two_sided"] for v in rest["verdicts"]] == [v["p_two_sided"] for v in rest2["verdicts"]]

    # the exact path can also return verdicts: the planted class-P episodes relabelled as class E
    ep[ep["class"] == "P"].assign(**{"class": "E"}).to_csv("/tmp/t_ep_pe.csv", index=False)
    resx, _ = run(["--input", "/tmp/t_fx.csv", "--episodes", "/tmp/t_ep_pe.csv", "--country", "Synthia",
                   "--power-draws", "20"])
    assert next(r for r in resx["placebo"] if r["group"] == "E")["method"].startswith("exact")
    assert verdict(resx, "E", "T1").startswith("SUPPORTED: H1") and verdict(resx, "E", "T3").startswith("SUPPORTED: H4")

    # 14. power: the x1.0 row (nothing planted) sits near the nominal level on a null fixture,
    # the full rule never exceeds the unadjusted figure, and power rises with the multiplier
    resn, _ = run(["--input", "/tmp/t_null.csv", "--episodes", "/tmp/t_ep.csv", "--country", "Synthia",
                   "--primary-class", "P", "--power-draws", "400"])
    for t in ("T1", "T2", "T3"):
        raw = next(r for r in resn["power"] if r["group"] == "P" and r["test"] == t and r["rule"] == "unadjusted 5%")
        full = next(r for r in resn["power"] if r["group"] == "P" and r["test"] == t and r["rule"] == "full rule")
        assert 0.01 <= float(raw["x1.0"]) <= 0.10, (t, raw["x1.0"])
        assert float(full["x1.0"]) <= 0.05, (t, full["x1.0"])
        assert all(float(full[c]) <= float(raw[c]) for c in raw if c.startswith("x"))
        assert float(raw["x3.0"]) >= float(raw["x2.0"]) >= float(raw["x1.5"]) > float(raw["x1.0"]), (t, raw)
    # too few placebo sets: no power figure
    ep[ep["episode_id"].isin(["FX-E3"])].to_csv("/tmp/t_ep_one.csv", index=False)
    res1, _ = run(["--input", "/tmp/t_null.csv", "--episodes", "/tmp/t_ep_one.csv", "--country", "Synthia"])
    assert any("not measurable at this size" in r["rule"] for r in res1["power"])
    assert not any(r["rule"] in ("unadjusted 5%", "full rule") for r in res1["power"])

    # 15. --start/--end filter by parsed week, on the real product's day-month-year text
    make("/tmp/t_dmy.csv", ["--week-format", "dmy"])
    assert re.fullmatch(r"\d{1,2}-[A-Z][a-z]+-\d{4}", pd.read_csv("/tmp/t_dmy.csv", dtype=str)["WEEK"][0])
    period = ["--start", "2018-01-01", "--end", "2023-12-31"]
    resd, _ = run(["--input", "/tmp/t_dmy.csv", *base, *period])
    iso = pd.read_csv("/tmp/t_fx.csv", dtype=str)
    want = iso[(iso["WEEK"] >= "2018-01-01") & (iso["WEEK"] <= "2023-12-31")]
    f = resd["facts"]
    assert f["week_format_parsed"] == "D-Month-YYYY" and f["rows_in_period"] == len(want)
    fc = f["countries"]["Synthia"]
    assert fc["range_first_week"] == "2018-01-06" and fc["range_last_week"] == "2023-12-30", fc
    assert fc["rows"] == int((want["COUNTRY"] == "Synthia").sum())
    resi, _ = run(["--input", "/tmp/t_fx.csv", *base, *period])  # same rows as ISO text: same results
    assert resd["verdicts"] == resi["verdicts"] and resd["power"] == resi["power"]
    bad = pd.read_csv("/tmp/t_fx.csv", dtype=str)
    bad["WEEK"] = pd.to_datetime(bad["WEEK"]).dt.strftime("%m/%d/%Y")
    bad.to_csv("/tmp/t_badfmt.csv", index=False)
    assert "neither known format" in stopped(["--input", "/tmp/t_badfmt.csv", *base])

    # 16. --facts-only prints the facts, structure and coverage, and no test
    resf, outf = run(["--input", "/tmp/t_fx.csv", *base, "--facts-only"])
    assert "# RUN FACTS" in outf and "## EPISODES" in outf and "## OUTCOME COVERAGE" in outf
    for banned in ("PRIMARY TESTS", "EXPLORATORY", "LEAD/LAG", "## POWER", "PLACEBO STRUCTURE", "p_two_sided"):
        assert banned not in outf, banned
    assert resf["verdicts"] == [] and "no test was computed" in outf

    # 17. the empty-week stop fires on each condition, and the override works
    allw = [w.strftime("%Y-%m-%d") for w in pd.date_range("2015-01-03", "2025-12-27", freq="7D")]
    drop_weeks("/tmp/t_fx.csv", "/tmp/t_gap.csv", allw[300:305])            # five consecutive weeks
    msg = stopped(["--input", "/tmp/t_gap.csv", *base])
    assert "consecutive weeks" in msg and "no row for any country" in msg and "more than" not in msg, msg
    drop_weeks("/tmp/t_fx.csv", "/tmp/t_sparse.csv", allw[10:570:25])       # 23 scattered weeks, about 4%
    msg = stopped(["--input", "/tmp/t_sparse.csv", *base])
    assert "more than 2%" in msg and "consecutive" not in msg, msg
    resa, outa = run(["--input", "/tmp/t_gap.csv", *base, "--allow-empty-weeks"])
    assert "FAILED" in outa and resa["verdicts"], "override did not run"
    _, outg = run(["--input", "/tmp/t_gap.csv", *base, "--facts-only"])     # facts-only reports, never tests
    assert "FAILED" in outg and "PRIMARY TESTS" not in outg

    # 18. negative-control episodes (class N) form their own group and are never pooled
    make("/tmp/t_two.csv", ["--two-country", "--negative-controls"], ep="/tmp/t_ep2.csv")
    both = ["--input", "/tmp/t_two.csv", "--episodes", "/tmp/t_ep2.csv", "--country", "Synthia,Fixtureland",
            "--draws", "1000", "--power-draws", "50"]
    res2c, out2c = run(both)
    ep2 = pd.read_csv("/tmp/t_ep2.csv", dtype=str)
    npl = {r["group"]: r["episodes"] for r in res2c["placebo"]}
    assert npl["N"] == (ep2["class"] == "N").sum() == 3
    assert npl["ALL"] == (ep2["class"] != "N").sum() and npl["ALL"] == npl["E"] + npl["P"]
    for v in res2c["verdicts"]:
        if v["group"] == "N":
            assert v["expected"] == "null expected" and v["result"].startswith("NULL EXPECTED"), v
        else:
            assert v["expected"] != "null expected"
    nolist = ep2[ep2["class"] != "N"]
    nolist.to_csv("/tmp/t_ep2_noN.csv", index=False)
    resno, _ = run([*both[:3], "/tmp/t_ep2_noN.csv", *both[4:]])
    assert res2c["obs"]["ALL"] == resno["obs"]["ALL"] and res2c["obs"]["E"] == resno["obs"]["E"]
    ep2.assign(**{"class": ep2["class"].replace("N", "X")}).to_csv("/tmp/t_ep2_bad.csv", index=False)
    assert "classes other than" in stopped([*both[:3], "/tmp/t_ep2_bad.csv", *both[4:]])

    # 19. several countries: each episode's placebo positions come from its own country's series.
    # The second country's series is cut short, so the two countries have different week ranges.
    two = pd.read_csv("/tmp/t_two.csv", dtype=str)
    two[~((two["COUNTRY"] == "Fixtureland") & (two["WEEK"] < "2017-01-01"))].to_csv("/tmp/t_two_cut.csv", index=False)
    only_e = ep2[ep2["class"] == "E"]
    only_e.to_csv("/tmp/t_ep2_E.csv", index=False)
    common = ["--input", "/tmp/t_two_cut.csv", "--episodes", "/tmp/t_ep2_E.csv", "--power-draws", "20"]
    r_both, _ = run([*common, "--country", "Synthia,Fixtureland"])
    r_a, _ = run([*common, "--country", "Synthia"])
    r_b, _ = run([*common, "--country", "Fixtureland"])
    fa, fb = r_both["facts"]["countries"]["Synthia"], r_both["facts"]["countries"]["Fixtureland"]
    assert fa["weeks_in_range"] != fb["weeks_in_range"]
    assert fa == r_a["facts"]["countries"]["Synthia"] and fb == r_b["facts"]["countries"]["Fixtureland"]
    sets = lambda r: int(float(next(x for x in r["placebo"] if x["group"] == "E")["possible_sets"]))
    assert sets(r_both) == sets(r_a) * sets(r_b), "placebo positions are not taken per country"
    pos = lambda r, k: next(x for x in r["placebo"] if x["group"] == "E")[k]
    assert pos(r_both, "min_placebo_positions") == min(pos(r_a, "min_placebo_positions"), pos(r_b, "min_placebo_positions"))
    assert pos(r_both, "max_placebo_positions") == max(pos(r_a, "max_placebo_positions"), pos(r_b, "max_placebo_positions"))
    for t in ("T1", "T2", "T3"):  # three episodes in each country: the pooled change is the plain average
        avg = (r_a["obs"]["E"][t] + r_b["obs"]["E"][t]) / 2
        assert abs(r_both["obs"]["E"][t] - avg) < 1e-9, t
    assert "distinct names" in stopped([*common, "--country", "Synthia,Synthia"])

    # 20. the analysis script names no country (names, or quoted two- and three-letter codes)
    src = open(S.__file__, encoding="utf-8").read()
    for name in COUNTRY_LITERALS:
        assert not re.search(r"\b" + re.escape(name) + r"\b", src, re.I), f"country literal in script: {name}"
    for code in COUNTRY_CODES:
        assert not re.search(r"""["']""" + code + r"""["']""", src), f"country code in script: {code}"
    for name in list(F.COUNTRIES) + list(F.MORE_COUNTRIES):
        assert name not in src, f"fixture country named in script: {name}"
    assert S.VERSION == "0.5.1"

    # ---------------------------------------------------------------- added for version 0.4.1
    # 21. a quiet country inside a complete file does not stop the run: its own empty weeks are
    # reported in the run facts, and the file-level check passes
    full = pd.read_csv("/tmp/t_fx.csv", dtype=str)
    keep_weeks = set(allw[::6])  # the second country keeps rows in one week out of six
    quiet = full[(full["COUNTRY"] != "Fixtureland") | full["WEEK"].isin(keep_weeks)]
    quiet.to_csv("/tmp/t_quiet.csv", index=False)
    resq, outq = run(["--input", "/tmp/t_quiet.csv", "--episodes", "/tmp/t_ep.csv",
                      "--country", "Synthia,Fixtureland", "--draws", "300", "--power-draws", "20"])
    fq = resq["facts"]
    assert fq["countries"]["Fixtureland"]["share_of_weeks_with_no_rows"] > 0.5
    assert fq["countries"]["Fixtureland"]["longest_run_of_weeks_with_no_rows"] >= 4
    assert fq["file_weeks_with_no_rows_for_any_country"] == 3 and "passed" in outq and resq["verdicts"]
    # listed alone, with the other country's rows still in the file, it still does not stop
    resq1, _ = run(["--input", "/tmp/t_quiet.csv", "--episodes", "/tmp/t_ep2.csv", "--country", "Fixtureland",
                    "--draws", "300", "--power-draws", "20"])
    assert resq1["facts"]["file_countries_in_period"] == 2 and resq1["verdicts"]

    # 22. whole weeks removed from the file stop the run. This is the broken filter of 2026-11-14:
    # rows were kept by comparing day-month-year text, which keeps or drops whole weeks by day number
    dmy = pd.read_csv("/tmp/t_dmy.csv", dtype=str)
    broken = dmy[dmy["WEEK"] >= "2-"]  # text comparison: drops every week whose day starts with "1"
    assert 0 < len(broken) < len(dmy)
    broken.to_csv("/tmp/t_broken.csv", index=False)
    msg = stopped(["--input", "/tmp/t_broken.csv", *base])
    assert "no row for any country" in msg and "more than 2%" in msg, msg

    # ---------------------------------------------------------------- added for version 0.5.0
    names = ",".join(list(F.COUNTRIES) + list(F.MORE_COUNTRIES))
    make("/tmp/t_el.csv", ["--elections"], ep="/tmp/t_el_ep.csv")
    make("/tmp/t_el_null.csv", ["--elections", "--no-effects"], ep="/tmp/t_el_ep.csv")
    make("/tmp/t_el_both.csv", ["--elections", "--effect-both"], ep="/tmp/t_el_ep.csv")
    elec = pd.read_csv("/tmp/t_el_ep.csv", dtype=str, keep_default_na=False)
    only_lc = elec[elec["class"].isin(["L", "C"])]
    only_lc.to_csv("/tmp/t_lc_ep.csv", index=False)
    lc = ["--episodes", "/tmp/t_lc_ep.csv", "--country", names, "--primary-class", "LC", "--power-draws", "30"]
    lcv = lambda r, t: verdict(r, "L-C", t)

    # 23. effects planted in L elections and not in C are found, in both designs; every election
    # also carries an election-season rise, which the C elections cancel
    for design in ("stratified", "pooled"):
        r, o = run(["--input", "/tmp/t_el.csv", *lc, "--lc-design", design])
        assert lcv(r, "T1").startswith("SUPPORTED: H1"), (design, lcv(r, "T1"))
        assert lcv(r, "T3").startswith("SUPPORTED: H4"), (design, lcv(r, "T3"))
        assert r["lc"][0]["L_used"] == 20 and r["lc"][0]["C_used"] == 20 and r["facts"]["lc_design"] == design
        assert r["lc"][0]["strata_used"] == (8 if design == "stratified" else 1)
    assert "not other years" in o and not r["placebo"][0].get("possible_sets")

    # 24. nothing planted in L: no verdict, and the x1.0 power row sits near the nominal level
    r0, _ = run(["--input", "/tmp/t_el_null.csv", *lc[:-1], "300"])
    for t in ("T1", "T2", "T3"):
        assert lcv(r0, t).startswith("INSUFFICIENT EVIDENCE"), (t, lcv(r0, t))
        raw = next(x for x in r0["power"] if x["group"] == "L-C" and x["test"] == t and x["rule"] == "unadjusted 5%")
        full = next(x for x in r0["power"] if x["group"] == "L-C" and x["test"] == t and x["rule"] == "full rule")
        assert 0.01 <= float(raw["x1.0"]) <= 0.10 and float(full["x1.0"]) <= 0.05, (t, raw["x1.0"], full["x1.0"])
        assert float(raw["x3.0"]) > float(raw["x1.5"]) > float(raw["x1.0"]), (t, raw)

    # 25. the same effect planted in L and in C elections: the difference is not "supported"
    rb, _ = run(["--input", "/tmp/t_el_both.csv", *lc])
    for t in ("T1", "T2", "T3"):
        assert not lcv(rb, t).startswith(("SUPPORTED", "CONTRADICTED")), (t, lcv(rb, t))

    # 26. class P placebo weeks come from the episode's own tercile of pre-episode level
    df, _ = S.load("/tmp/t_fx.csv")
    d = df[df["COUNTRY"] == "Synthia"]
    w0 = d["WEEK"].min()
    y, weeks, _, _ = S.build_series(d, w0, d["WEEK"].max())
    pep = pd.read_csv("/tmp/t_ep.csv", dtype=str)
    spans = [((pd.Timestamp(a) - w0).days // 7, (pd.Timestamp(b) - w0).days // 7)
             for a, b in zip(pep["start_date"], pep["end_date"])]
    eng = S.Engine(y, len(weeks), spans)
    rp, _ = run(["--input", "/tmp/t_fx.csv", *base, "--primary-class", "P"])
    for (a, b), eid, cls in zip(spans, pep["episode_id"], pep["class"]):
        if cls != "P":
            continue
        every = eng.placebo_starts(a, b - a + 1, "P")[:-1]
        matched = eng.placebo_starts(a, b - a + 1, "P", matched=True)[:-1]
        levels = np.array([eng.lead_level(c) for c in every])
        cuts = np.quantile(levels, [1 / 3, 2 / 3])
        tercile = lambda x: int(np.searchsorted(cuts, x, side="right"))
        own = tercile(eng.lead_level(a))
        assert matched == [c for c, lv in zip(every, levels) if tercile(lv) == own] and matched
        assert len(every) / 3 - 2 <= len(matched) <= len(every) / 3 + 2
        printed = next(m["matched_placebo_positions"] for m in rp["matching"] if m["episode_id"] == eid)
        assert printed == len(matched)
    assert verdict(rp, "P", "T1").startswith("SUPPORTED: H1")       # still found with matched weeks
    ra, _ = run(["--input", "/tmp/t_fx.csv", *base, "--primary-class", "P", "--p-placebo", "all"])
    assert not ra["matching"] and next(x for x in ra["placebo"] if x["group"] == "P")["min_placebo_positions"] > 400
    # too few matched weeks: not testable (the threshold is raised for this check, then restored)
    keep_min, S.MIN_MATCHED = S.MIN_MATCHED, 1000
    rt, _ = run(["--input", "/tmp/t_fx.csv", *base, "--primary-class", "P", "--power-draws", "5"])
    S.MIN_MATCHED = keep_min
    assert all(m["matched_placebo_positions"] < 1000 for m in rt["matching"])
    assert verdict(rt, "P", "T1").startswith("NOT TESTABLE"), verdict(rt, "P", "T1")
    assert S.MIN_MATCHED == 20

    # 27. label permutations: exact enumeration matches a brute-force count, in both designs
    two = ["Synthia", "Fixtureland"]
    small = only_lc[only_lc["country"].isin(two)].reset_index(drop=True)
    small.to_csv("/tmp/t_lc_small.csv", index=False)
    dfe, _ = S.load("/tmp/t_el_null.csv")
    vals = {}
    for c in two:
        dc = dfe[dfe["COUNTRY"] == c]
        w0c = dc["WEEK"].min()
        yc, wk, _, _ = S.build_series(dc, w0c, dc["WEEK"].max())
        ec = S.Engine(yc, len(wk), [])
        for _, row in small[small["country"] == c].iterrows():
            a = (pd.Timestamp(row["anchor_date"]) - w0c).days // 7
            vals[row["episode_id"]] = ec._raw_stats(a, 0)[("Y1", "after")]
    ids, cls, ctry = list(small["episode_id"]), list(small["class"]), list(small["country"])
    v = np.array([vals[i] for i in ids])
    is_l = np.array([c == "L" for c in cls])

    def strat_stat(lab):
        num = den = 0.0
        for c in two:
            ix = [i for i in range(len(ids)) if ctry[i] == c]
            l_ = [v[i] for i in ix if lab[i]]
            c_ = [v[i] for i in ix if not lab[i]]
            num += len(l_) * (np.mean(l_) - np.mean(c_))
            den += len(l_)
        return num / den

    def pool_stat(lab):
        return np.mean(v[lab]) - np.mean(v[~lab])

    for design, stat, n_expected in (("stratified", strat_stat, 100), ("pooled", pool_stat, 252)):
        rs, _ = run(["--input", "/tmp/t_el_null.csv", "--episodes", "/tmp/t_lc_small.csv", "--country",
                     ",".join(two), "--primary-class", "LC", "--lc-design", design, "--power-draws", "10"])
        assert rs["lc"][0]["label_arrangements"] == str(n_expected) and rs["lc"][0]["method"].startswith("exact")
        labs = []
        for combo in itertools.combinations(range(len(ids)), int(is_l.sum())):
            lab = np.zeros(len(ids), dtype=bool)
            lab[list(combo)] = True
            if design == "pooled" or all(lab[[i for i in range(len(ids)) if ctry[i] == c]].sum()
                                         == is_l[[i for i in range(len(ids)) if ctry[i] == c]].sum() for c in two):
                labs.append(lab)
        assert len(labs) == n_expected
        obs = stat(is_l)
        brute = sum(abs(stat(lab)) >= abs(obs) - 1e-12 for lab in labs)
        row = next(x for x in rs["verdicts"] if x["group"] == "L-C" and x["test"] == "T1")
        assert row["rank"] == f"{brute} of {n_expected}", (design, row["rank"], brute)
        assert row["p_two_sided"] == f"{brute / n_expected:.4f}"
        assert abs(rs["obs"]["L-C"]["T1"] - obs) < 1e-9

    # 28. both leave-one-out forms are selectable; "sign" asks less than "strict"
    S.LOO_MODE = "strict"
    weak = [(1.0, 0.50), (2.0, 0.50)]
    assert S.decide(0.01, 1.5, 0.0, None, weak)[0] is False
    S.LOO_MODE = "sign"
    assert S.decide(0.01, 1.5, 0.0, None, weak)[0] is True
    assert S.decide(0.01, 1.5, 0.0, None, [(1.0, 0.5), (-2.0, 0.01)])[0] is False
    S.LOO_MODE = "strict"
    rsg, _ = run(["--input", "/tmp/t_el.csv", *lc, "--loo", "sign"])
    assert rsg["facts"]["leave_one_out"] == "sign" and lcv(rsg, "T1").startswith("SUPPORTED: H1")
    assert r["facts"]["leave_one_out"] == "strict"

    # 29. the episode-list rules for elections
    only_lc.drop(columns=["anchor_date"]).to_csv("/tmp/t_lc_noanchor.csv", index=False)
    assert "anchor_date" in stopped(["--input", "/tmp/t_el.csv", "--episodes", "/tmp/t_lc_noanchor.csv",
                                     "--country", names, "--primary-class", "LC"])
    only_lc.assign(stratum="one").to_csv("/tmp/t_lc_onestratum.csv", index=False)   # a stratum column wins
    r1s, _ = run(["--input", "/tmp/t_el.csv", "--episodes", "/tmp/t_lc_onestratum.csv", "--country", names,
                  "--primary-class", "LC", "--power-draws", "5"])
    rpl, _ = run(["--input", "/tmp/t_el.csv", *lc[:-1], "5", "--lc-design", "pooled"])
    assert abs(r1s["obs"]["L-C"]["T1"] - rpl["obs"]["L-C"]["T1"]) < 1e-12 and r1s["lc"][0]["strata_used"] == 1
    rf, _ = run(["--input", "/tmp/t_el.csv", *lc[:-1], "5", "--lc-filter", "type=full outage"])   # all L are outages
    assert rf["lc"][0]["L_used"] == 20 and rf["facts"]["lc_filter"] == "type=full outage"
    rn, _ = run(["--input", "/tmp/t_el.csv", *lc[:-1], "5", "--lc-filter", "type=absent"])   # no L left
    assert lcv(rn, "all").startswith("NOT RUN")
    # a country whose elections are all L has no counterpart under the stratified design and is dropped
    lone = only_lc.copy()
    lone.loc[lone["country"] == "Synthia", "class"] = "L"
    lone.loc[lone["country"] == "Synthia", "type"] = "full outage"
    lone.to_csv("/tmp/t_lc_lone.csv", index=False)
    rl, _ = run(["--input", "/tmp/t_el.csv", "--episodes", "/tmp/t_lc_lone.csv", "--country", names,
                 "--primary-class", "LC", "--power-draws", "5"])
    assert rl["lc"][0]["dropped_no_counterpart"] == 5 and rl["lc"][0]["strata_used"] == 7

    # 30. L and C never enter the exam, political or pooled groups, and C does not screen placebo weeks
    rall, _ = run(["--input", "/tmp/t_el.csv", "--episodes", "/tmp/t_el_ep.csv", "--country", names,
                   "--primary-class", "LC", "--power-draws", "5"])
    counts = {x["group"]: x["episodes"] for x in rall["placebo"]}
    assert counts == {"ALL": 7, "P": 4, "E": 3}, counts
    assert {x["group"] for x in rall["verdicts"]} == {"ALL", "P", "E", "L-C"}
    for x in rall["verdicts"]:
        if x["group"] != "L-C":
            assert x["result"].startswith("DESCRIPTIVE ONLY")

    # 31. the reporting-check outcome (armed clashes) is reported for every group, marked as such,
    # and carries no verdict; it appears in the coverage table
    yb = [x for x in rall["explore"] if x["outcome"] == "YB"]
    assert {x["group"] for x in yb} == {"ALL", "P", "E", "L-C"} and all(x["status"] == "reporting check" for x in yb)
    assert all(x["status"] == "exploratory" for x in rall["explore"] if x["outcome"] != "YB")
    assert not any(v.get("outcome") == "YB" for v in rall["verdicts"])
    _, oall = run(["--input", "/tmp/t_el.csv", "--episodes", "/tmp/t_el_ep.csv", "--country", names, "--facts-only"])
    assert re.search(r"^\s*YB\s", oall, re.M), "YB missing from outcome coverage"

    # ---------------------------------------------------------------- added for version 0.5.1
    reg = ["--country", names, "--primary-class", "LC", "--lc-design", "stratified", "--loo", "strict",
           "--mei-count", "1.5", "--mei-share", "0.10", "--start", "2016-01-01"]
    full = only_lc.copy()
    full["status"] = "included"
    full["timing"] = np.where(full["class"] == "L", "pre", "")
    full["stratum"] = full["country"]
    full.to_csv("/tmp/t_reg.csv", index=False)

    # 32. --power-only prints the facts, the usable counts, the power table and one gate figure,
    # and no test result; its power table is the full run's, figure for figure
    pw = ["--input", "/tmp/t_el_null.csv", "--episodes", "/tmp/t_reg.csv", *reg, "--lc-filter", "timing=pre",
          "--min-episodes", "10", "--power-draws", "60"]
    rp_, op_ = run(pw + ["--power-only"])
    rfull, ofull = run(pw)
    for banned in ("PRIMARY TESTS", "EXPLORATORY", "LEAD/LAG", "p_two_sided", "pooled_change", "VINTAGE"):
        assert banned not in op_, banned
    assert "## POWER GATE FIGURE" in op_ and "USABLE ELECTIONS BY STRATUM" in op_ and "no test result was printed" in op_
    assert rp_["verdicts"] == [] and rp_["explore"] == [] and rp_["obs"] == {}
    assert rp_["power"] == rfull["power"] and rp_["gate"] == rfull["gate"]
    rows_lc = [x for x in rp_["power"] if x["group"] == "L-C"]
    assert [x["rule"] for x in rows_lc[:3]] == ["unadjusted 5%", "three conditions", "full rule"] and len(rows_lc) == 9
    for x in rows_lc:
        assert {"x0.67", "x1.5", "share-0.10", "share+0.10"} <= set(x)
        assert (x["share+0.10"] == "n/a") == (x["test"] != "T2"), x
    for t in ("T1", "T2", "T3"):
        raw, three, fr = [next(x for x in rows_lc if x["test"] == t and x["rule"] == r_)
                          for r_ in ("unadjusted 5%", "three conditions", "full rule")]
        for c in [k for k in raw if k.startswith(("x", "share")) and raw[k] != "n/a"]:
            assert float(fr[c]) <= float(three[c]) <= float(raw[c]), (t, c)
    t1 = next(x for x in rows_lc if x["test"] == "T1" and x["rule"] == "three conditions")
    assert rp_["gate"] == float(t1["x1.5"]) and f"{rp_['gate']:.2f}" in op_.split("## POWER GATE FIGURE")[1]
    t2 = next(x for x in rows_lc if x["test"] == "T2" and x["rule"] == "unadjusted 5%")
    assert float(t2["share+0.10"]) > float(t2["x1.0"]) and float(t2["share-0.10"]) > float(t2["x1.0"]), t2
    assert "not both" in stopped(pw + ["--power-only", "--facts-only"])
    rfo, ofo = run(pw + ["--facts-only"])   # the usable counts are in the facts-only output too
    assert rfo["usable"] == rp_["usable"] and rfo["usable"][-1] == {"stratum": "TOTAL", "L_usable": 20, "C_usable": 20}
    assert "USABLE ELECTIONS BY STRATUM" in ofo and "PRIMARY TESTS" not in ofo and "## POWER" not in ofo
    assert len(rfo["usable"]) == 9 and all(u["L_usable"] >= 1 and u["C_usable"] >= 1 for u in rfo["usable"])

    # 33. --include-ambiguous-controls promotes doubtful controls only
    amb = full.copy()
    li, ci = amb.index[amb["class"] == "L"][:3], amb.index[amb["class"] == "C"][:4]
    amb.loc[li, "status"] = "ambiguous"
    amb.loc[ci, "status"] = "ambiguous"
    amb.to_csv("/tmp/t_amb.csv", index=False)
    fo = ["--input", "/tmp/t_el_null.csv", "--episodes", "/tmp/t_amb.csv", *reg, "--facts-only"]
    used = lambda r: (r["lc"][0]["L_listed"], r["lc"][0]["C_listed"])
    assert used(run(fo)[0]) == (17, 16)
    assert used(run(fo + ["--include-ambiguous-controls"])[0]) == (17, 20)
    assert used(run(fo + ["--include-ambiguous"])[0]) == (20, 20)
    assert run(fo + ["--include-ambiguous-controls"])[0]["facts"]["include_ambiguous_controls"] is True

    # 34. --lc-filter can be repeated; the filters combine with AND; case and outer spaces are ignored
    mix = full.copy()
    Lx = mix.index[mix["class"] == "L"]
    mix.loc[Lx[:4], "type"] = "platform block"                                   # pre, platform block
    mix.loc[Lx[4:10], ["type", "timing"]] = ["platform block", "post"]           # post, platform block
    mix.to_csv("/tmp/t_mix.csv", index=False)
    fm = ["--input", "/tmp/t_el_null.csv", "--episodes", "/tmp/t_mix.csv", *reg, "--facts-only"]
    n_l = lambda extra: run(fm + extra)[0]["lc"][0]["L_listed"]
    assert n_l([]) == 20 and n_l(["--lc-filter", "timing=pre"]) == 14 and n_l(["--lc-filter", "type=platform block"]) == 10
    both_f = ["--lc-filter", "timing=pre", "--lc-filter", "type=platform block"]
    assert n_l(both_f) == 4 and n_l(both_f[2:] + both_f[:2]) == 4
    assert n_l(["--lc-filter", "timing= PRE ", "--lc-filter", " type = Platform Block "]) == 4
    rm_, _ = run(fm + both_f)
    assert rm_["facts"]["lc_filter"] == "timing=pre AND type=platform block" and rm_["lc"][0]["C_listed"] == 20
    assert rm_["lc"][0]["outage_among_L_used"] is False and run(fm)[0]["lc"][0]["outage_among_L_used"] is True
    assert "COLUMN=VALUE" in stopped(fm + ["--lc-filter", "nosuchcolumn=pre"])

    # 35. --min-episodes counts usable L: included, complete window, a usable C in the same stratum
    few = full[~((full["country"] == "Synthia") & (full["class"] == "C"))]     # one country loses its controls
    few.to_csv("/tmp/t_few.csv", index=False)
    ff = ["--input", "/tmp/t_el.csv", "--episodes", "/tmp/t_few.csv", *reg, "--power-draws", "5"]
    r18, _ = run(ff + ["--min-episodes", "18"])
    assert r18["lc"][0]["L_listed"] == 20 and r18["lc"][0]["L_used"] == 17 and r18["usable"][-1]["L_usable"] == 17
    assert lcv(r18, "T1").startswith("DESCRIPTIVE ONLY: 17 L election(s) usable, below the minimum of 18")
    assert lcv(run(ff + ["--min-episodes", "17"])[0], "T1").startswith("SUPPORTED: H1")
    # under the stratified design the minimum applies to L only: 18 usable C do not block a minimum of 20
    r20, _ = run(["--input", "/tmp/t_el.csv", "--episodes", "/tmp/t_few.csv", *reg[:5], "pooled", *reg[6:],
                  "--power-draws", "5", "--min-episodes", "19"])
    assert r20["lc"][0]["L_used"] == 20 and r20["lc"][0]["C_used"] == 18
    assert lcv(r20, "T1").startswith("DESCRIPTIVE ONLY: 18 C election(s) usable")      # pooled: C counts too
    incomplete = full.copy()
    incomplete.loc[incomplete.index[0], "anchor_date"] = "2025-12-20"            # its after-window runs past the file
    incomplete.to_csv("/tmp/t_incomplete.csv", index=False)
    ri, _ = run(["--input", "/tmp/t_el.csv", "--episodes", "/tmp/t_incomplete.csv", *reg, "--facts-only"])
    assert ri["lc"][0]["L_listed"] + ri["lc"][0]["C_listed"] == 39

    # 36. the minimum effect of interest is part of the verdict
    fe = ["--input", "/tmp/t_el.csv", "--episodes", "/tmp/t_reg.csv", *reg[:8], "--power-draws", "5", "--start", "2016-01-01"]
    assert lcv(run(fe + ["--mei-count", "1.5", "--mei-share", "0.10"])[0], "T1").startswith("SUPPORTED: H1")
    rbig, _ = run(fe + ["--mei-count", "3.0", "--mei-share", "0.50"])
    assert lcv(rbig, "T1") == "DETECTED, BELOW THE MINIMUM EFFECT OF INTEREST (up)", lcv(rbig, "T1")
    assert lcv(rbig, "T2") == "DETECTED, BELOW THE MINIMUM EFFECT OF INTEREST (down)", lcv(rbig, "T2")
    assert rbig["facts"]["mei_count"] == 3.0 and rbig["facts"]["mei_share"] == 0.5
    keep_mei = (S.MEI_COUNT, S.MEI_SHARE)
    S.MEI_COUNT, S.MEI_SHARE = 1.5, 0.10
    for value, ok in ((np.log(1.50), True), (np.log(1.49), False), (np.log(0.67), True), (np.log(0.68), False),
                      (np.log(0.50), True), (0.0, False)):
        assert S.meets_mei("Y1", value) is ok, value
    for value, ok in ((0.10, True), (-0.10, True), (0.099, False), (-0.2, True)):
        assert S.meets_mei("RATIO", value) is ok, value
    S.MEI_COUNT, S.MEI_SHARE = keep_mei
    assert "must be 1 or more" in stopped(fe + ["--mei-count", "0.5"])

    # 37. a fall in recorded protest is never "supported: H2" when any L election in the run had an outage
    make("/tmp/t_fall.csv", ["--elections", "--l-fall"], ep="/tmp/t_fall_ep.csv")
    fall = pd.read_csv("/tmp/t_fall_ep.csv", dtype=str, keep_default_na=False)
    fall = fall[fall["class"].isin(["L", "C"])].copy()
    under = "INSUFFICIENT EVIDENCE: recorded protest fell; this cannot be separated from under-recording"
    fl = ["--input", "/tmp/t_fall.csv", *reg, "--power-draws", "5"]
    for kind in ("full outage", "mobile outage", "regional outage"):
        fall.assign(type=np.where(fall["class"] == "L", kind, "none")).to_csv("/tmp/t_fall_o.csv", index=False)
        r_, _ = run(fl + ["--episodes", "/tmp/t_fall_o.csv"])
        assert lcv(r_, "T1") == under, (kind, lcv(r_, "T1"))
        assert next(x for x in r_["verdicts"] if x["group"] == "L-C" and x["test"] == "T1")["direction"] == "down"
    for kind in ("platform block", "throttling"):
        fall.assign(type=np.where(fall["class"] == "L", kind, "none")).to_csv("/tmp/t_fall_p.csv", index=False)
        assert lcv(run(fl + ["--episodes", "/tmp/t_fall_p.csv"])[0], "T1").startswith("SUPPORTED: H2 suppression"), kind
    onebad = fall.assign(type=np.where(fall["class"] == "L", "platform block", "none"))
    onebad.loc[onebad.index[onebad["class"] == "L"][0], "type"] = "Mobile Outage "       # one outage among twenty
    onebad.to_csv("/tmp/t_fall_1.csv", index=False)
    assert lcv(run(fl + ["--episodes", "/tmp/t_fall_1.csv"])[0], "T1") == under
    r_, _ = run(fl + ["--episodes", "/tmp/t_fall_1.csv", "--lc-filter", "type=platform block"])   # filtered out: allowed
    assert lcv(r_, "T1").startswith("SUPPORTED: H2 suppression") and r_["lc"][0]["L_used"] == 19
    # a rise is unaffected by the outage rule
    assert lcv(run(["--input", "/tmp/t_el.csv", "--episodes", "/tmp/t_reg.csv", *reg, "--power-draws", "5"])[0],
               "T1").startswith("SUPPORTED: H1")

    # 38. consistency guards on the election list
    gfo = ["--input", "/tmp/t_el_null.csv", *reg, "--facts-only"]
    def guard_case(change, tag):
        d = full.copy()
        change(d)
        d.to_csv(f"/tmp/t_g_{tag}.csv", index=False)
        return gfo + ["--episodes", f"/tmp/t_g_{tag}.csv"]
    a0, a1 = full.index[0], full.index[1]
    base_day = pd.Timestamp(full.loc[a0, "anchor_date"])
    def near(d, days):
        d.loc[a1, "anchor_date"] = (base_day + pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    msg = stopped(guard_case(lambda d: near(d, 55), "gap55"))
    assert "less than 56 days apart" in msg and full.loc[a0, "episode_id"] in msg and full.loc[a1, "episode_id"] in msg
    run(guard_case(lambda d: near(d, 56), "gap56"))                               # exactly 56 days: allowed
    def amb_near(d):                                                               # the rule covers rows of any status
        near(d, 30)
        d.loc[a1, "status"] = "ambiguous"
    assert "less than 56 days apart" in stopped(guard_case(amb_near, "gapamb"))
    def standing(d, status):
        d.loc[a0, ["timing", "status"]] = ["standing", status]
    assert "standing" in stopped(guard_case(lambda d: standing(d, "included"), "st1"))
    r_, _ = run(guard_case(lambda d: standing(d, "ambiguous"), "st2"))
    assert r_["lc"][0]["L_listed"] == 19
    def odd_type(d, value):
        d.loc[a0, "type"] = value
    assert "type outside" in stopped(guard_case(lambda d: odd_type(d, "outage"), "ty1"))
    assert "type outside" in stopped(guard_case(lambda d: odd_type(d, ""), "ty2"))
    run(guard_case(lambda d: odd_type(d, " Platform Block"), "ty3"))              # case and spaces are ignored

    # 39. the registered polling-day period: rows outside it are left out and listed in the run facts
    rper, _ = run(gfo + ["--episodes", "/tmp/t_reg.csv", "--anchor-from", "2018-01-01", "--anchor-to", "2024-12-31"])
    chk = rper["facts"]["election_list_checks"]
    out_ids = set(full[(full["anchor_date"] < "2018-01-01") | (full["anchor_date"] > "2024-12-31")]["episode_id"])
    assert chk["rows_outside_anchor_period"] == 16 == len(out_ids) and set(chk["ids_outside_anchor_period"]) == out_ids
    assert chk["anchor_from"] == "2018-01-01" and rper["lc"][0]["L_listed"] + rper["lc"][0]["C_listed"] == 24
    rall_, _ = run(gfo + ["--episodes", "/tmp/t_reg.csv"])
    assert rall_["facts"]["election_list_checks"]["rows_outside_anchor_period"] == 0
    assert rall_["facts"]["election_list_checks"]["earliest_anchor_listed"] == full["anchor_date"].min()

    # 40. each L-C test row says how many elections it used; an election with no protest or riot in
    # its windows has no riot share and drops out of T2 only
    rq, _ = run(["--input", "/tmp/t_el.csv", "--episodes", "/tmp/t_reg.csv", *reg, "--power-draws", "5"])
    assert all(x["elections_used"] == "20 L, 20 C" for x in rq["verdicts"] if x["group"] == "L-C")
    dq = pd.read_csv("/tmp/t_el.csv", dtype=str)
    row = full[full["class"] == "C"].iloc[0]
    wk, day = pd.to_datetime(dq["WEEK"]), pd.Timestamp(row["anchor_date"])
    hide = (dq["COUNTRY"] == row["country"]) & (wk >= day - pd.Timedelta(days=40)) & \
        (wk <= day + pd.Timedelta(days=35)) & dq["EVENT_TYPE"].isin(["Protests", "Riots"])
    dq[~hide].to_csv("/tmp/t_quiet_el.csv", index=False)
    rq2, _ = run(["--input", "/tmp/t_quiet_el.csv", "--episodes", "/tmp/t_reg.csv", *reg, "--power-draws", "5"])
    usedq = {x["test"]: x["elections_used"] for x in rq2["verdicts"] if x["group"] == "L-C"}
    assert usedq == {"T1": "20 L, 20 C", "T2": "20 L, 19 C", "T3": "20 L, 20 C"}, usedq
    print("all 40 checks passed")


if __name__ == "__main__":
    main()
