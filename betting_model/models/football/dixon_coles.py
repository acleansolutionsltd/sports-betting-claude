"""Stage 1 - football core model.

Dixon-Coles adjusted Poisson: team attack and defence strengths with
exponential time decay, a per-league home advantage and the low-score
correction (rho). Negative-binomial marginals are available for fatter tails
via ``dispersion``; it stays off until it wins a Stage 5 test.

Leakage guard: ``fit`` only ever sees matches strictly before ``as_of``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import optimize, stats

MAX_GOALS = 10


def _tau(rho: float, lh: float, la: float) -> np.ndarray:
    """Dixon-Coles correction factors for the 0-0, 0-1, 1-0 and 1-1 cells."""
    t = np.ones((2, 2))
    t[0, 0] = 1 - lh * la * rho
    t[0, 1] = 1 + lh * rho
    t[1, 0] = 1 + la * rho
    t[1, 1] = 1 - rho
    return np.clip(t, 1e-6, None)


def score_matrix(lh: float, la: float, rho: float = 0.0, dispersion: float | None = None,
                 max_goals: int = MAX_GOALS) -> np.ndarray:
    """P(home goals = i, away goals = j) as an (max_goals+1) square matrix."""
    k = np.arange(max_goals + 1)
    if dispersion:
        n = 1.0 / dispersion
        ph = stats.nbinom.pmf(k, n, n / (n + lh))
        pa = stats.nbinom.pmf(k, n, n / (n + la))
    else:
        ph = stats.poisson.pmf(k, lh)
        pa = stats.poisson.pmf(k, la)
    m = np.outer(ph, pa)
    m[:2, :2] *= _tau(rho, lh, la)
    return m / m.sum()


def probs_1x2_over(m: np.ndarray, line: float = 2.5) -> tuple[float, float, float, float]:
    i, j = np.indices(m.shape)
    return (float(m[i > j].sum()), float(m[i == j].sum()), float(m[i < j].sum()),
            float(m[(i + j) > line].sum()))


@dataclass
class TeamModel:
    mu: float
    home: float
    att: dict
    dfn: dict
    rho: float
    n_matches: dict = field(default_factory=dict)
    as_of: pd.Timestamp | None = None

    def lambdas(self, home_team: str, away_team: str, min_matches: int = 0):
        """Expected goals, or None if either team has too little history
        (a promoted side is not guessed at - the blend falls back to the market)."""
        for t in (home_team, away_team):
            if t not in self.att or self.n_matches.get(t, 0) < min_matches:
                return None
        lh = np.exp(self.mu + self.home + self.att[home_team] - self.dfn[away_team])
        la = np.exp(self.mu + self.att[away_team] - self.dfn[home_team])
        return float(lh), float(la)


def fit(matches: pd.DataFrame, as_of, xi: float, ridge: float = 1.0,
        history_days: int = 1095) -> TeamModel | None:
    """Fit on one league's matches played strictly before ``as_of``.

    matches needs: match_date, HomeTeam, AwayTeam, FTHG, FTAG.
    xi is the time-decay rate per day (weight = exp(-xi * days_ago)).
    """
    as_of = pd.Timestamp(as_of)
    d = matches[(matches["match_date"] < as_of)
                & (matches["match_date"] >= as_of - pd.Timedelta(days=history_days))]
    d = d.dropna(subset=["FTHG", "FTAG"])
    if len(d) < 100:
        return None
    teams = sorted(set(d["HomeTeam"]) | set(d["AwayTeam"]))
    idx = {t: i for i, t in enumerate(teams)}
    T = len(teams)
    h = d["HomeTeam"].map(idx).to_numpy()
    a = d["AwayTeam"].map(idx).to_numpy()
    hg = d["FTHG"].to_numpy(float)
    ag = d["FTAG"].to_numpy(float)
    w = np.exp(-xi * (as_of - d["match_date"]).dt.days.to_numpy(float))

    def nll(p):
        mu, home, att, dfn = p[0], p[1], p[2:2 + T], p[2 + T:]
        lh = np.exp(mu + home + att[h] - dfn[a])
        la = np.exp(mu + att[a] - dfn[h])
        ll = (w * (hg * np.log(lh) - lh + ag * np.log(la) - la)).sum()
        rh, ra = w * (hg - lh), w * (ag - la)
        g = np.empty_like(p)
        g[0] = rh.sum() + ra.sum()
        g[1] = rh.sum()
        g[2:2 + T] = np.bincount(h, rh, T) + np.bincount(a, ra, T) - ridge * att
        g[2 + T:] = -np.bincount(a, rh, T) - np.bincount(h, ra, T) - ridge * dfn
        pen = 0.5 * ridge * ((att ** 2).sum() + (dfn ** 2).sum())
        return -(ll - pen), -g

    x0 = np.zeros(2 + 2 * T)
    x0[0] = np.log(max((hg.mean() + ag.mean()) / 2, 0.1))
    res = optimize.minimize(nll, x0, jac=True, method="L-BFGS-B")
    mu, home, att, dfn = res.x[0], res.x[1], res.x[2:2 + T], res.x[2 + T:]
    lh = np.exp(mu + home + att[h] - dfn[a])
    la = np.exp(mu + att[a] - dfn[h])

    def rho_nll(rho):
        t = np.ones(len(hg))
        m00, m01, m10, m11 = ((hg == 0) & (ag == 0), (hg == 0) & (ag == 1),
                              (hg == 1) & (ag == 0), (hg == 1) & (ag == 1))
        t[m00] = 1 - lh[m00] * la[m00] * rho
        t[m01] = 1 + lh[m01] * rho
        t[m10] = 1 + la[m10] * rho
        t[m11] = 1 - rho
        return -(w * np.log(np.clip(t, 1e-6, None))).sum()

    rho = optimize.minimize_scalar(rho_nll, bounds=(-0.25, 0.25), method="bounded").x
    counts = np.bincount(np.concatenate([h, a]), minlength=T)
    return TeamModel(float(mu), float(home), dict(zip(teams, att)), dict(zip(teams, dfn)), float(rho),
                     dict(zip(teams, counts.tolist())), as_of)


def lambdas_from_market(p_home: float, p_draw: float, p_away: float, p_over25: float | None,
                        rho: float = 0.0, dispersion: float | None = None):
    """Expected goals implied by de-vigged 1X2 and over/under 2.5 prices.

    Least-squares match of the score matrix to the market probabilities. With no
    totals price the 1X2 probabilities alone pin down both lambdas.
    """
    target = [p_home, p_draw, p_away] + ([p_over25] if p_over25 is not None and np.isfinite(p_over25) else [])
    if not np.isfinite(target).all():
        return None
    target = np.array(target)

    def resid(x):
        ph, pd_, pa, po = probs_1x2_over(score_matrix(np.exp(x[0]), np.exp(x[1]), rho, dispersion))
        return np.array([ph, pd_, pa, po][: len(target)]) - target

    res = optimize.least_squares(resid, np.log([1.5, 1.2]), bounds=(np.log(0.05), np.log(6.0)),
                                 xtol=1e-7, ftol=1e-9)
    return float(np.exp(res.x[0])), float(np.exp(res.x[1]))


def shots_form(matches: pd.DataFrame, as_of, window: int = 8, min_matches: int = 5) -> dict:
    """Recent shots-on-target form per team from matches before ``as_of``.

    Returns {team: (sot_for_ratio, sot_against_ratio)} relative to the league
    average, plus '_league' -> (home sot avg, away sot avg, goals per sot).
    """
    as_of = pd.Timestamp(as_of)
    d = matches[(matches["match_date"] < as_of) & (matches["match_date"] >= as_of - pd.Timedelta(days=400))]
    d = d.dropna(subset=["HST", "AST", "FTHG", "FTAG"])
    if len(d) < 50:
        return {}
    long = pd.concat([
        pd.DataFrame({"team": d.HomeTeam, "date": d.match_date, "f": d.HST, "a": d.AST}),
        pd.DataFrame({"team": d.AwayTeam, "date": d.match_date, "f": d.AST, "a": d.HST}),
    ]).sort_values("date")
    avg = (d.HST.mean() + d.AST.mean()) / 2
    out = {"_league": (float(d.HST.mean()), float(d.AST.mean()),
                       float((d.FTHG.sum() + d.FTAG.sum()) / max(d.HST.sum() + d.AST.sum(), 1)))}
    for team, g in long.groupby("team"):
        g = g.tail(window)
        if len(g) >= min_matches:
            out[team] = (float(g.f.mean() / avg), float(g.a.mean() / avg))
    return out


def shots_lambdas(form: dict, home_team: str, away_team: str):
    if home_team not in form or away_team not in form or "_league" not in form:
        return None
    h_avg, a_avg, conv = form["_league"]
    return (conv * h_avg * form[home_team][0] * form[away_team][1],
            conv * a_avg * form[away_team][0] * form[home_team][1])
