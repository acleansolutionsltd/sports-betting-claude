"""Match simulation shared by every football market.

One set of seeded score draws per match feeds 1X2, totals, BTTS, handicaps and
player props, so same-game legs are always evaluated jointly on the same draws.
"""
from __future__ import annotations

import numpy as np

from .dixon_coles import MAX_GOALS, score_matrix


def blend_lambdas(market, team, shots, weights: dict):
    """Weighted blend of expected goals. The market is the anchor: with no
    market price there is no projection. Missing model components are dropped
    and the remaining weights renormalised; the weights actually used are
    returned so the fallback is visible."""
    if market is None:
        return None, {}
    parts = {"market": market, "team": team, "shots": shots}
    used = {k: weights[k] for k, v in parts.items() if v is not None and weights.get(k, 0) > 0}
    tot = sum(used.values())
    used = {k: w / tot for k, w in used.items()}
    lh = sum(w * parts[k][0] for k, w in used.items())
    la = sum(w * parts[k][1] for k, w in used.items())
    return (lh, la), used


def simulate_scores(lh: float, la: float, rho: float, n: int, rng: np.random.Generator,
                    dispersion: float | None = None):
    """Draw n scorelines from the Dixon-Coles score matrix."""
    m = score_matrix(lh, la, rho, dispersion)
    flat = rng.choice(m.size, size=n, p=m.ravel())
    return flat // (MAX_GOALS + 1), flat % (MAX_GOALS + 1)


def exact_market_probs(lh: float, la: float, rho: float, dispersion: float | None = None) -> dict:
    """Closed-form market probabilities from the score matrix (no sampling noise).
    Used by the backtest; the live run uses draws so legs can be combined."""
    m = score_matrix(lh, la, rho, dispersion)
    i, j = np.indices(m.shape)
    p = {"home": m[i > j].sum(), "draw": m[i == j].sum(), "away": m[i < j].sum(),
         "btts_yes": m[(i > 0) & (j > 0)].sum()}
    for line in (0.5, 1.5, 2.5, 3.5, 4.5):
        p[f"over_{line}"] = m[(i + j) > line].sum()
        p[f"under_{line}"] = 1 - p[f"over_{line}"]
    p["btts_no"] = 1 - p["btts_yes"]
    p["dc_1x"], p["dc_x2"], p["dc_12"] = p["home"] + p["draw"], p["away"] + p["draw"], p["home"] + p["away"]
    return {k: float(v) for k, v in p.items()}


def leg_hits(hg: np.ndarray, ag: np.ndarray) -> dict:
    """Per-simulation outcome of every team market.

    Returns {market_key: (win, push)} with boolean arrays; push is None when the
    market cannot void. Keys match ``settle``.
    """
    tot, diff = hg + ag, hg - ag
    legs = {
        "1x2:home": (diff > 0, None), "1x2:draw": (diff == 0, None), "1x2:away": (diff < 0, None),
        "dc:1x": (diff >= 0, None), "dc:x2": (diff <= 0, None), "dc:12": (diff != 0, None),
        "btts:yes": ((hg > 0) & (ag > 0), None), "btts:no": ((hg == 0) | (ag == 0), None),
    }
    for line in (0.5, 1.5, 2.5, 3.5, 4.5, 5.5):
        legs[f"total:over_{line}"] = (tot > line, None)
        legs[f"total:under_{line}"] = (tot < line, None)
    for line in (0.5, 1.5, 2.5):
        legs[f"home_total:over_{line}"] = (hg > line, None)
        legs[f"away_total:over_{line}"] = (ag > line, None)
    for line in np.arange(-3.0, 3.5, 0.5):  # Asian handicap on the home side; whole lines can push
        adj = diff + line
        push = (adj == 0) if float(line).is_integer() else None
        legs[f"ah:home_{line:+.1f}"] = (adj > 0, push)
        legs[f"ah:away_{-line:+.1f}"] = (adj < 0, push)
    return legs


def settle(market_key: str, hg: int, ag: int) -> str:
    """Grade one market on a final score: 'win', 'loss' or 'void'."""
    win, push = leg_hits(np.array([hg]), np.array([ag]))[market_key]
    if push is not None and push[0]:
        return "void"
    return "win" if win[0] else "loss"
