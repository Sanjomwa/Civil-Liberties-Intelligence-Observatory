#!/usr/bin/env python3
"""Shutdowns-and-dissent event study: analysis code with a fixed output contract.

Written and tested against a SYNTHETIC fixture only (see make_fixture.py). Under the
"AI writes, Sam runs" protocol, Sam runs this on real data himself and pastes back only
what this script prints.

OUTPUT CONTRACT. The script prints ONLY:
  * a run-facts block (row counts, date range, hashes, fixture-or-real flag, settings);
  * per-episode structural counts (window weeks, comparison periods used) - no event totals;
  * pooled test statistics, placebo ranks, p-values, verdicts;
  * pooled lead/lag change ratios, averaged across episodes, rounded;
  * power figures.
It never prints weekly series, baselines, levels, sub-national tables or per-episode outcome
rows. Every table goes through guard(), which refuses anything that looks like one row per week.

Countries, classes and episodes come only from the arguments and the episode list. Nothing in
this file names a country.

The primary test from version 0.5.0 compares elections with a restriction (class L) against
elections without one (class C), by randomization inference on the L/C labels. See README 10.

Usage:
    python3 shutdowns_study.py --input data.csv --episodes episodes.csv --country NAME[,NAME...]
    add --facts-only for the first run on any new input (no test is computed)
Inputs are arguments, so the same code runs on the fixture and on real data unchanged.
"""
import argparse
import hashlib
import itertools
import json
import math
import re
import sys

import numpy as np
import pandas as pd

VERSION = "0.5.1"
REQUIRED = ["WEEK", "COUNTRY", "ADMIN1", "EVENT_TYPE", "SUB_EVENT_TYPE", "EVENTS", "ID"]
EPISODE_REQUIRED = ["episode_id", "country", "class", "start_date", "end_date"]
ANCHORED = ("L", "C")      # election classes: outcome windows are measured from anchor_date (polling day)
MIN_MATCHED = 20           # class P: fewer matched placebo positions than this is "not testable"
WEEK_FORMATS = [("YYYY-MM-DD", "%Y-%m-%d"), ("D-Month-YYYY", "%d-%B-%Y")]
CLASSES = {"E": "exam-timed", "P": "politically triggered", "N": "negative control (no documented restriction)",
           "L": "election with a restriction", "C": "control election (no restriction)"}
LEAD_WEEKS = 4
LAG_WEEKS = 4
COMPARISON_SHIFTS = [-156, -104, -52, 52, 104, 156]  # same season, up to three years either side
MULTIPLIERS = [0.5, 0.67, 1.0, 1.5, 2.0, 3.0]
SHARE_SHIFTS = [-0.10, 0.10]   # power for the riot share (T2) at the registered minimum effect
# Restriction types for class L, in order of severity (the election-list procedure records the
# first that applies). The first three cut what gets recorded as well as what people can do.
TYPES = ["full outage", "mobile outage", "regional outage", "throttling", "platform block"]
OUTAGE_TYPES = set(TYPES[:3])
MIN_GAP_DAYS = 56              # two elections in one country closer than this share window weeks
GATE = ("L-C", "T1", "three conditions", "x1.5")   # the power-gate figure (see README 11.3)
EXACT_LIMIT = 100_000      # enumerate every placebo set when there are at most this many
MIN_SETS_FOR_POWER = 20    # below this, power is "not measurable at this size"
# Empty-week stop, judged on the WHOLE input file: a week counts as missing only when no country
# in the file has a row for it. (The product has no row for a country-week without events, so a
# quiet country's own empty weeks are reported in the run facts and never stop the run.)
MAX_EMPTY_SHARE = 0.02     # more than this share of weeks in the range missing from the file
MAX_EMPTY_RUN = 4          # this many consecutive weeks missing from the file
ALPHA = 0.05
TOL = 1e-12

