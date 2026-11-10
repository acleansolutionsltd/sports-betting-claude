"""Stage 5 - walk-forward backtest for the football model.

Rolling origin: for each match date the team model is fitted only on matches
played before that date. Prices used are the pre-match snapshot (the "bet
time" price); closing prices are used only to measure closing-line value.
Hyperparameters are tuned on the validation seasons and frozen for the test
seasons, which are the only numbers reported as out-of-sample.
"""
from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd

from ..config import CLEAN, ROOT, load_config
from ..ev.odds import devig_power
from ..models.football import dixon_coles as dc
from ..models.football.sim import blend_lambdas, exact_market_probs
from . import metrics as mx

REPORT = ROOT / "backtest" / "reports" / "football.md"
PRICED = {"home": ("B365H", "B365CH"), "away": ("B365A", "B365CA"),
          "over_2.5": ("B365>2.5", "B365C>2.5"), "under_2.5": ("B365<2.5", "B365C<2.5")}
UNPRICED = ["btts_yes", "btts_no", "over_1.5", "under_3.5", "under_4.5", "dc_1x", "dc_x2", "dc_12"]
MARKET_GROUP = {"home": "1X2", "away": "1X2", "over_2.5": "totals", "under_2.5": "totals",
                "btts_yes": "BTTS", "btts_no": "BTTS", "over_1.5": "totals", "under_3.5": "totals",
                "under_4.5": "totals", "dc_1x": "double chance", "dc_x2": "double chance",
                "dc_12": "double chance"}


def load_matches() -> pd.DataFrame:
    m = pd.read_csv(CLEAN / "football_matches.csv", parse_dates=["match_date"], low_memory=False,
                    dtype={"season": str})
    return m.dropna(subset=["match_date"]).sort_values(["match_date", "Div", "HomeTeam"]).reset_index(drop=True)


def add_anchor(m: pd.DataFrame) -> pd.DataFrame:
    """De-vigged sharp price per match: Pinnacle where published, otherwise
    Betfair Exchange, otherwise the market average. The source is recorded."""
    m = m.copy()
    sources = [("pinnacle", "PS{}", "P{}2.5", "PSC{}", "PC{}2.5"),
               ("betfair_exchange", "BFE{}", "BFE{}2.5", "BFEC{}", "BFEC{}2.5"),
               ("market_average", "Avg{}", "Avg{}2.5", "AvgC{}", "AvgC{}2.5")]
    for c in ["a_home", "a_draw", "a_away", "a_over", "c_home", "c_draw", "c_away", "c_over"]:
        m[c] = np.nan
    m["anchor_source"] = None
    for name, x12, ou, cx12, cou in sources:
        cols = [x12.format(s) for s in "HDA"]
        if not set(cols) <= set(m.columns):
            continue
        p = devig_power(m[cols].apply(pd.to_numeric, errors="coerce").to_numpy())
        take = m["anchor_source"].isna() & np.isfinite(p).all(axis=1)
        m.loc[take, ["a_home", "a_draw", "a_away"]] = p[take]
        m.loc[take, "anchor_source"] = name
        po = devig_power(m[[ou.format(">"), ou.format("<")]].apply(pd.to_numeric, errors="coerce").to_numpy())
        m.loc[take, "a_over"] = po[take, 0]
        pc = devig_power(m[[cx12.format(s) for s in "HDA"]].apply(pd.to_numeric, errors="coerce").to_numpy())
        m.loc[take, ["c_home", "c_draw", "c_away"]] = pc[take]
        pco = devig_power(m[[cou.format(">"), cou.format("<")]].apply(pd.to_numeric, errors="coerce").to_numpy())
        m.loc[take, "c_over"] = pco[take, 0]
    return m


