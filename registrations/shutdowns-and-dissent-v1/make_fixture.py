#!/usr/bin/env python3
"""Synthetic fixture for the shutdowns-and-dissent study.

Writes a CSV with the column names of ACLED's aggregated weekly product and
INVENTED values. No real ACLED row, count, place name or date pattern is used.
Countries and regions are fictional. Every ID starts with "SYN-".

Usage:
    python3 make_fixture.py --out fixture.csv --episodes-out episodes_fixture.csv
    python3 make_fixture.py --out fixture_null.csv --episodes-out episodes_fixture.csv --no-effects
Options added for version 0.4 (the default output is unchanged, byte for byte):
    --week-format dmy     write WEEK as day-month-year text, e.g. 21-April-2001
    --opposite            plant effects in the direction opposite to the hypotheses
    --two-country         add exam-timed episodes in the second invented country
    --negative-controls   add class-N episodes (no restriction) in the second invented country
Options added for version 0.5:
    --elections           eight invented countries, each with five elections: classes L (with a
                          restriction) and C (without), an anchor_date column, an election-season rise
                          in every election, and extra effects planted in L only
    --effect-both         with --elections: plant the extra effects in C elections too
    --l-type TYPE         with --elections: the restriction type written for L rows (default
                          "full outage"; must be one of the five registered types)
    --l-fall              with --elections: L elections get a fall in peaceful protest, not a rise
"""
import argparse
import numpy as np
import pandas as pd

SEED_DEFAULT = 20261111
COUNTRIES = {"Synthia": 12, "Fixtureland": 8}
# (event_type, sub_event_type, disorder_type, mean events per admin1-week, first year present)
SUBTYPES = [
    ("Protests", "Peaceful protest", "Demonstrations", 0.90, 2015),
    ("Protests", "Protest with intervention", "Demonstrations", 0.12, 2015),
    ("Protests", "Excessive force against protesters", "Demonstrations", 0.02, 2015),
    ("Riots", "Violent demonstration", "Demonstrations", 0.25, 2015),
    ("Riots", "Mob violence", "Political violence", 0.40, 2015),
    ("Violence against civilians", "Abduction/forced disappearance", "Political violence", 0.04, 2015),
    ("Strategic developments", "Arrests", "Strategic developments", 0.03, 2019),  # appears late on purpose
    ("Battles", "Armed clash", "Political violence", 0.30, 2015),
]
# Fictional episodes for Synthia. class P = politically triggered, E = exam-timed.
EPISODES = [
    ("FX-P1", "Synthia", "P", "outage", "2018-03-13", "2018-03-14"),
    ("FX-P2", "Synthia", "P", "platform block", "2020-08-04", "2020-08-06"),
    ("FX-P3", "Synthia", "P", "outage", "2022-05-17", "2022-05-17"),
    ("FX-P4", "Synthia", "P", "platform block", "2024-02-20", "2024-02-22"),
    ("FX-E1", "Synthia", "E", "platform block", "2019-10-08", "2019-10-25"),
    ("FX-E2", "Synthia", "E", "platform block", "2021-10-05", "2021-10-22"),
    ("FX-E3", "Synthia", "E", "platform block", "2023-10-10", "2023-10-27"),
]
# Planted effects (multipliers on the national rate), P episodes in Synthia only:
PLANT = {"Peaceful protest": ("after", 2.5), "Protest with intervention": ("during_after", 4.0),
         "Excessive force against protesters": ("during_after", 4.0)}
# Effects against the hypotheses around class-P episodes: fewer peaceful protests (suppression,
# not backfire), far fewer riots (no substitution), less intervention (no cover for repression).
PLANT_OPPOSITE = {"Peaceful protest": ("after", 0.3),
                  "Protest with intervention": ("during_after", 0.08),
                  "Excessive force against protesters": ("during_after", 0.08),
                  "Violent demonstration": ("after", 0.08), "Mob violence": ("after", 0.08)}
