"""Stage 4 - slip builder.

Standing rules implemented here:
  * every leg must be at least the probability floor (65%);
  * choose the combination with the highest joint model probability whose
    combined price falls inside the target band;
  * legs from different matches multiply; legs from the same match are never
    multiplied - their joint probability comes from the shared simulation draws
    (``joint_prob_from_draws``) and the Bet Builder price must be the one quoted
    by the bookmaker, entered as a single composite leg;
  * the result reports both the model joint probability and the price-implied
    probability, because a high joint probability is not the same as +EV.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Leg:
    event_id: str              # one leg per event_id in an accumulator
    description: str
    model_prob: float
    price_decimal: float
    price_source: str = ""     # e.g. "bet365 app" or "football-data.co.uk (third-party)"
    price_time_utc: str = ""
    meta: dict = field(default_factory=dict)


def joint_prob_from_draws(*hit_arrays) -> float:
    """Joint probability of same-match legs from shared simulation draws.

    Each argument is a boolean array (one entry per simulation) saying whether
    that leg won in that simulation. All arrays must come from the same run.
    """
    if not hit_arrays:
        raise ValueError("need at least one leg")
    n = len(hit_arrays[0])
    joint = np.ones(n, dtype=bool)
    for h in hit_arrays:
        h = np.asarray(h, dtype=bool)
        if len(h) != n:
            raise ValueError("legs come from different simulation runs")
        joint &= h
    return float(joint.mean())


def build_acca(legs, band=(11.0, 11.2), floor: float = 0.65, min_legs: int = 2,
               resolution: float = 1e-4) -> dict | None:
    """Highest joint-probability accumulator with combined price inside ``band``.

    Exact search (multiple-choice knapsack over log-prices) with at most one leg
    per event. Returns None when no combination lands in the band - the floor is
    never lowered to make one fit.
    """
    lo, hi = band
    eligible = [l for l in legs if l.model_prob >= floor and l.price_decimal > 1.0]
    rejected = len(legs) - len(eligible)
    events: dict[str, list[Leg]] = {}
    for l in eligible:
        events.setdefault(l.event_id, []).append(l)
    ev_ids = sorted(events)
    size = int(math.ceil(math.log(hi) / resolution)) + 2
    NEG = -1e18
    dp = np.full(size, NEG)
    dp[0] = 0.0
    choice = np.full((len(ev_ids), size), -1, dtype=np.int32)
    for ei, eid in enumerate(ev_ids):
        new = dp.copy()
        for li, leg in enumerate(events[eid]):
            w = int(round(math.log(leg.price_decimal) / resolution))
            if w <= 0 or w >= size:
                continue
            cand = np.full(size, NEG)
            cand[w:] = dp[:-w] + math.log(leg.model_prob)
            better = cand > new
            new[better] = cand[better]
            choice[ei][better] = li
        dp = new

    def rebuild(b):
        picked = []
        for ei in range(len(ev_ids) - 1, -1, -1):
            li = choice[ei][b]
            if li >= 0:
                # only valid if this event's choice was the one that set dp at b
                leg = events[ev_ids[ei]][li]
                picked.append(leg)
                b -= int(round(math.log(leg.price_decimal) / resolution))
        return picked[::-1] if b == 0 else None

    b_lo = max(int(math.floor(math.log(lo) / resolution)) - len(ev_ids), 1)
    b_hi = min(int(math.ceil(math.log(hi) / resolution)) + len(ev_ids), size - 1)
    best = None
    for b in sorted(range(b_lo, b_hi + 1), key=lambda i: -dp[i]):
        if dp[b] <= NEG / 2:
            break
        picked = rebuild(b)
        if not picked or len(picked) < min_legs:
            continue
        price = math.prod(l.price_decimal for l in picked)
        if lo <= price <= hi:  # exact check after the discretised search
            best = picked
            break
    if best is None:
        return None
    price = math.prod(l.price_decimal for l in best)
    joint = math.prod(l.model_prob for l in best)
    return {
        "legs": best,
        "n_legs": len(best),
        "price_decimal": price,
        "model_joint_prob": joint,
        "price_implied_prob": 1.0 / price,
        "ev_per_unit": joint * (price - 1.0) - (1.0 - joint),
        "legs_below_floor_rejected": rejected,
    }