def component_lambdas(m: pd.DataFrame, seasons, xi: float, ridge: float, cfg: dict,
                      with_market: bool = True) -> pd.DataFrame:
    """Walk forward and record each component's expected goals for every match
    in ``seasons``. Nothing dated on or after a match date is used for it."""
    fc = cfg["football"]
    rows = []
    for div, lg in m.groupby("Div"):
        target = lg[lg.season.isin(seasons)]
        model, fitted_on = None, None
        for date, day in target.groupby("match_date"):
            if model is None or (date - fitted_on).days >= fc["refit_days"]:
                model = dc.fit(lg, date, xi, ridge, fc["history_days"]) or model
                fitted_on = date
            form = dc.shots_form(lg, date, fc["shots_window"])
            for r in day.itertuples():
                rho = model.rho if model else 0.0
                team = model.lambdas(r.HomeTeam, r.AwayTeam, fc["min_team_matches"]) if model else None
                shots = dc.shots_lambdas(form, r.HomeTeam, r.AwayTeam)
                mkt = None
                if with_market and np.isfinite(r.a_home):
                    mkt = dc.lambdas_from_market(r.a_home, r.a_draw, r.a_away, r.a_over, rho, fc["dispersion"])
                rows.append((r.Index, rho, *(mkt or (np.nan, np.nan)), *(team or (np.nan, np.nan)),
                             *(shots or (np.nan, np.nan))))
    comp = pd.DataFrame(rows, columns=["idx", "rho", "mk_h", "mk_a", "tm_h", "tm_a", "sh_h", "sh_a"]).set_index("idx")
    return m.join(comp, how="inner")


def _pair(r, a, b):
    return None if not np.isfinite(getattr(r, a)) else (getattr(r, a), getattr(r, b))


def predict(comp: pd.DataFrame, weights: dict, dispersion=None) -> pd.DataFrame:
    """Blend the components and produce market probabilities for every match."""
    out = []
    for r in comp.itertuples():
        lam, used = blend_lambdas(_pair(r, "mk_h", "mk_a"), _pair(r, "tm_h", "tm_a"),
                                  _pair(r, "sh_h", "sh_a"), weights)
        if lam is None:
            continue
        p = exact_market_probs(lam[0], lam[1], r.rho, dispersion)
        p.update(idx=r.Index, lam_h=lam[0], lam_a=lam[1], w_market=used.get("market", 0.0))
        out.append(p)
    P = pd.DataFrame(out).set_index("idx").add_prefix("p_")
    return comp.join(P, how="inner")


def outcomes(d: pd.DataFrame) -> pd.DataFrame:
    hg, ag = d.FTHG, d.FTAG
    y = pd.DataFrame(index=d.index)
    y["home"], y["draw"], y["away"] = hg > ag, hg == ag, hg < ag
    y["btts_yes"] = (hg > 0) & (ag > 0)
    y["btts_no"] = ~y["btts_yes"]
    for line in (1.5, 2.5, 3.5, 4.5):
        y[f"over_{line}"] = (hg + ag) > line
        y[f"under_{line}"] = ~y[f"over_{line}"]
    y["dc_1x"], y["dc_x2"], y["dc_12"] = ~y["away"], ~y["home"], ~y["draw"]
    return y.astype(int)


def selections(d: pd.DataFrame, prob_cols: dict, floor: float) -> pd.DataFrame:
    """Every priced leg whose probability meets the floor. ``prob_cols`` maps a
    market to the probability column that decides qualification."""
    y = outcomes(d)
    rows = []
    for mk, (price_col, close_col) in PRICED.items():
        price = pd.to_numeric(d[price_col], errors="coerce")
        close = pd.to_numeric(d[close_col], errors="coerce")
        q = d[(d[prob_cols[mk]] >= floor) & price.notna()]
        won = y.loc[q.index, mk]
        rows.append(pd.DataFrame({
            "match_idx": q.index, "match_date": q.match_date, "kickoff_utc": q.kickoff_utc, "league": q.Div,
            "season": q.season, "home_team": q.HomeTeam, "away_team": q.AwayTeam, "market": mk,
            "market_group": MARKET_GROUP[mk], "model_prob": q[prob_cols[mk]], "price": price[q.index],
            "result": np.where(won == 1, "win", "loss"), "stake_units": 1.0,
            "net_units": np.where(won == 1, price[q.index] - 1, -1.0),
            "clv": price[q.index] / close[q.index] - 1}))
    return pd.concat(rows).sort_values(["kickoff_utc", "league", "home_team", "market"]).reset_index(drop=True)