COUNT_OUTCOMES = ["Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "YB"]
# YB (armed clashes) is a reporting check, not a hypothesis: a restriction on the internet has no
# obvious reason to change how much fighting there is, so if YB moves with the restriction, the
# likelier explanation is that fewer events of every kind were recorded while people were offline.
REPORTING_CHECK = "YB"
# Primary tests (one per hypothesis family; Holm applied across these three). Every test is
# two-sided. "up" is the predicted direction of T2 and T3; T1 carries two rival hypotheses.
PRIMARY = [
    {"test": "T1", "outcome": "Y1", "measure": "after", "plant": "Y1",
     "up": "H1 backfire", "down": "H2 suppression", "expected": "either (H1 up, H2 down)"},
    {"test": "T2", "outcome": "RATIO", "measure": "after", "plant": "Y3",
     "up": "H3 substitution", "down": None, "expected": "up"},
    {"test": "T3", "outcome": "Y2", "measure": "da", "plant": "Y2",
     "up": "H4 cover for repression", "down": None, "expected": "up"},
]
EXPLORATORY = [("Y3", "after"), ("Y4", "da"), ("Y5", "da"), ("Y6", "after"), ("YB", "da")]
LEADLAG = [f"lead{j - LEAD_WEEKS}" for j in range(LEAD_WEEKS)] + [f"lag+{j + 1}" for j in range(LAG_WEEKS)]


# ----------------------------------------------------------------------------- guard
class ContractViolation(Exception):
    pass


FORBIDDEN_COLS = {"week", "date", "week_start", "events", "fatalities", "level", "baseline", "count", "admin1"}
DATE_RE = re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b")
MAX_ROWS = 40


def guard(name, df):
    """Refuse any table that could expose weekly rows, levels or dates. Returns df if safe."""
    for c in df.columns:
        if str(c).lower() in FORBIDDEN_COLS:
            raise ContractViolation(f"{name}: column '{c}' is not allowed in output")
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            raise ContractViolation(f"{name}: date column '{c}' is not allowed in output")
        if not pd.api.types.is_numeric_dtype(df[c]) and df[c].astype(str).str.contains(DATE_RE).any():
            raise ContractViolation(f"{name}: column '{c}' contains calendar dates")
    if len(df) > MAX_ROWS:
        raise ContractViolation(f"{name}: {len(df)} rows; tables this long may be one row per week")
    return df


def emit(name, df):
    guard(name, df)
    print(f"\n## {name}")
    print(df.to_string(index=False))


# ----------------------------------------------------------------------------- loading
def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_week(col):
    """Parse WEEK strictly, in one of the two known formats. Never guesses."""
    for label, fmt in WEEK_FORMATS:
        try:
            return pd.to_datetime(col.str.strip(), format=fmt, errors="raise"), label
        except (ValueError, TypeError):
            continue
    sys.exit("WEEK is in neither known format (" + ", ".join(l for l, _ in WEEK_FORMATS) +
             "); stopping before any analysis")


def parse_day(text, name):
    try:
        return pd.Timestamp(pd.to_datetime(text, format="%Y-%m-%d", errors="raise"))
    except (ValueError, TypeError):
        sys.exit(f"{name} must be YYYY-MM-DD; got '{text}'")


def load(path):
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip().upper() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        sys.exit(f"input is missing required columns: {missing}")
    df["WEEK"], week_format = parse_week(df["WEEK"])
    df["EVENTS"] = pd.to_numeric(df["EVENTS"], errors="raise").astype(int)
    return df, week_format


def data_kind(df):
    syn = df["ID"].astype(str).str.startswith("SYN-")
    if syn.all():
        return "fixture"
    if not syn.any():
        return "real"
    sys.exit("input mixes synthetic (SYN-) and other IDs; refusing to run")


def saturday_on_or_after(day):
    return day + pd.Timedelta(days=(5 - day.weekday()) % 7)


def saturday_on_or_before(day):
    return day - pd.Timedelta(days=(day.weekday() - 5) % 7)


def build_series(d, w0, w1):
    """Weekly national series for one country over the week range w0..w1 (both Saturdays)."""
    weeks = pd.date_range(w0, w1, freq="7D")
    T = len(weeks)
    pos = ((d["WEEK"] - w0).dt.days // 7).to_numpy()
    sub, et, ev = d["SUB_EVENT_TYPE"].to_numpy(), d["EVENT_TYPE"].to_numpy(), d["EVENTS"].to_numpy()

    def tot(mask):
        return np.bincount(pos[mask], weights=ev[mask], minlength=T)

    m1 = sub == "Peaceful protest"
    m2 = np.isin(sub, ["Protest with intervention", "Excessive force against protesters"])
    m3 = et == "Riots"
    y = {"Y1": tot(m1), "Y2": tot(m2), "Y3": tot(m3),
         "Y4": tot(sub == "Abduction/forced disappearance"), "Y5": tot(sub == "Arrests"),
         "YB": tot(et == "Battles")}
    spread = d[m1 | m2 | m3].assign(p=pos[m1 | m2 | m3]).groupby("p")["ADMIN1"].nunique()
    y6 = np.zeros(T)
    y6[spread.index.to_numpy()] = spread.to_numpy()
    y["Y6"] = y6
    n_empty, longest = empty_weeks(d["WEEK"], w0, w1)
    return y, weeks, n_empty, longest


def empty_weeks(week_col, w0, w1):
    """Weeks in w0..w1 (Saturdays) with no row in week_col: (how many, longest consecutive run)."""
    T = (w1 - w0).days // 7 + 1
    if T <= 0:
        return 0, 0
    pos = np.unique((week_col - w0).dt.days // 7)
    has_rows = np.zeros(T, dtype=bool)
    has_rows[pos[(pos >= 0) & (pos < T)]] = True
    longest = run = 0
    for h in has_rows:
        run = 0 if h else run + 1
        longest = max(longest, run)
    return int(T - has_rows.sum()), int(longest)


# ----------------------------------------------------------------------------- statistics
def thin(counts, mult, rng):
    """Scale counts by mult without rounding: binomial thinning below 1, added Poisson above."""
    c = np.asarray(counts)
    if mult == 1:
        return c.astype(float)
    if mult < 1:
        return rng.binomial(c.astype(int), mult).astype(float)
    return c + rng.poisson((mult - 1.0) * c)


class Engine:
    """One country's series. Gives the comparison-adjusted statistics for any start week and
    episode length. Real episodes, placebo sets and power all read from the same code."""

    def __init__(self, y, T, real_spans):
        self.y, self.T = y, T
        self.cs = {k: np.concatenate([[0.0], np.cumsum(np.log1p(v))]) for k, v in y.items()}
        self.raw = {k: np.concatenate([[0.0], np.cumsum(v)]) for k, v in y.items()}
        blocked = np.zeros(T + 1, dtype=int)  # weeks inside any listed episode's full window
        for s, e in real_spans:
            lo, hi = max(0, s - LEAD_WEEKS), min(T, e + 1 + LAG_WEEKS)
            if lo < hi:
                blocked[lo:hi] = 1
        self.bcs = np.concatenate([[0], np.cumsum(blocked[:T])])
        # first week each outcome is present at all; windows before it are unusable for that outcome
        self.first = {k: (int(np.nonzero(v)[0][0]) if np.any(v) else T) for k, v in y.items()}
        self.cache = {}

    def _mean(self, cs, a, b):
        return (cs[b] - cs[a]) / (b - a)

    def _valid(self, s, dur):
        return s - LEAD_WEEKS >= 0 and s + dur + LAG_WEEKS <= self.T

    def _clear(self, s, dur):
        a, b = s - LEAD_WEEKS, s + dur + LAG_WEEKS
        return self.bcs[b] - self.bcs[a] == 0

    def _ratio(self, a, b):
        if a < max(self.first["Y1"], self.first["Y3"]):
            return np.nan
        num = self.raw["Y3"][b] - self.raw["Y3"][a]
        den = (self.raw["Y1"][b] - self.raw["Y1"][a]) + num
        return num / den if den > 0 else np.nan

    def _raw_stats(self, s, dur):
        """Unadjusted statistics for a window starting at week s lasting dur weeks."""
        L0, L1, D1, A1 = s - LEAD_WEEKS, s, s + dur, s + dur + LAG_WEEKS
        out = {}
        for k in COUNT_OUTCOMES:
            cs = self.cs[k]
            if L0 < self.first[k]:
                for m in ["after", "da", "pre"] + LEADLAG:
                    out[(k, m)] = np.nan
                continue
            lead = self._mean(cs, L0, L1)
            out[(k, "after")] = self._mean(cs, D1, A1) - lead
            out[(k, "da")] = self._mean(cs, L1, A1) - lead
            out[(k, "pre")] = self._mean(cs, L1 - 2, L1) - self._mean(cs, L0, L0 + 2)
            for j in range(LEAD_WEEKS):
                out[(k, f"lead{j - LEAD_WEEKS}")] = (cs[L0 + j + 1] - cs[L0 + j]) - lead
            for j in range(LAG_WEEKS):
                out[(k, f"lag+{j + 1}")] = (cs[D1 + j + 1] - cs[D1 + j]) - lead
        out[("RATIO", "after")] = self._ratio(D1, A1) - self._ratio(L0, L1)
        out[("RATIO", "da")] = self._ratio(L1, A1) - self._ratio(L0, L1)
        out[("RATIO", "pre")] = self._ratio(L1 - 2, L1) - self._ratio(L0, L0 + 2)
        return out

    def adjusted(self, s, dur, is_real=False):
        """Statistics minus the mean of the same statistics in same-season comparison windows.
        Returns (stats dict, number of comparison windows) or (None, 0) if unusable."""
        key = (s, dur, is_real)
        if key in self.cache:
            return self.cache[key]
        res = (None, 0)
        if self._valid(s, dur) and (is_real or self._clear(s, dur)):
            # Comparison windows are NOT screened for listed episodes. Every position, real or
            # placebo, is compared with its same-season neighbours in exactly the same way; that
            # symmetry is what makes the placebo a valid reference. The cost: if a neighbour
            # holds another real episode, a true effect is understated.
            comps = [self._raw_stats(s + sh, dur) for sh in COMPARISON_SHIFTS if self._valid(s + sh, dur)]
            if comps:
                own = self._raw_stats(s, dur)
                adj = {}
                for k in own:
                    cvals = [c[k] for c in comps if not np.isnan(c[k])]
                    adj[k] = own[k] - np.mean(cvals) if cvals and not np.isnan(own[k]) else np.nan
                res = (adj, len(comps))
        self.cache[key] = res
        return res

    def planted_share_shift(self, s, dur, shift, rng):
        """Change in the riot-share statistic at window s when riots in the target weeks are
        thinned or topped up so that the share moves by `shift`. Returns 0 where the share cannot
        move that way (no peaceful protest in the weeks, or a fall asked of a share of zero)."""
        a, A1 = s + dur, s + dur + LAG_WEEKS
        old = self._ratio(a, A1)
        if np.isnan(old):
            return 0.0
        prot = self.raw["Y1"][A1] - self.raw["Y1"][a]
        yv = self.y["Y3"][a:A1]
        target = min(max(old + shift, 0.0), 0.99)
        if prot <= 0 or target == old:
            return 0.0
        want = target * prot / (1.0 - target)          # riot total that gives the target share
        have = float(yv.sum())
        if want < have:
            new = rng.binomial(yv.astype(int), want / have).astype(float)
        else:
            new = yv + rng.poisson((want - have) / len(yv), size=len(yv))
        return float(new.sum() / (prot + new.sum()) - old)

    def planted_delta(self, s, dur, t, mult, rng):
        """Change in test t's statistic at window s when its outcome is scaled by mult in the
        test's target weeks. Counts are thinned (below 1) or topped up (above 1), never rounded."""
        if mult == 1:
            return 0.0
        L1, D1, A1 = s, s + dur, s + dur + LAG_WEEKS
        a = D1 if t["measure"] == "after" else L1
        yv = self.y[t["plant"]][a:A1]
        new = thin(yv, mult, rng)
        if t["outcome"] == "RATIO":
            old = self._ratio(a, A1)
            den = (self.raw["Y1"][A1] - self.raw["Y1"][a]) + new.sum()
            return (new.sum() / den if den > 0 else np.nan) - old
        return float(np.mean(np.log1p(new)) - np.mean(np.log1p(yv)))

    def lead_level(self, s):
        """Mean of log(1 + Y1) over the lead weeks before week s. Used only to match class-P
        placebo weeks to the episode's own pre-episode level; never printed."""
        return self._mean(self.cs["Y1"], s - LEAD_WEEKS, s)

    def placebo_starts(self, s, dur, cls, matched=False):
        """Eligible placebo start weeks for one listed episode, in this country's series only.
        Exam-timed (E) and negative-control (N) episodes keep their season (whole-year shifts);
        politically triggered ones may fall anywhere eligible, or, with matched=True, only in
        weeks whose lead level is in the same within-country tercile as the episode's own.
        The real position is the last entry: it is itself a member of the reference set."""
        if cls in ("E", "N"):
            cand = [s + 52 * j for j in range(-60, 61) if j != 0]
        else:
            cand = range(LEAD_WEEKS, self.T - dur - LAG_WEEKS + 1)
        ok = [c for c in cand if self.adjusted(c, dur)[0] is not None]
        if matched and cls == "P" and ok and s - LEAD_WEEKS >= 0:
            levels = np.array([self.lead_level(c) for c in ok])
            cuts = np.quantile(levels, [1 / 3, 2 / 3])
            own = np.searchsorted(cuts, self.lead_level(s), side="right")
            ok = [c for c, lv in zip(ok, levels) if np.searchsorted(cuts, lv, side="right") == own]
        return ok + [s]


def rowmean(M):
    """Mean across columns ignoring NaN; NaN where a row has no value."""
    ok = ~np.isnan(M)
    n = ok.sum(axis=1)
    return np.where(n > 0, np.where(ok, M, 0.0).sum(axis=1) / np.maximum(n, 1), np.nan)


def pooled(values):
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    return float(v.mean()) if len(v) else np.nan


class Ref:
    """A placebo reference distribution for one pooled statistic.
    exact=True: every possible placebo set is present once (the real set among them), so
    p = rank / count. exact=False: random draws, so p = (1 + rank) / (draws + 1)."""

    def __init__(self, values, exact):
        self.values, self.exact = values, exact
        ok = values[~np.isnan(values)]
        self.n = len(ok)
        self.sorted = np.sort(ok)
        self.sorted_abs = np.sort(np.abs(ok))

    def rank(self, obs):
        """Number of reference sets at least as far from zero as obs."""
        return int(self.n - np.searchsorted(self.sorted_abs, abs(obs) - TOL, side="left"))

    def p(self, obs, replaces=None):
        """Two-sided p-value. In exact mode obs must be a member, or 'replaces' gives the
        member's value that obs stands in for (used when an effect is planted in a member)."""
        if np.isnan(obs) or self.n == 0:
            return np.nan
        k = self.rank(obs)
        if not self.exact:
            return (1 + k) / (self.n + 1)
        if replaces is not None:
            if np.isnan(replaces):
                return (1 + k) / (self.n + 1)
            k = k - int(abs(replaces) >= abs(obs) - TOL) + 1
        return k / self.n

    def share_below(self, obs):
        if np.isnan(obs) or self.n == 0:
            return np.nan
        return float(np.searchsorted(self.sorted, obs - TOL, side="left") / self.n)


def holm(pvals):
    order = np.argsort(pvals)
    adj, running = np.empty(len(pvals)), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvals) - rank) * pvals[i]))
        adj[i] = running
    return adj


