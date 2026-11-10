"""Stage 1 - NFL core model: empirical score-pair bootstrap.

The pool is every completed regular-season game before the game being priced.
Each pool game gets a weight; the weights are the maximum-entropy adjustment of
a kernel prior (games with a similar spread and total count more) such that the
weighted win, cover and over probabilities equal the de-vigged market prices.
Sampling score pairs with those weights keeps real NFL margins (3s, 7s, 10s)
and totals, which a normal distribution smooths away.

Convention (nflverse): spread_line > 0 means the home team is favoured by that
many points; the home side covers when home - away > spread_line.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import optimize

from ...ev.odds import american_to_decimal_array, devig_power

VOLUME_COLS = ["pass_att", "carries", "pass_td", "rush_td"]


def build_pool(games: pd.DataFrame, before_utc, start_season: int) -> pd.DataFrame:
    """Completed regular-season games that kicked off before ``before_utc``."""
    g = games[(games.game_type == "REG") & (games.season >= start_season)
              & (games.kickoff_utc < before_utc)].dropna(subset=["home_score", "away_score"])
    return g.reset_index(drop=True)


def market_targets(games: pd.DataFrame) -> pd.DataFrame:
    """De-vigged moneyline, spread and total probabilities for each game."""
    out = pd.DataFrame(index=games.index)
    ml = devig_power(np.column_stack([american_to_decimal_array(games.home_moneyline),
                                      american_to_decimal_array(games.away_moneyline)]))
    sp = devig_power(np.column_stack([american_to_decimal_array(games.home_spread_odds),
                                      american_to_decimal_array(games.away_spread_odds)]))
    to = devig_power(np.column_stack([american_to_decimal_array(games.over_odds),
                                      american_to_decimal_array(games.under_odds)]))
    out["p_home"], out["p_cover"], out["p_over"] = ml[:, 0], sp[:, 0], to[:, 0]
    return out


def fit_weights(pool: pd.DataFrame, spread: float, total: float, p_home: float, p_cover: float,
                p_over: float, bw_spread: float = 4.0, bw_total: float = 5.0):
    """Maximum-entropy weights matching the three market probabilities.

    Ties and pushes are treated as voids: the constraint is on the probability
    conditional on the bet not being void, which is what a de-vigged two-way
    price describes.
    """
    hs, as_ = pool.home_score.to_numpy(float), pool.away_score.to_numpy(float)
    margin, tot = hs - as_, hs + as_
    z = ((pool.spread_line.to_numpy(float) - spread) / bw_spread) ** 2 \
        + ((pool.total_line.to_numpy(float) - total) / bw_total) ** 2
    base = np.exp(-0.5 * np.nan_to_num(z, nan=8.0))
    base /= base.sum()
    G = np.column_stack([
        (margin > 0) - p_home * (margin != 0),
        (margin > spread) - p_cover * (margin != spread),
        (tot > total) - p_over * (tot != total),
    ]).astype(float)

    def dual(theta):
        s = G @ theta
        mx = s.max()
        e = base * np.exp(s - mx)
        zsum = e.sum()
        return mx + np.log(zsum) + 1e-6 * theta @ theta, (e / zsum) @ G + 2e-6 * theta

    res = optimize.minimize(dual, np.zeros(3), jac=True, method="BFGS")
    s = G @ res.x
    w = base * np.exp(s - s.max())
    w /= w.sum()
    diag = {"max_constraint_error": float(np.abs(w @ G).max()),
            "effective_sample": float(1.0 / (w ** 2).sum()), "pool_size": int(len(pool))}
    return w, diag


def simulate(pool: pd.DataFrame, weights: np.ndarray, n: int, rng: np.random.Generator) -> dict:
    """Draw n historical games with the fitted weights. Each draw carries the
    whole game (scores and, where the pool has them, play volumes and touchdown
    counts), so every market and prop from one run is jointly consistent."""
    idx = rng.choice(len(pool), size=n, p=weights)
    out = {"home": pool.home_score.to_numpy(int)[idx], "away": pool.away_score.to_numpy(int)[idx]}
    for side in ("home", "away"):
        for c in VOLUME_COLS:
            col = f"{side}_{c}"
            if col in pool:
                out[col] = pool[col].to_numpy(float)[idx]
    return out


def leg_hits(home: np.ndarray, away: np.ndarray, spread: float, total: float) -> dict:
    """Per-simulation (win, push) arrays for team markets, including alternative
    lines around the main spread and total. Keys match ``settle``."""
    margin, tot = home - away, home + away
    legs = {"ml:home": (margin > 0, margin == 0), "ml:away": (margin < 0, margin == 0)}
    for d in (-10, -7, -6.5, -3.5, -3, 0, 3, 3.5, 6.5, 7, 10):
        line = spread + d  # home must win by more than this
        legs[f"spread:home_{-line:+.1f}"] = (margin > line, margin == line)
        legs[f"spread:away_{line:+.1f}"] = (margin < line, margin == line)
        tl = total + d
        legs[f"total:over_{tl:.1f}"] = (tot > tl, tot == tl)
        legs[f"total:under_{tl:.1f}"] = (tot < tl, tot == tl)
    for side, pts in (("home", home), ("away", away)):
        for tl in (13.5, 16.5, 20.5, 23.5, 27.5):
            legs[f"{side}_total:over_{tl}"] = (pts > tl, None)
            legs[f"{side}_total:under_{tl}"] = (pts < tl, None)
    return legs


def settle(market_key: str, home: int, away: int) -> str:
    """Grade a market key on a final score. Line values are read from the key."""
    kind, sel = market_key.split(":")
    side, _, val = sel.partition("_")
    margin, tot = home - away, home + away
    if kind == "ml":
        x = margin if side == "home" else -margin
    elif kind == "spread":
        x = (margin if side == "home" else -margin) + float(val)
    elif kind == "total":
        x = (tot - float(val)) * (1 if side == "over" else -1)
    else:  # home_total / away_total
        pts = home if kind.startswith("home") else away
        x = (pts - float(val)) * (1 if side == "over" else -1)
    return "void" if x == 0 else "win" if x > 0 else "loss"


def add_team_volumes(games: pd.DataFrame, player_weeks: pd.DataFrame) -> pd.DataFrame:
    """Attach each team's pass attempts, carries and passing/rushing touchdowns
    to its games, from player weekly stats. Games without stats keep NaN."""
    if len(player_weeks) == 0:
        return games
    t = player_weeks.groupby(["season", "week", "team"]).agg(
        pass_att=("attempts", "sum"), carries=("carries", "sum"),
        pass_td=("passing_tds", "sum"), rush_td=("rushing_tds", "sum")).reset_index()
    g = games
    for side in ("home", "away"):
        g = g.merge(t.rename(columns={"team": f"{side}_team", **{c: f"{side}_{c}" for c in VOLUME_COLS}}),
                    on=["season", "week", f"{side}_team"], how="left")
    return g