# Second invented country: exam-timed episodes in a different season, and negative controls
# (class N: the first country's exam weeks, where the second country had no restriction).
EPISODES_SECOND = [
    ("FL-E1", "Fixtureland", "E", "platform block", "2018-05-08", "2018-05-25"),
    ("FL-E2", "Fixtureland", "E", "platform block", "2020-05-05", "2020-05-22"),
    ("FL-E3", "Fixtureland", "E", "platform block", "2022-05-10", "2022-05-27"),
]
EPISODES_NEGATIVE = [
    ("FL-N1", "Fixtureland", "N", "none", "2019-10-08", "2019-10-25"),
    ("FL-N2", "Fixtureland", "N", "none", "2021-10-05", "2021-10-22"),
    ("FL-N3", "Fixtureland", "N", "none", "2023-10-10", "2023-10-27"),
]
# Elections (version 0.5). Six more invented countries; every country votes in odd years.
MORE_COUNTRIES = {"Mockovia": 10, "Testonia": 9, "Samplestan": 11, "Demoland": 7, "Placebia": 10, "Nullmark": 8}
ELECTION_YEARS = [2017, 2019, 2021, 2023, 2025]
# every election, L or C: protest rises in the four weeks from the polling week
ELECTION_SEASON = {"Peaceful protest": 1.6, "Protest with intervention": 1.6, "Violent demonstration": 1.3}
# on top of that, in elections with a restriction (L) only:
PLANT_L = {"Peaceful protest": 2.5, "Protest with intervention": 4.0, "Excessive force against protesters": 4.0}
PLANT_L_FALL = {"Peaceful protest": 0.3}
MISSING_WEEKS = ["2016-07-02", "2016-07-09", "2021-01-02"]  # whole weeks with no rows at all


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--episodes-out", required=True)
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT)
    ap.add_argument("--no-effects", action="store_true", help="null fixture: plant nothing")
    ap.add_argument("--week-format", choices=["iso", "dmy"], default="iso")
    ap.add_argument("--opposite", action="store_true")
    ap.add_argument("--two-country", action="store_true")
    ap.add_argument("--negative-controls", action="store_true")
    ap.add_argument("--elections", action="store_true")
    ap.add_argument("--effect-both", action="store_true")
    ap.add_argument("--l-type", default="full outage")
    ap.add_argument("--l-fall", action="store_true")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    weeks = pd.date_range("2015-01-03", "2025-12-27", freq="7D")  # Saturdays
    assert all(w.weekday() == 5 for w in weeks)
    listed = EPISODES + (EPISODES_SECOND if a.two_country else []) + \
        (EPISODES_NEGATIVE if a.negative_controls else [])
    plant = PLANT_OPPOSITE if a.opposite else PLANT
    ep = pd.DataFrame(listed, columns=["episode_id", "country", "class", "type", "start_date", "end_date"])
    countries = dict(COUNTRIES)
    elections = []
    if a.elections:
        countries.update(MORE_COUNTRIES)
        ep["anchor_date"] = ""
        for k, country in enumerate(countries):
            for j, year in enumerate(ELECTION_YEARS):
                poll = pd.Timestamp(year=year, month=4 + k, day=14)
                cls = "L" if (k + j) % 2 == 0 else "C"
                start = poll - pd.Timedelta(days=1) if cls == "L" else poll
                end = poll + pd.Timedelta(days=3) if cls == "L" else poll
                elections.append((f"EL-{k + 1:02d}-{year}", country, cls,
                                  a.l_type if cls == "L" else "none", start.strftime("%Y-%m-%d"),
                                  end.strftime("%Y-%m-%d"), poll.strftime("%Y-%m-%d")))
        ep = pd.concat([ep, pd.DataFrame(elections, columns=list(ep.columns))], ignore_index=True)
    ep.to_csv(a.episodes_out, index=False)
    w0 = weeks[0]
    idx = lambda d: (pd.Timestamp(d) - w0).days // 7
    rows = []
    for country, n_adm in countries.items():
        # slow national factor: seasonal + autocorrelated noise, shared by sub-types
        ar = np.zeros(len(weeks))
        for t in range(1, len(weeks)):
            ar[t] = 0.6 * ar[t - 1] + rng.normal(0, 0.25)
        season = 0.25 * np.sin(2 * np.pi * (weeks.dayofyear.values / 365.25))
        factor = np.exp(ar + season)
        mult = {s[1]: np.ones(len(weeks)) for s in SUBTYPES}
        if country == "Synthia" and not a.no_effects:
            for _, e in ep[(ep["class"] == "P") & (ep["country"] == country)].iterrows():
                s, t = idx(e.start_date), idx(e.end_date)
                for sub, (when, m) in plant.items():
                    lo = t + 1 if when == "after" else s
                    mult[sub][lo:t + 5] *= m
        for _, cname, cls, _, _, _, poll in elections:
            if cname != country:
                continue
            lo = idx(poll)
            for sub, m in ELECTION_SEASON.items():
                mult[sub][lo:lo + 4] *= m
            if (cls == "L" or a.effect_both) and not a.no_effects:
                for sub, m in (PLANT_L_FALL if a.l_fall else PLANT_L).items():
                    mult[sub][lo:lo + 4] *= m
        adm_w = rng.dirichlet(np.ones(n_adm) * 2.0) * n_adm
        for et, sub, dis, rate, first_year in SUBTYPES:
            for a_i in range(n_adm):
                lam = rate * adm_w[a_i] * factor * mult[sub]
                ev = rng.poisson(lam)
                for t in np.nonzero(ev)[0]:  # zero weeks have no row, as in an aggregated product
                    wk = weeks[t]
                    if wk.year < first_year or wk.strftime("%Y-%m-%d") in MISSING_WEEKS:
                        continue
                    rows.append((wk.strftime("%Y-%m-%d"), "Synthetic Region", country,
                                 f"{country} Province {a_i + 1:02d}", et, sub, int(ev[t]),
                                 int(rng.binomial(ev[t], 0.05)), int(rng.integers(1000, 500000)), dis,
                                 round(float(rng.uniform(-5, 5)), 4), round(float(rng.uniform(30, 40)), 4)))
    df = pd.DataFrame(rows, columns=["WEEK", "REGION", "COUNTRY", "ADMIN1", "EVENT_TYPE", "SUB_EVENT_TYPE",
                                     "EVENTS", "FATALITIES", "POPULATION_EXPOSURE", "DISORDER_TYPE",
                                     "CENTROID_LATITUDE", "CENTROID_LONGITUDE"])
    df = df.sample(frac=1.0, random_state=a.seed).reset_index(drop=True)
    df.insert(10, "ID", [f"SYN-{i:07d}" for i in range(len(df))])
    if a.week_format == "dmy":  # the real product's text format: day, full month name, year
        w = pd.to_datetime(df["WEEK"])
        df["WEEK"] = w.dt.day.astype(str) + "-" + w.dt.month_name() + "-" + w.dt.year.astype(str)
    df.to_csv(a.out, index=False)
    print(f"wrote {len(df)} synthetic rows to {a.out}; seed {a.seed}; effects planted: {not a.no_effects}")


if __name__ == "__main__":
    main()