def fmt_change(outcome, value):
    """Pooled change as a ratio for count outcomes, as a difference in share for the riot ratio."""
    if np.isnan(value):
        return "n/a"
    return f"{value:+.3f} (share)" if outcome == "RATIO" else f"x{np.exp(value):.2f}"


def fmt_p(p):
    return "n/a" if np.isnan(p) else f"{p:.4f}"


def direction(v):
    return "n/a" if np.isnan(v) else ("up" if v > 0 else "down" if v < 0 else "none")


class Group:
    """One group of episodes with its placebo reference sets. Members may sit in different
    countries; each member's placebo positions come from its own country's series."""

    def __init__(self, name, members, draws, rng, matched=False):
        self.name, self.members, self.n = name, members, len(members)
        self.cands = [m["eng"].placebo_starts(m["s"], m["dur"], m["cls"], matched) for m in members]
        self.sizes = [len(c) for c in self.cands]
        self.n_sets = math.prod(self.sizes)
        self.exact = self.n_sets <= EXACT_LIMIT
        self.usable = min(self.sizes) > 1
        if not self.usable:
            return
        if self.exact:  # every combination once; the real set (all last entries) is the last row
            grids = np.meshgrid(*[np.arange(k) for k in self.sizes], indexing="ij")
            self.idx = np.stack([g.ravel() for g in grids], axis=1)
        else:
            self.idx = np.stack([rng.integers(0, k, size=draws) for k in self.sizes], axis=1)
        self.method = f"exact, all {self.n_sets} sets" if self.exact else f"{draws} random draws"
        self._arr, self._mat = {}, {}

    def arr(self, i, key):
        """Member i's adjusted statistic at each of its candidate positions."""
        if (i, key) not in self._arr:
            m, c = self.members[i], self.cands[i]
            self._arr[(i, key)] = np.array(
                [m["eng"].adjusted(int(x), m["dur"], is_real=(j == len(c) - 1))[0][key]
                 for j, x in enumerate(c)], dtype=float)
        return self._arr[(i, key)]

    def mat(self, key):
        if key not in self._mat:
            self._mat[key] = np.column_stack([self.arr(i, key)[self.idx[:, i]] for i in range(self.n)])
        return self._mat[key]

    def ref(self, key, drop=None):
        M = self.mat(key)
        if drop is not None:
            M = np.delete(M, drop, axis=1)
        return Ref(rowmean(M), self.exact)

    def obs(self, key, drop=None):
        return pooled([m["adj"][key] for i, m in enumerate(self.members) if i != drop])


MEI_COUNT, MEI_SHARE = 1.5, 0.10  # set from --mei-count and --mei-share


def meets_mei(outcome, value):
    """Is the pooled change at least the minimum effect of interest? Counts: at least xMEI, or at
    most x(1/MEI) rounded to two places (x0.67 for 1.5). The riot share: at least MEI_SHARE in
    absolute value."""
    if np.isnan(value):
        return False
    if outcome == "RATIO":
        return abs(value) >= MEI_SHARE - TOL
    ratio = float(np.exp(value))
    return ratio >= MEI_COUNT - TOL or ratio <= round(1.0 / MEI_COUNT, 2) + TOL


LOO_MODE = "strict"  # set from --loo. strict: each leave-one-out keeps its sign AND p <= 0.05;
                     # sign: each leave-one-out keeps its sign only.


def decide(p_holm, obs, pre_obs, pre_ref, loo):
    """The four-part rule. loo is a list of (obs_j, p_j), one per left-out episode.
    Returns (fires, pretrend_flag, loo_ok). The caller reads the direction from obs."""
    p_pre = pre_ref.p(pre_obs) if pre_ref is not None else np.nan
    pre_flag = bool(not np.isnan(p_pre) and p_pre <= ALPHA and np.sign(pre_obs) == np.sign(obs))
    strict = LOO_MODE == "strict"
    loo_ok = len(loo) >= 2 and all(
        (not np.isnan(o)) and np.sign(o) == np.sign(obs)
        and (not strict or ((not np.isnan(p)) and p <= ALPHA)) for o, p in loo)
    fires = bool((not np.isnan(obs)) and obs != 0 and p_holm <= ALPHA and not pre_flag and loo_ok)
    return fires, pre_flag, bool(loo_ok)


# Power is reported under three rules. "three conditions" is Holm, pre-trend and leave-one-out;
# "full rule" adds the minimum effect of interest. At a true effect equal to the minimum, about
# half of all estimates fall below it, so "full rule" power there cannot much exceed one half.
RULE_LABELS = (("raw", "unadjusted 5%"), ("three", "three conditions"), ("full", "full rule"))


def power_block(g, power_draws, rng):
    """Share of planted placebo sets in which the rule fires in the planted direction.
    One test's outcome is scaled at a time; the other two tests are left as they are.
    x1.0 plants nothing, so its row is the false-positive rate on this series."""
    keys = [(t["outcome"], t["measure"]) for t in PRIMARY]
    prekeys = [(t["outcome"], "pre") for t in PRIMARY]
    refs = [g.ref(k) for k in keys]
    pre_refs = [g.ref(k) for k in prekeys]
    loo_refs = [[g.ref(k, drop=j) for j in range(g.n)] for k in keys] if g.n >= 2 else None
    hits = {(ti, m, rule): 0 for ti in range(3) for m in MULTIPLIERS for rule in ("raw", "three", "full")}
    for _ in range(power_draws):
        # a placebo set that is not the real one
        x = [int(rng.integers(0, k - 1)) for k in g.sizes]
        row = int(np.ravel_multi_index(x, g.sizes)) if g.exact else None
        vals = [np.array([g.arr(i, k)[x[i]] for i in range(g.n)]) for k in keys]
        pre_obs = [pooled([g.arr(i, k)[x[i]] for i in range(g.n)]) for k in prekeys]
        p_null = [refs[ti].p(pooled(vals[ti])) for ti in range(3)]
        for ti, t in enumerate(PRIMARY):
            for m in MULTIPLIERS:
                if m == 1:
                    planted = vals[ti]
                else:
                    planted = vals[ti] + np.array(
                        [g.members[i]["eng"].planted_delta(g.cands[i][x[i]], g.members[i]["dur"], t, m, rng)
                         for i in range(g.n)])
                o = pooled(planted)
                p = refs[ti].p(o, replaces=refs[ti].values[row] if g.exact else None)
                right_way = (not np.isnan(o)) and (m == 1 or (o > 0) == (m > 1))
                if np.isnan(p) or not right_way:
                    continue
                if p <= ALPHA:
                    hits[(ti, m, "raw")] += 1
                ps = np.array([1.0 if np.isnan(q) else q for q in p_null])
                ps[ti] = p
                if holm(ps)[ti] > ALPHA or g.n < 2:
                    continue
                loo = []
                for j in range(g.n):
                    r = loo_refs[ti][j]
                    oj = pooled(np.delete(planted, j))
                    loo.append((oj, r.p(oj, replaces=r.values[row] if g.exact else None)))
                fires, _, _ = decide(holm(ps)[ti], o, pre_obs[ti], pre_refs[ti], loo)
                hits[(ti, m, "three")] += int(fires)
                hits[(ti, m, "full")] += int(fires and meets_mei(t["outcome"], o))
    rows = []
    for ti, t in enumerate(PRIMARY):
        for rule, label in RULE_LABELS:
            row = {"group": g.name, "test": t["test"], "outcome": t["outcome"], "rule": label}
            for m in MULTIPLIERS:
                row[f"x{m}"] = f"{hits[(ti, m, rule)] / power_draws:.2f}"
            rows.append(row)
    return rows


