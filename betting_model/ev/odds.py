"""Stage 4 - odds conversion, margin removal and expected value.

All prices are handled internally as decimal odds. Probabilities for props and
totals always come from a simulated distribution (see ``outcome_probs``), never
from "projection minus line".
"""
from __future__ import annotations

from fractions import Fraction
from typing import Iterable

import numpy as np


# --------------------------------------------------------------------------- conversion
def fractional_to_decimal(frac: str) -> float:
    """'10/1' -> 11.0, '4/6' -> 1.6667, 'evens' -> 2.0."""
    s = str(frac).strip().lower()
    if s in {"evens", "evs", "even"}:
        return 2.0
    num, _, den = s.partition("/")
    return float(Fraction(int(num), int(den or 1))) + 1.0


def american_to_decimal(american: float) -> float:
    """+150 -> 2.5, -200 -> 1.5."""
    a = float(american)
    if a == 0 or abs(a) < 100:
        raise ValueError(f"not a valid American price: {american}")
    return 1.0 + (a / 100.0 if a > 0 else 100.0 / -a)


def to_decimal(odds, fmt: str | None = None) -> float:
    """Convert any supported format to decimal.

    ``fmt`` may be 'decimal', 'fractional' or 'american'. When omitted, strings
    containing '/' are fractional, strings starting with +/- are American and
    anything else is read as decimal. Bare numbers are ambiguous (is 150 decimal
    or American?), so numeric input without ``fmt`` is always treated as decimal.
    """
    if fmt == "fractional":
        return fractional_to_decimal(odds)
    if fmt == "american":
        return american_to_decimal(odds)
    if fmt in (None, "decimal"):
        if fmt is None and isinstance(odds, str):
            s = odds.strip().lower()
            if "/" in s or s.startswith("ev"):
                return fractional_to_decimal(s)
            if s[:1] in "+-":
                return american_to_decimal(float(s))
        d = float(odds)
        if d <= 1.0:
            raise ValueError(f"decimal odds must be above 1.0, got {odds}")
        return d
    raise ValueError(f"unknown odds format: {fmt}")


def american_to_decimal_array(a) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(a > 0, 1.0 + a / 100.0, 1.0 + 100.0 / -a)
    out[~np.isfinite(out) | (np.abs(a) < 100)] = np.nan
    return out


def implied_prob(decimal: float) -> float:
    """Raw price-implied probability (still includes the bookmaker margin)."""
    return 1.0 / float(decimal)


def overround(decimals: Iterable[float]) -> float:
    """Bookmaker margin of a complete market: sum of implied probabilities minus 1."""
    return float(sum(1.0 / float(d) for d in decimals) - 1.0)


# --------------------------------------------------------------------------- de-vig
def devig_power(decimals) -> np.ndarray:
    """Power method: find k with sum((1/d)^k) = 1.

    Accepts one market (1-D) or many markets as rows (2-D). Rows containing a
    missing or invalid price come back as NaN rather than being guessed.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        q = 1.0 / np.asarray(decimals, dtype=float)
    one_d = q.ndim == 1
    q = np.atleast_2d(q)
    ok = np.isfinite(q).all(axis=1) & (q > 0).all(axis=1) & (q < 1).all(axis=1)
    out = np.full(q.shape, np.nan)
    if ok.any():
        qq = q[ok]
        lo = np.full(len(qq), 0.2)
        hi = np.full(len(qq), 5.0)
        for _ in range(60):  # bisection; sum(q^k) is decreasing in k
            mid = (lo + hi) / 2
            s = (qq ** mid[:, None]).sum(axis=1)
            lo = np.where(s > 1, mid, lo)
            hi = np.where(s > 1, hi, mid)
        p = qq ** ((lo + hi) / 2)[:, None]
        out[ok] = p / p.sum(axis=1, keepdims=True)
    return out[0] if one_d else out


def devig_shin(decimals) -> np.ndarray:
    """Shin (1993) method for a single market: models the margin as protection
    against insider money, which removes more margin from longshots."""
    q = 1.0 / np.asarray(decimals, dtype=float)
    if not np.isfinite(q).all():
        return np.full(q.shape, np.nan)
    b = q.sum()
    if b <= 1.0:
        return q / b

    def probs(z):
        return (np.sqrt(z * z + 4 * (1 - z) * q * q / b) - z) / (2 * (1 - z))

    lo, hi = 0.0, 0.5
    for _ in range(80):  # sum(probs) is decreasing in z
        mid = (lo + hi) / 2
        if probs(mid).sum() > 1:
            lo = mid
        else:
            hi = mid
    p = probs((lo + hi) / 2)
    return p / p.sum()


def devig(decimals, method: str = "power") -> np.ndarray:
    if method == "power":
        return devig_power(decimals)
    if method == "shin":
        return devig_shin(decimals)
    if method == "multiplicative":
        q = 1.0 / np.asarray(decimals, dtype=float)
        return q / q.sum(axis=-1, keepdims=True)
    raise ValueError(f"unknown de-vig method: {method}")


# --------------------------------------------------------------------------- EV
def ev_per_unit(p_win: float, decimal: float, p_push: float = 0.0) -> float:
    """Expected profit per 1 unit staked.

    EV = p_win * (decimal - 1) - p_lose, where p_lose = 1 - p_win - p_push.
    A push (void) returns the stake, so it contributes zero.
    """
    p_lose = 1.0 - p_win - p_push
    if min(p_win, p_push, p_lose) < -1e-9:
        raise ValueError("probabilities must be non-negative and sum to at most 1")
    return p_win * (decimal - 1.0) - p_lose


def outcome_probs(draws, line: float) -> dict:
    """Over/under/push probabilities for a line, taken from simulated draws."""
    x = np.asarray(draws, dtype=float)
    return {
        "over": float((x > line).mean()),
        "under": float((x < line).mean()),
        "push": float((x == line).mean()),
    }


def distribution_summary(draws) -> dict:
    x = np.asarray(draws, dtype=float)
    return {
        "mean": float(x.mean()),
        "median": float(np.median(x)),
        "p10": float(np.quantile(x, 0.10)),
        "p90": float(np.quantile(x, 0.90)),
    }
