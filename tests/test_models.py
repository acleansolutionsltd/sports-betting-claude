import numpy as np
import pandas as pd
import pytest

from betting_model.models.football import dixon_coles as dc
from betting_model.models.football import props as fprops
from betting_model.models.football import sim as fsim
from betting_model.models.nfl import props as nprops
from betting_model.models.nfl import score_pair as sp


def _league(n_teams=10, seasons=3, seed=0):
    rng = np.random.default_rng(seed)
    strength = np.linspace(0.4, -0.4, n_teams)
    rows, day = [], pd.Timestamp("2022-08-01")
    for _ in range(seasons):
        for h in range(n_teams):
            for a in range(n_teams):
                if h != a:
                    day += pd.Timedelta(days=1)
                    lh, la = np.exp(0.45 + strength[h] - strength[a]), np.exp(0.2 + strength[a] - strength[h])
                    rows.append((day, f"T{h}", f"T{a}", rng.poisson(lh), rng.poisson(la),
                                 rng.poisson(4 * lh), rng.poisson(4 * la)))
    return pd.DataFrame(rows, columns=["match_date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "HST", "AST"])


def test_score_matrix_is_a_distribution():
    for disp in (None, 0.1):
        m = dc.score_matrix(1.6, 1.1, -0.08, disp)
        assert m.sum() == pytest.approx(1.0)
        assert (m >= 0).all()
    assert dc.score_matrix(1.6, 1.1, 0, 0.3)[6:, :].sum() > dc.score_matrix(1.6, 1.1, 0)[6:, :].sum()  # fatter tail


def test_market_lambdas_round_trip():
    m = dc.score_matrix(1.9, 0.9, -0.05)
    ph, pd_, pa, po = dc.probs_1x2_over(m)
    lh, la = dc.lambdas_from_market(ph, pd_, pa, po, -0.05)
    assert (lh, la) == pytest.approx((1.9, 0.9), abs=1e-3)
    assert dc.lambdas_from_market(np.nan, pd_, pa, po) is None


def test_fit_recovers_order_and_never_sees_the_future():
    d = _league()
    cutoff = d.match_date.iloc[len(d) // 2]
    m = dc.fit(d, cutoff, xi=0.001)
    assert m.att["T0"] - m.dfn["T9"] > m.att["T9"] - m.dfn["T0"]
    assert m.home > 0
    # changing every result on or after the cutoff must not change the fit
    d2 = d.copy()
    d2.loc[d2.match_date >= cutoff, ["FTHG", "FTAG"]] = 9
    m2 = dc.fit(d2, cutoff, xi=0.001)
    assert m2.att == pytest.approx(m.att) and m2.rho == pytest.approx(m.rho)
    assert m.lambdas("T0", "Unknown FC") is None  # no history -> no guess


def test_blend_needs_market_and_renormalises():
    w = {"market": 0.8, "team": 0.15, "shots": 0.05}
    assert fsim.blend_lambdas(None, (1.5, 1.0), (1.4, 1.1), w)[0] is None
    lam, used = fsim.blend_lambdas((2.0, 1.0), None, (1.0, 2.0), w)
    assert used == pytest.approx({"market": 0.8 / 0.85, "shots": 0.05 / 0.85})
    assert lam[0] == pytest.approx(2.0 * 0.8 / 0.85 + 1.0 * 0.05 / 0.85)


def test_football_sim_matches_exact_probs_and_settles():
    rng = np.random.default_rng(7)
    hg, ag = fsim.simulate_scores(1.7, 1.2, -0.06, 200_000, rng)
    exact = fsim.exact_market_probs(1.7, 1.2, -0.06)
    hits = fsim.leg_hits(hg, ag)
    assert hits["1x2:home"][0].mean() == pytest.approx(exact["home"], abs=0.005)
    assert hits["btts:yes"][0].mean() == pytest.approx(exact["btts_yes"], abs=0.005)
    assert hits["total:over_2.5"][0].mean() == pytest.approx(exact["over_2.5"], abs=0.005)
    assert fsim.settle("ah:home_-1.0", 2, 1) == "void"
    assert fsim.settle("ah:home_-1.0", 3, 1) == "win"
    assert fsim.settle("ah:away_+1.0", 3, 1) == "loss"
    assert fsim.settle("btts:no", 2, 0) == "win"


def test_football_props_consistent_with_match_and_skip_when_missing():
    rng = np.random.default_rng(5)
    hg, _ = fsim.simulate_scores(1.8, 1.0, -0.05, 50_000, rng)
    out = fprops.sim_player(
        "Striker", team_goals=hg, team_lambda=1.8, team_baseline_goals=1.5, p_start=0.9,
        minutes_if_start=80, minutes_if_sub=20, shots_per90=3.2, sot_per90=1.3, goal_share=0.3, rng=rng)
    shots, sot, goals = out["shots"].draws, out["shots_on_target"].draws, out["goals"].draws
    assert (goals <= hg).all() and (goals <= sot).all() and (sot <= shots).all()
    assert shots.mean() == pytest.approx(3.2 * 1.2 * (0.9 * 80 + 0.1 * 20) / 90, rel=0.05)
    skipped = fprops.sim_player("NoMinutes", team_goals=hg, team_lambda=1.8, team_baseline_goals=1.5,
                                p_start=None, minutes_if_start=80, minutes_if_sub=20, shots_per90=3.2,
                                sot_per90=1.3, goal_share=0.3, rng=rng)
    assert all(p.skipped and "p_start" in p.reason for p in skipped.values())
    card = fprops.sim_card("Mid", cards_per90=0.25, referee_factor=None, intensity=1.0, exp_minutes=85, n=10, rng=rng)
    assert card.skipped and "referee_factor" in card.reason


def _pool(n=3000, seed=0):
    rng = np.random.default_rng(seed)
    spread = rng.choice(np.arange(-10, 10.5, 0.5), n)
    total = rng.choice(np.arange(37, 54.5, 0.5), n)
    home = np.clip(np.round((total + spread) / 2 + rng.normal(0, 9.5, n)), 0, None)
    away = np.clip(np.round((total - spread) / 2 + rng.normal(0, 9.5, n)), 0, None)
    df = pd.DataFrame({"home_score": home, "away_score": away, "spread_line": spread, "total_line": total})
    for s in ("home", "away"):
        df[f"{s}_pass_att"], df[f"{s}_carries"] = rng.poisson(34, n), rng.poisson(27, n)
        df[f"{s}_pass_td"], df[f"{s}_rush_td"] = rng.poisson(1.5, n), rng.poisson(0.9, n)
    return df


def test_maxent_weights_match_market():
    pool = _pool()
    w, diag = sp.fit_weights(pool, 6.5, 44.5, 0.74, 0.51, 0.48)
    m = pool.home_score - pool.away_score
    t = pool.home_score + pool.away_score
    assert w.sum() == pytest.approx(1) and (w >= 0).all()
    assert (w @ (m > 0)) / (w @ (m != 0)) == pytest.approx(0.74, abs=1e-3)
    assert w @ (m > 6.5) == pytest.approx(0.51, abs=1e-3)
    assert w @ (t > 44.5) == pytest.approx(0.48, abs=1e-3)
    assert diag["effective_sample"] > 100


def test_nfl_settle_and_pushes():
    assert sp.settle("ml:home", 20, 20) == "void"
    assert sp.settle("spread:home_-3.0", 23, 20) == "void"
    assert sp.settle("spread:home_-3.5", 24, 20) == "win"
    assert sp.settle("spread:away_+3.5", 24, 20) == "loss"
    assert sp.settle("total:under_44.5", 24, 20) == "win"
    assert sp.settle("away_total:over_20.5", 24, 20) == "loss"
    hits = sp.leg_hits(np.array([23]), np.array([20]), 3.0, 43.0)
    assert hits["spread:home_-3.0"][1][0] and hits["total:over_43.0"][1][0]


def test_nfl_props_shapes_and_skips():
    pool = _pool()
    w, _ = sp.fit_weights(pool, 3.0, 45.5, 0.6, 0.5, 0.5)
    rng = np.random.default_rng(2)
    d = sp.simulate(pool, w, 40_000, rng)
    rec, yds = nprops.sim_receiving("WR1", d["home_pass_att"], 0.25, 0.65, 12.0, rng)
    assert rec.draws.mean() == pytest.approx(d["home_pass_att"].mean() * 0.25 * 0.65, rel=0.03)
    assert yds.draws.mean() == pytest.approx(rec.draws.mean() * 12.0, rel=0.05)
    assert set(rec.summary()) >= {"mean", "median", "p10", "p90"}
    pr = rec.prob("over", 5.5)
    assert 0 < pr["win"] < 1 and pr["push"] == 0
    skipped, _ = nprops.sim_receiving("WR2", d["home_pass_att"], None, 0.65, 12.0, rng)
    assert skipped.skipped and "target_share" in skipped.reason
    no_vol, _ = nprops.sim_receiving("WR3", None, 0.2, 0.65, 12.0, rng)
    assert no_vol.skipped
    tds = nprops.sim_touchdowns(d["home_rush_td"], d["home_pass_td"], {"QB": 0.15, "RB": 0.6}, {"RB": 0.1, "WR1": 0.3}, rng)
    assert tds["QB"].draws.mean() == pytest.approx(d["home_rush_td"].mean() * 0.15, rel=0.1)  # rushing only
    total_td = d["home_rush_td"] + d["home_pass_td"]
    assert (tds["QB"].draws + tds["RB"].draws + tds["WR1"].draws <= total_td).all()