# ----------------------------------------------------------------------------- L against C
def arrangements(is_l, strata, draws, rng):
    """Every way (or a random sample of ways) to re-assign the L labels, keeping the number of
    L in each stratum fixed. Returns (matrix of label rows, exact?, number of arrangements).
    In exact mode the real labelling is one of the rows."""
    groups = [np.flatnonzero(strata == g) for g in np.unique(strata)]
    count = math.prod(math.comb(len(ix), int(is_l[ix].sum())) for ix in groups)
    n = len(is_l)
    if count <= EXACT_LIMIT:
        per = [[c for c in itertools.combinations(ix, int(is_l[ix].sum()))] for ix in groups]
        rows = np.zeros((count, n), dtype=bool)
        for r, combo in enumerate(itertools.product(*per)):
            for part in combo:
                rows[r, list(part)] = True
        return rows, True, count
    rows = np.zeros((draws, n), dtype=bool)
    for ix in groups:
        base = is_l[ix]
        for r in range(draws):
            rows[r, ix] = rng.permutation(base)
    return rows, False, count


def lc_stat(values, rows, strata):
    """Mean change in L minus mean change in C, within each stratum, averaged over strata with
    weights equal to the number of L. With one stratum this is the plain difference in means.
    values may hold NaN (an episode unusable for this outcome); rows is a matrix of label rows."""
    num = np.zeros(len(rows))
    den = np.zeros(len(rows))
    for g in np.unique(strata):
        ix = np.flatnonzero((strata == g) & ~np.isnan(values))
        if len(ix) < 2:
            continue
        lab = rows[:, ix].astype(float)
        v = values[ix]
        n_l = lab.sum(axis=1)
        n_c = len(ix) - n_l
        ok = (n_l > 0) & (n_c > 0)
        sum_l = lab @ v
        d = np.where(ok, sum_l / np.maximum(n_l, 1) - (v.sum() - sum_l) / np.maximum(n_c, 1), 0.0)
        num += np.where(ok, n_l * d, 0.0)
        den += np.where(ok, n_l, 0.0)
    return np.where(den > 0, num / np.maximum(den, 1), np.nan)


class LCGroup:
    """Elections with a restriction (L) against elections without (C). Outcome windows are
    measured from polling day for both, and no within-country comparison years are used: the
    C elections are the comparison. The reference distribution permutes the L/C labels."""

    def __init__(self, members, design, draws, rng):
        self.design, self.draws, self.rng = design, draws, rng
        strata = np.array([m["stratum"] if design == "stratified" else "all" for m in members], dtype=object)
        is_l = np.array([m["cls"] == "L" for m in members])
        # a stratum is usable only if it holds at least one L and one C
        keep = np.array([is_l[strata == g].any() and (~is_l[strata == g]).any() for g in strata], dtype=bool) \
            if len(members) else np.zeros(0, dtype=bool)
        self.members = [m for m, k in zip(members, keep) if k]
        self.strata, self.is_l = strata[keep], is_l[keep]
        self.n_l, self.n_c = int(self.is_l.sum()), int((~self.is_l).sum())
        self.n_strata = len(set(self.strata))
        self.dropped = int((~keep).sum())
        self.usable = self.n_l >= 1 and self.n_c >= 1
        self._vals, self._drop = {}, {}
        if self.usable:
            self.rows, self.exact, self.count = arrangements(self.is_l, self.strata, draws, rng)
            self.method = f"exact, all {self.count} label arrangements" if self.exact \
                else f"{draws} random label arrangements"

    def values(self, key):
        if key not in self._vals:
            self._vals[key] = np.array([m["raw"][key] for m in self.members], dtype=float)
        return self._vals[key]

    def obs(self, values, labels=None):
        lab = self.is_l if labels is None else labels
        return float(lc_stat(values, lab[None, :], self.strata)[0])

    def ref(self, values):
        return Ref(lc_stat(values, self.rows, self.strata), self.exact)

    def without(self, j):
        """Strata and label arrangements with episode j removed (cached; depends only on j)."""
        if j not in self._drop:
            strata = np.delete(self.strata, j)
            # a label vector with one L removed from j's stratum: any will do for counting
            lab = np.delete(self.is_l, j) if self.is_l[j] else None
            if lab is None:
                lab = self.is_l.copy()
                same = np.flatnonzero((self.strata == self.strata[j]) & self.is_l)
                lab[same[0]] = False
                lab = np.delete(lab, j)
            rows, exact, _ = arrangements(lab, strata, self.draws, self.rng)
            self._drop[j] = (strata, rows, exact)
        return self._drop[j]

    def loo(self, values, labels):
        """Leave one L episode out at a time: list of (difference, p) under the given labels.
        The p-values are computed only when the strict leave-one-out form needs them."""
        out = []
        for j in np.flatnonzero(labels):
            v, lab = np.delete(values, j), np.delete(labels, j)
            if LOO_MODE != "strict":
                out.append((float(lc_stat(v, lab[None, :], np.delete(self.strata, j))[0]), np.nan))
                continue
            strata, rows, exact = self.without(int(j))
            o = float(lc_stat(v, lab[None, :], strata)[0])
            out.append((o, Ref(lc_stat(v, rows, strata), exact).p(o)))
        return out


def lc_power(g, power_draws, rng):
    """Power for L against C. A random label arrangement plays the part of the real one; one
    test's outcome is changed in its 'L' elections only; the rule is then applied. Count effects
    are multipliers (x0.67 and x1.5 are the registered minimum effects); for the riot share the
    riots are thinned or topped up to move the share by 0.10 either way. x1.0 plants nothing and
    is the false-positive rate, either direction."""
    keys = [(t["outcome"], t["measure"]) for t in PRIMARY]
    refs = [g.ref(g.values(k)) for k in keys]
    pre_refs = [g.ref(g.values((t["outcome"], "pre"))) for t in PRIMARY]
    effects = [(f"x{m}", "mult", m) for m in MULTIPLIERS] + \
              [(f"share{d:+.2f}", "share", d) for d in SHARE_SHIFTS]
    hits = {(ti, lab, rule): 0 for ti in range(3) for lab, _, _ in effects for rule, _ in RULE_LABELS}
    for _ in range(power_draws):
        r = int(rng.integers(0, len(g.rows)))
        labels = g.rows[r]
        p_null = [refs[ti].p(refs[ti].values[r]) for ti in range(3)]
        for ti, t in enumerate(PRIMARY):
            base = g.values(keys[ti])
            for lab, kind, size in effects:
                if kind == "share" and t["outcome"] != "RATIO":
                    continue
                if kind == "mult" and size == 1:
                    v, ref = base, refs[ti]
                else:
                    v = base.copy()
                    for i in np.flatnonzero(labels):
                        mem = g.members[i]
                        v[i] += (mem["eng"].planted_delta(mem["a"], 0, t, size, rng) if kind == "mult"
                                 else mem["eng"].planted_share_shift(mem["a"], 0, size, rng))
                    ref = g.ref(v)
                o = g.obs(v, labels)
                p = ref.p(o)
                nothing = kind == "mult" and size == 1
                up = size > 1 if kind == "mult" else size > 0
                right_way = (not np.isnan(o)) and (nothing or (o > 0) == up)
                if np.isnan(p) or not right_way:
                    continue
                if p <= ALPHA:
                    hits[(ti, lab, "raw")] += 1
                ps = np.array([1.0 if np.isnan(q) else q for q in p_null])
                ps[ti] = p
                if holm(ps)[ti] > ALPHA or labels.sum() < 2:
                    continue
                fires, _, _ = decide(holm(ps)[ti], o, pre_refs[ti].values[r], pre_refs[ti], g.loo(v, labels))
                hits[(ti, lab, "three")] += int(fires)
                hits[(ti, lab, "full")] += int(fires and meets_mei(t["outcome"], o))
    rows = []
    for ti, t in enumerate(PRIMARY):
        for rule, label in RULE_LABELS:
            row = {"group": "L-C", "test": t["test"], "outcome": t["outcome"], "rule": label}
            for lab, kind, _ in effects:
                row[lab] = "n/a" if kind == "share" and t["outcome"] != "RATIO" \
                    else f"{hits[(ti, lab, rule)] / power_draws:.2f}"
            rows.append(row)
    return rows


