"""Stage 5 - walk-forward backtest for the NFL score-pair model.

For every game in the test seasons the pool contains only games that kicked off
before that game's week. Because the model is re-weighted to match the
de-vigged moneyline, spread and total, those three markets equal the market by
construction; what is being tested is everything derived from the score
distribution (alternative spreads and totals, team totals), against two
baselines: a normal distribution and an un-kernelled bootstrap.

Prices: nflverse stores one consensus line per game (effectively the close), so
this is a bet-at-the-close backtest and the prices are not bet365's.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from ..config import CLEAN, ROOT, load_config
from ..ev.odds import american_to_decimal_array
from ..models.nfl import score_pair as sp
from . import metrics as mx

REPORT = ROOT / "backtest" / "reports" / "nfl.md"


def load_games() -> pd.DataFrame:
    g = pd.read_csv(CLEAN / "nfl_games.csv", low_memory=False)
    g["kickoff_utc"] = pd.to_datetime(g.kickoff_utc, utc=True)
    return g


def _family(key: str) -> str:
    kind = key.split(":")[0]
    return {"ml": "moneyline", "spread": "alt spread", "total": "alt total"}.get(kind, "team total")


def _weighted_leg_probs(pool, w, spread, total):
    hits = sp.leg_hits(pool.home_score.to_numpy(int), pool.away_score.to_numpy(int), spread, total)
    out = {}
    for k, (win, push) in hits.items():
        pp = float(w @ push) if push is not None else 0.0
        out[k] = float(w @ win) / max(1 - pp, 1e-9)
    return out


def _normal_leg_probs(spread, total, p_cover, p_over, sd_m, sd_t):
    """Baseline: margin and total independent normals matched to the same prices."""
    mu_m = spread + 0.0 - sd_m * norm.ppf(1 - p_cover)
    mu_t = total - sd_t * norm.ppf(1 - p_over)
    sd_team = np.sqrt(sd_m ** 2 + sd_t ** 2) / 2
    out = {}
    for d in (-10, -7, -6.5, -3.5, -3, 3, 3.5, 6.5, 7, 10):
        line = spread + d
        ph = norm.sf((line - mu_m) / sd_m)
        out[f"spread:home_{-line:+.1f}"], out[f"spread:away_{line:+.1f}"] = ph, 1 - ph
        tl = total + d
        po = norm.sf((tl - mu_t) / sd_t)
        out[f"total:over_{tl:.1f}"], out[f"total:under_{tl:.1f}"] = po, 1 - po
    for side, mu in (("home", (mu_t + mu_m) / 2), ("away", (mu_t - mu_m) / 2)):
        for tl in (13.5, 16.5, 20.5, 23.5, 27.5):
            po = norm.sf((tl - mu) / sd_team)
            out[f"{side}_total:over_{tl}"], out[f"{side}_total:under_{tl}"] = po, 1 - po
    return out


def run(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    nc = cfg["nfl"]
    floor = cfg["prob_floor"]
    games = load_games()
    tg = sp.market_targets(games)
    games = games.join(tg)
    test = games[(games.game_type == "REG") & games.season.isin(nc["test_seasons"])
                 & games.home_score.notna()].dropna(subset=["p_home", "p_cover", "p_over"])
    legs, diags, ml = [], [], []
    for (season, week), wk in test.groupby(["season", "week"]):
        pool = sp.build_pool(games, wk.kickoff_utc.min(), nc["pool_start_season"])
        sd_m = float((pool.home_score - pool.away_score - pool.spread_line).std())
        sd_t = float((pool.home_score + pool.away_score - pool.total_line).std())
        for r in wk.itertuples():
            w, diag = sp.fit_weights(pool, r.spread_line, r.total_line, r.p_home, r.p_cover, r.p_over,
                                     nc["kernel_bw"]["spread"], nc["kernel_bw"]["total"])
            wu, _ = sp.fit_weights(pool, r.spread_line, r.total_line, r.p_home, r.p_cover, r.p_over, 1e6, 1e6)
            diags.append({"game_id": r.game_id, **diag})
            pb = _weighted_leg_probs(pool, w, r.spread_line, r.total_line)
            pu = _weighted_leg_probs(pool, wu, r.spread_line, r.total_line)
            pn = _normal_leg_probs(r.spread_line, r.total_line, r.p_cover, r.p_over, sd_m, sd_t)
            for k, p in pb.items():
                if k not in pn:
                    continue  # main-line moneyline/spread/total equal the market by construction
                res = sp.settle(k, int(r.home_score), int(r.away_score))
                legs.append((r.game_id, season, week, k, _family(k), p, pu[k], pn[k], res))
            for side, p, price in (("home", r.p_home, r.home_moneyline), ("away", 1 - r.p_home, r.away_moneyline)):
                res = sp.settle(f"ml:{side}", int(r.home_score), int(r.away_score))
                dec = float(american_to_decimal_array([price])[0])
                ml.append({"game_id": r.game_id, "season": season, "week": week, "kickoff_utc": r.kickoff_utc,
                           "market": f"ml:{side}", "model_prob": p, "price": dec, "result": res,
                           "stake_units": 1.0,
                           "net_units": dec - 1 if res == "win" else 0.0 if res == "void" else -1.0})
    legs = pd.DataFrame(legs, columns=["game_id", "season", "week", "market", "family", "p_bootstrap",
                                       "p_uniform_bootstrap", "p_normal", "result"])
    ml = pd.DataFrame(ml).sort_values("kickoff_utc")
    return {"legs": legs, "ml": ml, "diag": pd.DataFrame(diags), "floor": floor, "games": len(test),
            "seasons": nc["test_seasons"], "cfg": nc}


def write_report(res: dict, path=REPORT) -> None:
    legs, ml, floor = res["legs"], res["ml"], res["floor"]
    settled = legs[legs.result != "void"].assign(won=lambda d: (d.result == "win").astype(int))
    L = ["# NFL walk-forward backtest", "",
         f"Generated {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC from nflverse games.csv. "
         f"Test seasons {res['seasons']} (regular season, completed games: {res['games']}). "
         f"Pool: all regular-season games since {res['cfg']['pool_start_season']} that kicked off before the "
         "week being predicted.", "",
         "Caveats: nflverse holds one consensus line per game, effectively the closing line, so this is a "
         "bet-at-the-close test and the prices are not bet365 prices. Alternative lines and team totals have "
         "no historical prices, so they are tested for accuracy and calibration only.", "",
         "## Fit quality", ""]
    d = res["diag"]
    L += [f"Largest error matching the three market probabilities: {d.max_constraint_error.max():.2e}. "
          f"Effective sample size of the weighted pool: median {d.effective_sample.median():.0f}, "
          f"minimum {d.effective_sample.min():.0f} "
          f"(games below {res['cfg']['min_effective_sample']}: "
          f"{int((d.effective_sample < res['cfg']['min_effective_sample']).sum())}).", "",
          "## Derived markets: bootstrap vs baselines (all legs, lower log loss is better)", ""]
    rows = []
    for fam, g in list(settled.groupby("family")) + [("all derived", settled)]:
        rows.append({"family": fam, "legs": len(g),
                     "kernel bootstrap (model)": mx.log_loss(g.p_bootstrap, g.won),
                     "uniform bootstrap": mx.log_loss(g.p_uniform_bootstrap, g.won),
                     "normal baseline": mx.log_loss(g.p_normal, g.won)})
    L += [pd.DataFrame(rows).set_index("family").round(5).to_markdown(), ""]
    per_game = settled.assign(
        ll_b=lambda x: -(x.won * np.log(x.p_bootstrap.clip(1e-9, 1)) + (1 - x.won) * np.log((1 - x.p_bootstrap).clip(1e-9, 1))),
        ll_n=lambda x: -(x.won * np.log(x.p_normal.clip(1e-9, 1)) + (1 - x.won) * np.log((1 - x.p_normal).clip(1e-9, 1)))
    ).groupby("game_id")[["ll_b", "ll_n"]].mean()
    diff = (per_game.ll_b - per_game.ll_n).to_numpy()
    rng = np.random.default_rng(0)
    boots = diff[rng.integers(0, len(diff), size=(2000, len(diff)))].mean(axis=1)
    lo, hi = np.quantile(boots, [0.025, 0.975])
    verdict = "bootstrap is better" if hi < 0 else "normal is better" if lo > 0 else "no significant difference"
    L += [f"Paired difference, kernel bootstrap minus normal, resampling whole games: {diff.mean():+.5f} "
          f"(95% CI {lo:+.5f} to {hi:+.5f}): **{verdict}**.", "",
          f"## Calibration of derived legs at or above the {floor:.0%} floor", ""]
    q = settled[settled.p_bootstrap >= floor]
    L += [mx.calibration_table(q.p_bootstrap, q.won, lo=floor).to_markdown(), "", "By family:", "",
          q.groupby("family").agg(n=("won", "size"), mean_model_prob=("p_bootstrap", "mean"),
                                  hit_rate=("won", "mean")).round(4).to_markdown(), "",
          f"## Moneyline legs at or above {floor:.0%} (consensus closing price, flat 1 unit)", "",
          "The model's moneyline probability equals the de-vigged market, so this row is the market-only "
          "baseline; the second row backs every favourite regardless of price.", ""]
    fav = ml[ml.model_prob > 0.5]
    qual = ml[ml.model_prob >= floor]
    L += [pd.DataFrame({f"moneyline >= {floor:.0%}": mx.bet_summary(qual),
                        "every favourite": mx.bet_summary(fav)}).T.to_markdown(), "",
          "By season:", "", pd.DataFrame({k: mx.bet_summary(g) for k, g in qual.groupby("season")}).T.to_markdown(), "",
          mx.calibration_table(qual.model_prob, qual.result == "win", lo=floor).to_markdown(), ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L))


if __name__ == "__main__":
    out = run()
    write_report(out)
    out["legs"].to_csv(CLEAN / "backtest_nfl_legs.csv", index=False)  # saved for the Stage 6 analysis
    print(REPORT.read_text())