def accas(sel: pd.DataFrame, sizes=(3, 5, 7)) -> pd.DataFrame:
    """Weekly accumulators from the qualifying legs: one leg per match (its most
    probable), highest probabilities first. Legs are from different matches, so
    joint probability is the product."""
    rows = []
    week = sel.match_date.dt.to_period("W-THU")
    for wk, g in sel.groupby(week):
        best = g.sort_values("model_prob", ascending=False).drop_duplicates("match_idx")
        for n in sizes:
            if len(best) < n:
                continue
            legs = best.head(n)
            won = (legs.result == "win").all()
            price = float(legs.price.prod())
            rows.append({"week": str(wk), "kickoff_utc": legs.kickoff_utc.min(), "n_legs": n,
                         "bucket": "2-3 legs" if n <= 3 else "4-6 legs" if n <= 6 else "7+ legs",
                         "model_prob": float(legs.model_prob.prod()), "price": price,
                         "result": "win" if won else "loss", "stake_units": 1.0,
                         "net_units": price - 1 if won else -1.0})
    return pd.DataFrame(rows).sort_values("kickoff_utc").reset_index(drop=True)


def tune_team_model(m: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Grid-search time decay and ridge on the validation seasons, scored by the
    team model's own 1X2 log loss. The winner is frozen in config.yaml."""
    val = cfg["football"]["validation_seasons"]
    res = []
    for xi, ridge in itertools.product([0.0010, 0.0019, 0.0030, 0.0045], [0.5, 1.0, 2.0, 4.0]):
        c = component_lambdas(m, val, xi, ridge, cfg, with_market=False).dropna(subset=["tm_h", "FTHG"])
        P = np.array([list(exact_market_probs(r.tm_h, r.tm_a, r.rho).values())[:3] for r in c.itertuples()])
        yi = np.where(c.FTHG > c.FTAG, 0, np.where(c.FTHG == c.FTAG, 1, 2))
        res.append({"xi": xi, "ridge": ridge, "n": len(c), "log_loss_1x2": mx.multiclass_log_loss(P, yi)})
    return pd.DataFrame(res).sort_values("log_loss_1x2").reset_index(drop=True)


def accuracy_table(variants: dict) -> pd.DataFrame:
    """1X2 and over/under 2.5 log loss and Brier for each named prediction set,
    on the matches common to all of them."""
    common = None
    for d in variants.values():
        common = d.index if common is None else common.intersection(d.index)
    rows = []
    for name, d in variants.items():
        d = d.loc[common]
        yi = np.where(d.FTHG > d.FTAG, 0, np.where(d.FTHG == d.FTAG, 1, 2))
        P = d[["p_home", "p_draw", "p_away"]].to_numpy()
        yo = ((d.FTHG + d.FTAG) > 2.5).astype(int)
        rows.append({"model": name, "matches": len(d), "1X2 log loss": mx.multiclass_log_loss(P, yi),
                     "1X2 Brier": mx.multiclass_brier(P, yi), "O/U 2.5 log loss": mx.log_loss(d.p_over_2_5, yo),
                     "O/U 2.5 Brier": mx.brier(d.p_over_2_5, yo)})
    return pd.DataFrame(rows).set_index("model").round(5)


def paired_logloss_diff(a: pd.DataFrame, b: pd.DataFrame, seed: int = 0) -> dict:
    """Mean per-match 1X2 log-loss difference (a minus b) with a bootstrap 95% CI.
    Negative means ``a`` is better."""
    common = a.index.intersection(b.index)
    a, b = a.loc[common], b.loc[common]
    yi = np.where(a.FTHG > a.FTAG, 0, np.where(a.FTHG == a.FTAG, 1, 2))
    la = -np.log(np.clip(a[["p_home", "p_draw", "p_away"]].to_numpy()[np.arange(len(a)), yi], 1e-9, 1))
    lb = -np.log(np.clip(b[["p_home", "p_draw", "p_away"]].to_numpy()[np.arange(len(b)), yi], 1e-9, 1))
    diff = la - lb
    rng = np.random.default_rng(seed)
    boots = diff[rng.integers(0, len(diff), size=(2000, len(diff)))].mean(axis=1)
    return {"mean_diff": float(diff.mean()), "ci_low": float(np.quantile(boots, 0.025)),
            "ci_high": float(np.quantile(boots, 0.975)), "n": int(len(diff))}


def _rename_probs(d):  # p_over_2.5 -> attribute-safe copies used by the tables
    return d.rename(columns={"p_over_2.5": "p_over_2_5"})


def market_only(comp: pd.DataFrame) -> pd.DataFrame:
    """Baseline: the de-vigged sharp price alone."""
    d = predict(comp, {"market": 1.0, "team": 0.0, "shots": 0.0})
    d["p_home"], d["p_draw"], d["p_away"] = d.a_home, d.a_draw, d.a_away
    has = d.a_over.notna()
    d.loc[has, "p_over_2.5"] = d.loc[has, "a_over"]
    d.loc[has, "p_under_2.5"] = 1 - d.loc[has, "a_over"]
    return d


def run(cfg: dict | None = None, tune: bool = True) -> dict:
    cfg = cfg or load_config()
    fc = cfg["football"]
    floor = cfg["prob_floor"]
    m = add_anchor(load_matches())
    m = m.dropna(subset=["FTHG", "FTAG"])
    out = {}
    if tune:
        out["tuning"] = tune_team_model(m, cfg)
    xi, ridge, w = fc["time_decay_xi"], fc["ridge"], fc["blend"]
    for label, seasons in (("validation", fc["validation_seasons"]), ("test", fc["test_seasons"])):
        comp = component_lambdas(m, seasons, xi, ridge, cfg)
        blend = predict(comp, w, fc["dispersion"])
        base = market_only(comp)
        team = predict(comp.dropna(subset=["tm_h"]).assign(mk_h=lambda d: d.tm_h, mk_a=lambda d: d.tm_a),
                       {"market": 1.0, "team": 0.0, "shots": 0.0})
        variants = {"market only (baseline)": base, "standing blend 80/15/5": blend, "team model alone": team}
        pc = {mk: f"p_{mk}" for mk in PRICED}
        sel = selections(blend, pc, floor)
        sel_base = selections(base, pc, floor)
        fav = base.copy()
        fav_mk = fav[["B365H", "B365D", "B365A"]].apply(pd.to_numeric, errors="coerce").idxmin(axis=1)
        fav_sel = pd.concat([selections(fav[fav_mk == c], {**pc, mk: "a_" + mk}, 0.0).query("market == @mk")
                             for c, mk in (("B365H", "home"), ("B365A", "away"))]).sort_values("kickoff_utc")
        y = outcomes(blend)
        unpriced = pd.concat([pd.DataFrame({"market": mk, "market_group": MARKET_GROUP[mk], "league": blend.Div,
                                            "season": blend.season, "home_team": blend.HomeTeam,
                                            "away_team": blend.AwayTeam, "match_date": blend.match_date,
                                            "model_prob": blend[f"p_{mk}"], "won": y[mk]})
                              for mk in UNPRICED])
        out[label] = {
            "seasons": seasons, "comp": comp, "blend": blend, "base": base,
            "accuracy": accuracy_table({k: _rename_probs(v) for k, v in variants.items()}),
            "paired": paired_logloss_diff(blend, base),
            "selections": sel, "selections_market_only": sel_base, "favourites": fav_sel,
            "accas": accas(sel), "unpriced": unpriced[unpriced.model_prob >= floor],
            "anchor_sources": blend.groupby(["season", "anchor_source"]).size().unstack(fill_value=0),
            "fallbacks": int((blend.p_w_market > w["market"] + 1e-9).sum()),
        }
    out["config"] = {"xi": xi, "ridge": ridge, "blend": w, "floor": floor}
    return out


def acca_ci_line(a: pd.DataFrame) -> str:
    parts = []
    for k, g in a.groupby("bucket"):
        lo, hi = mx.roi_bootstrap_ci(g.net_units)
        parts.append(f"{k} {lo:+.2f} to {hi:+.2f} ({len(g)} slips)")
    return ("ROI 95% bootstrap intervals: " + "; ".join(parts) + ". Intervals that span zero mean the "
            "accumulator results are not evidence of an edge in either direction.")


def _tbl(df: pd.DataFrame) -> str:
    return df.to_markdown() + "\n"


def write_report(res: dict, path=REPORT) -> None:
    c = res["config"]
    L = ["# Football walk-forward backtest", "",
         f"Generated {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC from football-data.co.uk files "
         "(see data/raw/football_data/manifest.json). Leagues: Premier League, La Liga, Bundesliga, "
         "Serie A, Ligue 1.", "",
         f"Settings (frozen before the test seasons were scored): time decay xi={c['xi']}/day, ridge={c['ridge']}, "
         f"blend {c['blend']}, probability floor {c['floor']:.0%}, flat 1-unit stakes.", "",
         "How to read this: the team model is refitted before each match date using only earlier matches. "
         "Qualification and staking use the pre-match snapshot prices (Friday/Tuesday afternoon); closing "
         "prices appear only in the closing-line-value columns. Bet prices are bet365's pre-match prices as "
         "recorded by football-data.co.uk.", ""]
    if "tuning" in res:
        L += ["## Hyperparameter tuning (validation seasons only)", "",
              "Team model alone, 1X2 log loss, lower is better. Top rows:", "", _tbl(res["tuning"].head(6))]
    for label in ("validation", "test"):
        r = res[label]
        title = "Validation seasons (used for tuning - not out of sample)" if label == "validation" \
            else "Test seasons (out of sample)"
        L += [f"## {title}: {', '.join(r['seasons'])}", "",
              "### Does the model beat the market-only baseline?", "", _tbl(r["accuracy"])]
        p = r["paired"]
        verdict = ("blend is better" if p["ci_high"] < 0 else "market only is better" if p["ci_low"] > 0
                   else "no significant difference")
        L += [f"Paired 1X2 log-loss difference, blend minus market only: {p['mean_diff']:+.5f} per match "
              f"(95% bootstrap CI {p['ci_low']:+.5f} to {p['ci_high']:+.5f}, n={p['n']}): **{verdict}**.", "",
              "Sharp-price source used as the anchor, matches per season:", "", _tbl(r["anchor_sources"]),
              f"Matches where a model component was missing (promoted side or short shot history) and the "
              f"blend fell back toward the market: {r['fallbacks']}.", ""]
        sel = r["selections"]
        L += [f"### Every qualifying leg (model probability at least {c['floor']:.0%}) at bet365 prices", ""]
        rows = {"standing blend": mx.bet_summary(sel),
                "market-only baseline (same floor)": mx.bet_summary(r["selections_market_only"]),
                "flat favourite baseline (every match)": mx.bet_summary(r["favourites"])}
        L += [_tbl(pd.DataFrame(rows).T)]
        lo, hi = mx.roi_bootstrap_ci(sel.net_units)
        L += [f"Blend ROI 95% bootstrap interval: {lo:+.3f} to {hi:+.3f} per unit.", "",
              "By market:", "", _tbl(pd.DataFrame({k: mx.bet_summary(g) for k, g in sel.groupby("market")}).T),
              "By league:", "", _tbl(pd.DataFrame({k: mx.bet_summary(g) for k, g in sel.groupby("league")}).T),
              "By season:", "", _tbl(pd.DataFrame({k: mx.bet_summary(g) for k, g in sel.groupby("season")}).T),
              "Calibration of priced qualifying legs (5% buckets):", "",
              _tbl(mx.calibration_table(sel.model_prob, sel.result == "win", lo=c["floor"]))]
        u = r["unpriced"]
        L += ["### Markets with no historical bet365 price (calibration only, no ROI)", "",
              "football-data.co.uk does not record BTTS, double chance or alternative totals prices, so these "
              "legs can be checked for calibration but not for profit.", "",
              _tbl(u.groupby("market").agg(n=("won", "size"), mean_model_prob=("model_prob", "mean"),
                                           hit_rate=("won", "mean")).round(4)),
              "All unpriced qualifying legs, 5% buckets:", "",
              _tbl(mx.calibration_table(u.model_prob, u.won, lo=c["floor"]))]
        a = r["accas"]
        L += ["### Accumulators (weekly, top legs by probability, one per match)", ""]
        if len(a):
            t = pd.DataFrame({k: mx.bet_summary(g) for k, g in a.groupby("bucket")}).T
            t["avg_price"] = a.groupby("bucket").price.mean().round(2)
            t["avg_joint_model_prob"] = a.groupby("bucket").model_prob.mean().round(4)
            L += [_tbl(t), acca_ci_line(a), ""]
        else:
            L += ["No week had enough qualifying legs.", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L))


if __name__ == "__main__":
    import time
    t0 = time.time()
    result = run()
    write_report(result)
    for k in ("validation", "test"):  # saved for the Stage 6 analysis
        result[k]["selections"].assign(split=k).to_csv(CLEAN / f"backtest_football_selections_{k}.csv", index=False)
        result[k]["unpriced"].assign(split=k).to_csv(CLEAN / f"backtest_football_unpriced_{k}.csv", index=False)
    print(result["tuning"].head(5))
    for k in ("validation", "test"):
        print(k, "\n", result[k]["accuracy"], "\n", result[k]["paired"], "\n",
              mx.bet_summary(result[k]["selections"]))
    print(f"done in {time.time() - t0:.0f}s -> {REPORT}")