# ----------------------------------------------------------------------------- main analysis
def analyse(args):
    global LOO_MODE, MEI_COUNT, MEI_SHARE
    LOO_MODE = args.loo
    if args.mei_count < 1 or args.mei_share < 0:
        sys.exit("--mei-count must be 1 or more and --mei-share 0 or more")
    MEI_COUNT, MEI_SHARE = args.mei_count, args.mei_share
    if args.facts_only and args.power_only:
        sys.exit("give --facts-only or --power-only, not both")
    countries = [c.strip() for c in args.country.split(",") if c.strip()]
    if not countries or len(set(countries)) != len(countries):
        sys.exit("--country needs one or more distinct names, separated by commas")
    start = parse_day(args.start, "--start") if args.start else None
    end = parse_day(args.end, "--end") if args.end else None
    if start is not None and end is not None and start > end:
        sys.exit("--start is after --end")
    df, week_format = load(args.input)
    kind = data_kind(df)
    rows_read = len(df)
    file_first, file_last = df["WEEK"].min(), df["WEEK"].max()
    if start is not None:
        df = df[df["WEEK"] >= start]
    if end is not None:
        df = df[df["WEEK"] <= end]
    rows_in_period = len(df)

    ep = pd.read_csv(args.episodes, dtype=str, keep_default_na=False)
    missing = [c for c in EPISODE_REQUIRED if c not in ep.columns]
    if missing:
        sys.exit(f"episode list is missing required columns: {missing}")
    n_listed = len(ep)
    ep["class"] = ep["class"].str.strip().str.upper()
    bad = sorted(set(ep.loc[ep["country"].isin(countries), "class"]) - set(CLASSES))
    if bad:
        sys.exit(f"episode list has classes other than {sorted(CLASSES)}: {bad}")
    ep = ep[ep["country"].isin(countries)].reset_index(drop=True)
    if ep.empty:
        sys.exit("no usable episodes for the listed countries in the episode list")

    # ---- consistency guards for election lists (classes L and C), on every listed row whatever
    # its status, so that a rule the list-builders skipped is caught before any outcome is read
    anchored = ep["class"].isin(ANCHORED)
    lc_guard = {"anchor_from": args.anchor_from or "none", "anchor_to": args.anchor_to or "none",
                "rows_outside_anchor_period": 0, "ids_outside_anchor_period": []}
    if anchored.any():
        if "anchor_date" not in ep.columns or (ep.loc[anchored, "anchor_date"].str.strip() == "").any():
            sys.exit("class L and C episodes need an anchor_date (polling day, YYYY-MM-DD)")
        anchors = pd.Series([parse_day(d, "anchor_date") for d in ep.loc[anchored, "anchor_date"]],
                            index=ep.index[anchored])
        # 1. restriction types
        is_l = ep["class"] == "L"
        ltype = ep.loc[is_l, "type"].str.strip().str.lower()
        odd = sorted(set(ltype) - set(TYPES))
        if odd:
            sys.exit(f"class L rows have a type outside {TYPES}: {odd} "
                     f"(first row: {ep.loc[ltype[~ltype.isin(TYPES)].index[0], 'episode_id']})")
        # 2. a standing restriction can never be an included L
        if "timing" in ep.columns and "status" in ep.columns:
            wrong = ep[is_l & (ep["timing"].str.strip().str.lower() == "standing")
                       & (ep["status"].str.strip().str.lower() == "included")]
            if len(wrong):
                sys.exit("class L rows with timing 'standing' must not have status 'included': "
                         + ", ".join(wrong["episode_id"]))
        # 3. elections in one country closer together than their windows allow
        close = []
        for c, idx in ep[anchored].groupby("country").groups.items():
            order = anchors[idx].sort_values()
            gaps = order.diff().dt.days
            for k in np.flatnonzero(gaps.to_numpy() < MIN_GAP_DAYS):
                close.append(f"{ep.loc[order.index[k - 1], 'episode_id']} and {ep.loc[order.index[k], 'episode_id']}")
        if close:
            sys.exit(f"elections in one country less than {MIN_GAP_DAYS} days apart must be one row "
                     "(their windows would share weeks): " + "; ".join(close))
        # 4. the registered polling-day period
        lo = parse_day(args.anchor_from, "--anchor-from") if args.anchor_from else None
        hi = parse_day(args.anchor_to, "--anchor-to") if args.anchor_to else None
        outside = pd.Series(False, index=anchors.index)
        if lo is not None:
            outside |= anchors < lo
        if hi is not None:
            outside |= anchors > hi
        lc_guard.update({"rows_outside_anchor_period": int(outside.sum()),
                         "ids_outside_anchor_period": list(ep.loc[outside[outside].index, "episode_id"]),
                         "earliest_anchor_listed": str(anchors.min().date()),
                         "latest_anchor_listed": str(anchors.max().date())})
        ep = ep.drop(index=outside[outside].index).reset_index(drop=True)

    if "status" in ep.columns:  # only "included" rows enter, unless a sensitivity flag says otherwise
        st = ep["status"].str.strip().str.lower()
        keep = st == "included"
        if args.include_ambiguous:
            keep |= st == "ambiguous"
        if args.include_ambiguous_controls:  # promotes doubtful controls only; never an L row
            keep |= (st == "ambiguous") & (ep["class"] == "C")
        ep = ep[keep].reset_index(drop=True)
    if ep.empty:
        sys.exit("no usable episodes for the listed countries in the episode list")
    lc_filters = []
    for item in args.lc_filter or []:  # every filter must hold (AND); they apply to L rows only
        col, _, val = item.partition("=")
        col = col.strip()
        if not val.strip() or col not in ep.columns:
            sys.exit("--lc-filter needs COLUMN=VALUE, with COLUMN in the episode list")
        ep = ep[(ep["class"] != "L") | (ep[col].str.strip().str.lower() == val.strip().lower())]
        ep = ep.reset_index(drop=True)
        lc_filters.append(f"{col}={val.strip()}")
    lc_filter = " AND ".join(lc_filters) if lc_filters else "none"
    has_stratum = "stratum" in ep.columns

    # ---- per-country series and run facts
    series, per_country, stop_reasons = {}, {}, []
    for c in countries:
        d = df[df["COUNTRY"] == c]
        if d.empty:
            sys.exit(f"no rows for country '{c}' in the period")
        # The range runs from --start/--end where given (never beyond what the file holds),
        # otherwise from the country's own first and last week with rows.
        w0 = max(saturday_on_or_after(start), saturday_on_or_after(file_first)) if start is not None \
            else d["WEEK"].min()
        w1 = min(saturday_on_or_before(end), saturday_on_or_before(file_last)) if end is not None \
            else d["WEEK"].max()
        sat = round(float((d["WEEK"].dt.weekday == 5).mean()), 4)
        band = (d["WEEK"].dt.year // 5 * 5).value_counts().sort_index()
        fact = {"rows": int(len(d)),
                "first_week_with_rows": str(d["WEEK"].min().date()),
                "last_week_with_rows": str(d["WEEK"].max().date()),
                "range_first_week": str(w0.date()), "range_last_week": str(w1.date()),
                "share_of_weeks_starting_saturday": sat,
                "rows_by_5yr_band": {f"{int(k)}-{int(k) + 4}": int(v) for k, v in band.items()},
                "episodes_used": int((ep["country"] == c).sum())}
        if sat >= 0.99:
            y, weeks, n_empty, longest = build_series(d, w0, w1)
            T = len(weeks)
            fact.update({"weeks_in_range": T, "weeks_with_no_rows": n_empty,
                         "share_of_weeks_with_no_rows": round(n_empty / T, 4),
                         "longest_run_of_weeks_with_no_rows": longest})
            series[c] = (y, weeks, w0)
        per_country[c] = fact

    # File-level weeks: the range the period arguments allow, over every country in the file.
    fw0 = saturday_on_or_after(max(start, file_first) if start is not None else file_first)
    fw1 = saturday_on_or_before(min(end, file_last) if end is not None else file_last)
    file_T = max((fw1 - fw0).days // 7 + 1, 0)
    file_empty, file_longest = empty_weeks(df["WEEK"], fw0, fw1)
    if file_T and file_empty / file_T > MAX_EMPTY_SHARE:
        stop_reasons.append(f"{file_empty} of {file_T} weeks in the range have no row for any country "
                            f"in the file (more than {MAX_EMPTY_SHARE:.0%})")
    if file_longest >= MAX_EMPTY_RUN:
        stop_reasons.append(f"a run of {file_longest} consecutive weeks has no row for any country "
                            f"in the file ({MAX_EMPTY_RUN} or more)")

    facts = {
        "script_version": VERSION, "script_sha256": sha256_of(__file__), "data_kind": kind,
        "input_sha256": sha256_of(args.input), "episodes_sha256": sha256_of(args.episodes),
        "week_format_parsed": week_format,
        "start_argument": args.start or "none", "end_argument": args.end or "none",
        "rows_read": int(rows_read), "rows_in_period": int(rows_in_period),
        "file_first_week": str(file_first.date()), "file_last_week": str(file_last.date()),
        "file_countries_in_period": int(df["COUNTRY"].nunique()),
        "file_weeks_in_range": int(file_T), "file_weeks_with_no_rows_for_any_country": file_empty,
        "file_share_of_weeks_with_no_rows": round(file_empty / file_T, 4) if file_T else None,
        "file_longest_run_of_weeks_with_no_rows": file_longest,
        "countries": per_country,
        "seed": args.seed, "placebo_draws_when_not_exact": args.draws, "exact_limit": EXACT_LIMIT,
        "power_draws": args.power_draws, "min_episodes_per_class": args.min_episodes,
        "primary_class": args.primary_class, "descriptive_only": bool(args.descriptive_only),
        "lc_design": args.lc_design, "lc_filter": lc_filter, "leave_one_out": args.loo,
        "p_placebo": args.p_placebo, "min_matched_positions": MIN_MATCHED,
        "facts_only": bool(args.facts_only), "allow_empty_weeks": bool(args.allow_empty_weeks),
        "episodes_listed": int(n_listed), "episodes_used": int(len(ep)),
        "episodes_used_by_class": {k: int(v) for k, v in ep["class"].value_counts().sort_index().items()},
        "include_ambiguous": bool(args.include_ambiguous),
        "include_ambiguous_controls": bool(args.include_ambiguous_controls),
        "mei_count": args.mei_count, "mei_share": args.mei_share, "power_only": bool(args.power_only),
        "election_list_checks": lc_guard,
        "lead_weeks": LEAD_WEEKS, "lag_weeks": LAG_WEEKS, "comparison_shifts_weeks": COMPARISON_SHIFTS,
    }
    print("# RUN FACTS")
    print(json.dumps(facts, indent=2))
    for c in countries:
        if per_country[c]["share_of_weeks_starting_saturday"] < 0.99:
            sys.exit(f"WEEK values for '{c}' are not Saturday-anchored; stopping before any analysis")

    print("\n## EMPTY-WEEK CHECK (whole file; each country's own empty weeks are in the run facts)")
    if not stop_reasons:
        print("passed: the file has rows for enough of the weeks in the range")
    else:
        for r in stop_reasons:
            print("FAILED - " + r)
        if args.facts_only:
            print("(facts-only run: continuing to the structure tables; an analysis run would stop here)")
        elif args.allow_empty_weeks:
            print("--allow-empty-weeks was given: continuing. Weeks with no rows count as zero events.")
        else:
            sys.exit("stopping before any analysis: " + "; ".join(stop_reasons) +
                     ". Check the input and the period; --allow-empty-weeks overrides.")

    # ---- engines and listed episodes
    engines, real, lc_members = {}, [], []
    for c in countries:
        y, weeks, w0 = series[c]
        e = ep[ep["country"] == c].copy()
        e["s"] = [(parse_day(d, "start_date") - w0).days // 7 for d in e["start_date"]]
        e["e"] = [(parse_day(d, "end_date") - w0).days // 7 for d in e["end_date"]]
        e["dur"] = e["e"] - e["s"] + 1
        if (e["dur"] < 1).any():
            sys.exit(f"an episode for '{c}' ends before it starts")
        # Control elections (C) have no restriction, so they do not screen placebo positions.
        blocking = e[e["class"] != "C"]
        eng = Engine(y, len(weeks), list(zip(blocking["s"], blocking["e"])))
        engines[c] = eng
        struct = []
        for _, r in e.iterrows():
            if r["class"] in ANCHORED:
                # Outcome windows run from polling day: four lead weeks before the polling week,
                # then four weeks starting with it. No within-country comparison years are used.
                a = (parse_day(r["anchor_date"], "anchor_date") - w0).days // 7
                usable = eng._valid(a, 0)
                struct.append({"episode_id": r.episode_id, "class": r["class"], "duration_weeks": int(r.dur),
                               "window_complete": bool(usable), "comparison_windows": 0})
                if usable:
                    stratum = r["stratum"].strip() if has_stratum and r["stratum"].strip() else c
                    lc_members.append({"id": r.episode_id, "country": c, "cls": r["class"], "a": int(a),
                                       "raw": eng._raw_stats(a, 0), "eng": eng, "stratum": stratum,
                                       "type": r["type"].strip().lower()})
                continue
            adj, ncomp = eng.adjusted(int(r.s), int(r.dur), is_real=True)
            struct.append({"episode_id": r.episode_id, "class": r["class"], "duration_weeks": int(r.dur),
                           "window_complete": adj is not None, "comparison_windows": ncomp})
            if adj is not None:
                real.append({"id": r.episode_id, "country": c, "cls": r["class"], "s": int(r.s),
                             "dur": int(r.dur), "adj": adj, "eng": eng})
        emit(f"EPISODES, country {countries.index(c) + 1} of {len(countries)}: {c} "
             "(structure only; no outcome values)", pd.DataFrame(struct))
        cov = [{"outcome": k,
                "first_year_present": int(weeks[eng.first[k]].year) if eng.first[k] < len(weeks) else "never",
                "share_of_weeks_nonzero": round(float(np.mean(y[k] > 0)), 2)} for k in COUNT_OUTCOMES]
        emit(f"OUTCOME COVERAGE: {c} (windows before an outcome first appears are excluded for it)",
             pd.DataFrame(cov))

    rng_draw = np.random.default_rng([args.seed, 1])
    rng_power = np.random.default_rng([args.seed, 2])
    lc_rows, usable_rows, lg = [], [], None
    if lc_members:
        # Structure of the L-against-C comparison. It depends on the list and on which windows are
        # complete, not on any outcome value, so it is printed in every mode.
        lg = LCGroup(lc_members, args.lc_design, args.draws, rng_draw)
        n_l_all = sum(m["cls"] == "L" for m in lc_members)
        l_types = sorted({m["type"] for m in lg.members if m["cls"] == "L"}) if lg.usable else []
        lc_rows.append({"design": args.lc_design, "L_listed": n_l_all, "C_listed": len(lc_members) - n_l_all,
                        "L_used": lg.n_l if lg.usable else 0, "C_used": lg.n_c if lg.usable else 0,
                        "strata_used": lg.n_strata if lg.usable else 0,
                        "dropped_no_counterpart": lg.dropped,
                        "label_arrangements": (str(lg.count) if lg.count < 10 ** 9 else f"{lg.count:.2e}")
                        if lg.usable else "0",
                        "method": lg.method if lg.usable else "none",
                        "outage_among_L_used": bool(OUTAGE_TYPES & set(l_types))})
        emit("L AGAINST C: STRUCTURE (windows are measured from polling day; the comparison is the "
             "C elections, not other years; 'used' = included, complete window, counterpart in stratum)",
             pd.DataFrame(lc_rows))
        if lg.usable:
            for g_ in sorted(set(lg.strata)):
                inside = lg.strata == g_
                usable_rows.append({"stratum": g_, "L_usable": int((lg.is_l & inside).sum()),
                                    "C_usable": int((~lg.is_l & inside).sum())})
            usable_rows.append({"stratum": "TOTAL", "L_usable": lg.n_l, "C_usable": lg.n_c})
            for k in range(0, len(usable_rows), MAX_ROWS):
                emit(f"L AGAINST C: USABLE ELECTIONS BY STRATUM (part {k // MAX_ROWS + 1}; --min-episodes "
                     f"{args.min_episodes} is compared with the L total)", pd.DataFrame(usable_rows[k:k + MAX_ROWS]))

    if args.facts_only:
        print("\n# END OF OUTPUT (facts-only run: no test was computed; everything above may be pasted back)")
        return {"facts": facts, "verdicts": [], "power": [], "leadlag": [], "explore": [], "placebo": [],
                "obs": {}, "lc": lc_rows, "matching": [], "usable": usable_rows, "gate": None}

    # Negative-control episodes (class N) form their own group and are never pooled with E or P.
    groups = {"ALL": [r for r in real if r["cls"] in ("E", "P")],
              "P": [r for r in real if r["cls"] == "P"],
              "E": [r for r in real if r["cls"] == "E"],
              "N": [r for r in real if r["cls"] == "N"]}
    verdict_rows, explore_rows, power_rows, leadlag_rows, placebo_rows, obs_out = [], [], [], [], [], {}
    matching_rows = []

    for gname, members in groups.items():
        n = len(members)
        if n == 0:
            continue
        g = Group(gname, members, args.draws, rng_draw, matched=(args.p_placebo == "matched"))
        if gname == "P" and args.p_placebo == "matched":
            for m, k in zip(members, g.sizes):
                matching_rows.append({"episode_id": m["id"], "matched_placebo_positions": int(k - 1)})
        placebo_rows.append({"group": gname, "episodes": n,
                             "countries": len({m["country"] for m in members}),
                             "min_placebo_positions": int(min(g.sizes)),
                             "max_placebo_positions": int(max(g.sizes)),
                             "possible_sets": str(g.n_sets) if g.n_sets < 10 ** 9 else f"{g.n_sets:.2e}",
                             "method": g.method if g.usable else "none"})
        if not g.usable:
            verdict_rows.append({"group": gname, "test": "all", "result": "NOT RUN: no placebo positions"})
            continue

        if args.descriptive_only:
            why_desc = "this run is declared descriptive (no hypothesis is tested on it)"
        elif gname not in (args.primary_class, "N"):
            why_desc = f"class {args.primary_class} is the primary test; this group is reported for description"
        elif n < args.min_episodes:
            why_desc = f"{n} episode(s), below the minimum of {args.min_episodes}"
        else:
            why_desc = None
        # class P with matched placebo weeks: too few matched positions means no verdict
        thin_match = gname == "P" and args.p_placebo == "matched" and min(g.sizes) - 1 < MIN_MATCHED

        tmp, pvals = [], []
        for t in PRIMARY:
            key, prekey = (t["outcome"], t["measure"]), (t["outcome"], "pre")
            ref, o = g.ref(key), g.obs(key)
            p = ref.p(o)
            loo = []
            if n >= 2:
                for j in range(n):
                    oj = g.obs(key, drop=j)
                    loo.append((oj, g.ref(key, drop=j).p(oj)))
            tmp.append((t, ref, o, p, g.obs(prekey), g.ref(prekey), loo))
            pvals.append(1.0 if np.isnan(p) else p)
        adj_p = holm(np.array(pvals))
        obs_out[gname] = {}
        for (t, ref, o, p, pre_o, pre_ref, loo), pa in zip(tmp, adj_p):
            fires, pre_flag, loo_ok = decide(pa, o, pre_o, pre_ref, loo)
            obs_out[gname][t["test"]] = o
            way = direction(o)
            if why_desc is not None:
                result = f"DESCRIPTIVE ONLY: {why_desc}"
            elif thin_match:
                result = (f"NOT TESTABLE: an episode has fewer than {MIN_MATCHED} matched placebo weeks "
                          "(see P MATCHING)")
            elif np.isnan(o):
                result = "INSUFFICIENT EVIDENCE: statistic undefined"
            elif fires and gname == "N":
                result = f"NEGATIVE CONTROL MOVED ({way}): a null was expected"
            elif fires and not meets_mei(t["outcome"], o):
                result = f"DETECTED, BELOW THE MINIMUM EFFECT OF INTEREST ({way})"
            elif fires and way == "up":
                result = f"SUPPORTED: {t['up']}" + (f" ({t['down']} contradicted)" if t["down"] else "")
            elif fires and t["down"]:
                result = f"SUPPORTED: {t['down']} ({t['up']} contradicted)"
            elif fires:
                result = f"CONTRADICTED: {t['up']} (change is in the opposite direction)"
            else:
                why = [w for w, b in [("not outside placebo spread after Holm", not pa <= ALPHA),
                                      ("same-sign pre-trend", pre_flag),
                                      ("fails leave-one-out", not loo_ok)] if b]
                head = "NULL EXPECTED, NULL FOUND" if gname == "N" else "INSUFFICIENT EVIDENCE"
                result = f"{head}: " + "; ".join(why)
            share = ref.share_below(o)
            verdict_rows.append({
                "group": gname, "test": t["test"], "outcome": t["outcome"],
                "expected": "null expected" if gname == "N" else t["expected"],
                "pooled_change": fmt_change(t["outcome"], o), "direction": way,
                "placebo_share_below": "n/a" if np.isnan(share) else f"{share:.3f}",
                "rank": "n/a" if np.isnan(o) else f"{ref.rank(o)} of {ref.n}",
                "p_two_sided": fmt_p(p), "p_holm": f"{pa:.4f}",
                "pretrend_flag": pre_flag, "leave_one_out_ok": loo_ok, "result": result})

        if g.n_sets >= MIN_SETS_FOR_POWER:
            power_rows.extend(power_block(g, args.power_draws, rng_power))
        else:
            power_rows.append({"group": gname, "test": "all", "outcome": "all",
                               "rule": f"not measurable at this size ({g.n_sets} possible placebo sets, "
                                       f"fewer than {MIN_SETS_FOR_POWER})"})

        for oc, ms in EXPLORATORY:
            ref, o = g.ref((oc, ms)), g.obs((oc, ms))
            explore_rows.append({"group": gname, "outcome": oc, "measure": ms,
                                 "pooled_change": fmt_change(oc, o), "direction": direction(o),
                                 "rank": "n/a" if np.isnan(o) else f"{ref.rank(o)} of {ref.n}",
                                 "p_two_sided": fmt_p(ref.p(o)), "status": "reporting check" if oc == REPORTING_CHECK else "exploratory"})
        if n >= 2:  # pooled lead/lag ratios: averaged across episodes, never per episode
            for oc in ["Y1", "Y2", "Y3"]:
                row = {"group": gname, "outcome": oc, "episodes_pooled": n}
                for lab in LEADLAG:
                    v = g.obs((oc, lab))
                    row[lab] = "n/a" if np.isnan(v) else f"x{np.exp(v):.2f}"
                leadlag_rows.append(row)

    # ---- elections with a restriction (L) against elections without (C)
    if lc_members:
        if not lg.usable:
            verdict_rows.append({"group": "L-C", "test": "all",
                                 "result": "NOT RUN: no stratum holds both an L and a C election"})
        else:
            if args.descriptive_only:
                why_desc = "this run is declared descriptive (no hypothesis is tested on it)"
            elif args.primary_class != "LC":
                why_desc = f"class {args.primary_class} is the primary test; this group is reported for description"
            elif lg.n_l < args.min_episodes:
                why_desc = f"{lg.n_l} L election(s) usable, below the minimum of {args.min_episodes}"
            elif args.lc_design == "pooled" and lg.n_c < args.min_episodes:
                why_desc = f"{lg.n_c} C election(s) usable, below the minimum of {args.min_episodes}"
            else:
                why_desc = None
            tmp, pvals = [], []
            for t in PRIMARY:
                v, pv = lg.values((t["outcome"], t["measure"])), lg.values((t["outcome"], "pre"))
                ref, o = lg.ref(v), lg.obs(v)
                p = ref.p(o)
                tmp.append((t, ref, o, p, lg.obs(pv), lg.ref(pv), lg.loo(v, lg.is_l) if lg.n_l >= 2 else [],
                            f"{int((~np.isnan(v) & lg.is_l).sum())} L, {int((~np.isnan(v) & ~lg.is_l).sum())} C"))
                pvals.append(1.0 if np.isnan(p) else p)
            adj_p = holm(np.array(pvals))
            obs_out["L-C"] = {}
            for (t, ref, o, p, pre_o, pre_ref, loo, used), pa in zip(tmp, adj_p):
                fires, pre_flag, loo_ok = decide(pa, o, pre_o, pre_ref, loo)
                obs_out["L-C"][t["test"]] = o
                way = direction(o)
                if why_desc is not None:
                    result = f"DESCRIPTIVE ONLY: {why_desc}"
                elif np.isnan(o):
                    result = "INSUFFICIENT EVIDENCE: statistic undefined"
                elif fires and way == "down" and t["test"] == "T1" and lc_rows[0]["outage_among_L_used"]:
                    # Outages cut the reporting this outcome depends on, so a fall is never read
                    # as suppression (H2) when any L election in the run had one.
                    result = ("INSUFFICIENT EVIDENCE: recorded protest fell; this cannot be separated "
                              "from under-recording")
                elif fires and not meets_mei(t["outcome"], o):
                    result = f"DETECTED, BELOW THE MINIMUM EFFECT OF INTEREST ({way})"
                elif fires and way == "up":
                    result = f"SUPPORTED: {t['up']}" + (f" ({t['down']} contradicted)" if t["down"] else "")
                elif fires and t["down"]:
                    result = f"SUPPORTED: {t['down']} ({t['up']} contradicted)"
                elif fires:
                    result = f"CONTRADICTED: {t['up']} (change is in the opposite direction)"
                else:
                    why = [w for w, b in [("not outside the label-permutation spread after Holm", not pa <= ALPHA),
                                          ("same-sign pre-trend", pre_flag),
                                          ("fails leave-one-out", not loo_ok)] if b]
                    result = "INSUFFICIENT EVIDENCE: " + "; ".join(why)
                share = ref.share_below(o)
                verdict_rows.append({
                    "group": "L-C", "test": t["test"], "outcome": t["outcome"], "expected": t["expected"],
                    "elections_used": used,
                    "pooled_change": fmt_change(t["outcome"], o), "direction": way,
                    "placebo_share_below": "n/a" if np.isnan(share) else f"{share:.3f}",
                    "rank": "n/a" if np.isnan(o) else f"{ref.rank(o)} of {ref.n}",
                    "p_two_sided": fmt_p(p), "p_holm": f"{pa:.4f}",
                    "pretrend_flag": pre_flag, "leave_one_out_ok": loo_ok, "result": result})
            if lg.count >= MIN_SETS_FOR_POWER:
                power_rows.extend(lc_power(lg, args.power_draws, rng_power))
            else:
                power_rows.append({"group": "L-C", "test": "all", "outcome": "all",
                                   "rule": f"not measurable at this size ({lg.count} label arrangements, "
                                           f"fewer than {MIN_SETS_FOR_POWER})"})
            for oc, ms in EXPLORATORY:
                v = lg.values((oc, ms))
                ref, o = lg.ref(v), lg.obs(v)
                explore_rows.append({"group": "L-C", "outcome": oc, "measure": ms,
                                     "pooled_change": fmt_change(oc, o), "direction": direction(o),
                                     "rank": "n/a" if np.isnan(o) else f"{ref.rank(o)} of {ref.n}",
                                     "p_two_sided": fmt_p(ref.p(o)), "status": "reporting check" if oc == REPORTING_CHECK else "exploratory"})
            for cls in ANCHORED:  # pooled lead/lag ratios for each side, raw (no comparison years)
                side = [m for m in lg.members if m["cls"] == cls]
                if len(side) >= 2:
                    for oc in ["Y1", "Y2", "Y3"]:
                        row = {"group": f"{cls} (raw)", "outcome": oc, "episodes_pooled": len(side)}
                        for lab in LEADLAG:
                            v = pooled([m["raw"][(oc, lab)] for m in side])
                            row[lab] = "n/a" if np.isnan(v) else f"x{np.exp(v):.2f}"
                        leadlag_rows.append(row)

    if matching_rows:
        emit(f"P MATCHING (placebo weeks in the same within-country tercile of pre-episode level; "
             f"fewer than {MIN_MATCHED} for any episode means not testable)", pd.DataFrame(matching_rows))
    if not placebo_rows:
        placebo_rows.append({"group": "none", "episodes": 0})
    emit("PLACEBO STRUCTURE (positions are taken within each episode's own country)",
         pd.DataFrame(placebo_rows))
    if not args.power_only:
        emit("PRIMARY TESTS (two-sided; rank = reference sets at least as far from zero, out of all used; "
             "for L-C the change is L minus C)", pd.DataFrame(verdict_rows).fillna(""))
        if explore_rows:
            emit("EXPLORATORY OUTCOMES (no verdicts; YB is the reporting check: armed clashes should not move)",
                 pd.DataFrame(explore_rows))
        if leadlag_rows:
            emit("POOLED LEAD/LAG CHANGE RATIOS (relative to the lead-week mean, comparison-adjusted)",
                 pd.DataFrame(leadlag_rows))
        else:
            print("\n## POOLED LEAD/LAG CHANGE RATIOS\nnot printed: fewer than 2 episodes in every group")
    gate = None
    if power_rows:
        for k in range(0, len(power_rows), MAX_ROWS):
            emit("POWER (share of planted reference sets in which the rule fires in the planted direction; "
                 "x1.0 plants nothing and is the false-positive rate, either direction; 'three conditions' "
                 f"= Holm, pre-trend, leave-one-out; 'full rule' adds the minimum effect; part {k // MAX_ROWS + 1})",
                 pd.DataFrame(power_rows[k:k + MAX_ROWS]).fillna(""))
        row = next((r for r in power_rows if r.get("group") == GATE[0] and r.get("test") == GATE[1]
                    and r.get("rule") == GATE[2]), None)
        print("\n## POWER GATE FIGURE")
        if row is None:
            print(f"not available: no power row for {GATE[0]}, {GATE[1]}, {GATE[2]} "
                  "(too few label arrangements, or no L-against-C comparison in this run)")
        else:
            gate = float(row[GATE[3]])
            print(f"{GATE[0]}, {GATE[1]} (peaceful protest), rule '{GATE[2]}', effect {GATE[3]}: {gate:.2f}")
            print("This is the share of simulated runs in which a rise of the registered minimum size, planted "
                  "in the L elections, passed Holm, the pre-trend check and leave-one-out.")
    if args.power_only:
        print("\n# END OF OUTPUT (power-only run: no test result was printed; everything above may be pasted back)")
        return {"facts": facts, "verdicts": [], "power": power_rows, "leadlag": [], "explore": [],
                "placebo": placebo_rows, "obs": {}, "lc": lc_rows, "matching": matching_rows,
                "usable": usable_rows, "gate": gate}
    print("\n## VINTAGE CHECK\nnot run: it needs at least two dated downloads of the same weeks")
    print("\n# END OF OUTPUT (everything above may be pasted back; nothing else was written)")
    return {"facts": facts, "verdicts": verdict_rows, "power": power_rows, "leadlag": leadlag_rows,
            "explore": explore_rows, "placebo": placebo_rows, "obs": obs_out, "lc": lc_rows,
            "matching": matching_rows, "usable": usable_rows, "gate": gate}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="CSV with the aggregated weekly columns")
    ap.add_argument("--episodes", required=True,
                    help="CSV: episode_id,country,class(L|C|P|E|N),type,start_date,end_date"
                         "[,anchor_date,stratum,status,...]; anchor_date is required for L and C")
    ap.add_argument("--country", required=True, help="one country name, or several separated by commas")
    ap.add_argument("--start", default=None, help="YYYY-MM-DD: use weeks on or after this day")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD: use weeks on or before this day")
    ap.add_argument("--facts-only", action="store_true",
                    help="print run facts, episode structure and outcome coverage, then exit before any test")
    ap.add_argument("--allow-empty-weeks", action="store_true",
                    help="continue past the file-level empty-week stop (weeks with no rows count as zero events)")
    ap.add_argument("--seed", type=int, default=20261111)
    ap.add_argument("--draws", type=int, default=2000,
                    help="random placebo sets, used only when there are too many to enumerate")
    ap.add_argument("--power-draws", type=int, default=500)
    ap.add_argument("--min-episodes", type=int, default=3)
    ap.add_argument("--primary-class", default="LC", choices=["LC", "E", "P", "ALL"],
                    help="group that carries verdicts (decided 2026-11-14: LC, elections with a "
                         "restriction against elections without)")
    ap.add_argument("--lc-design", default="stratified", choices=["stratified", "pooled"],
                    help="stratified: compare L with C inside each stratum (the 'stratum' column, or the "
                         "country when there is none); pooled: one comparison across all L and C")
    ap.add_argument("--lc-filter", action="append", metavar="COLUMN=VALUE",
                    help="use only the L episodes with this value in this episode-list column; may be "
                         "given more than once, and then every filter must hold (case and outer spaces ignored)")
    ap.add_argument("--mei-count", type=float, default=1.5,
                    help="minimum effect of interest for count outcomes, as a ratio (default 1.5: a verdict "
                         "needs at least x1.50 or at most x0.67)")
    ap.add_argument("--mei-share", type=float, default=0.10,
                    help="minimum effect of interest for the riot share, as an absolute change (default 0.10)")
    ap.add_argument("--anchor-from", default=None,
                    help="YYYY-MM-DD: L and C rows with an anchor_date before this are left out and listed")
    ap.add_argument("--anchor-to", default=None,
                    help="YYYY-MM-DD: L and C rows with an anchor_date after this are left out and listed")
    ap.add_argument("--power-only", action="store_true",
                    help="print run facts, structure, usable counts, the power table and the gate figure; "
                         "no test result is printed")
    ap.add_argument("--include-ambiguous-controls", action="store_true",
                    help="also use class C rows whose status is 'ambiguous'; class L rows are unaffected")
    ap.add_argument("--loo", default="strict", choices=["strict", "sign"],
                    help="leave-one-out: strict (sign and p <= 0.05 each time) or sign (sign only)")
    ap.add_argument("--p-placebo", default="matched", choices=["matched", "all"],
                    help="class P placebo weeks: matched on pre-episode level (same tercile), or all eligible")
    ap.add_argument("--include-ambiguous", action="store_true",
                    help="also use every row whose status is 'ambiguous', of any class (not used in the "
                         "election study; see --include-ambiguous-controls)")
    ap.add_argument("--descriptive-only", action="store_true",
                    help="no verdicts at all (decided 2026-11-11 for a single-country run)")
    return analyse(ap.parse_args(argv))


if __name__ == "__main__":
    main()
