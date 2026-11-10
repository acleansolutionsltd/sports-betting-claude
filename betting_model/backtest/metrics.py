"""Stage 5 - shared backtest metrics. Every function takes all qualifying
selections, losses included; nothing here filters results."""
from __future__ import annotations

import numpy as np
import pandas as pd


def log_loss(p, y) -> float:
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    y = np.asarray(y, float)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def brier(p, y) -> float:
    return float(((np.asarray(p, float) - np.asarray(y, float)) ** 2).mean())


def multiclass_log_loss(P, outcome_idx) -> float:
    P = np.clip(np.asarray(P, float), 1e-9, 1)
    return float(-np.log(P[np.arange(len(P)), np.asarray(outcome_idx)]).mean())


def multiclass_brier(P, outcome_idx) -> float:
    P = np.asarray(P, float)
    Y = np.zeros_like(P)
    Y[np.arange(len(P)), np.asarray(outcome_idx)] = 1
    return float(((P - Y) ** 2).sum(axis=1).mean())


def max_drawdown(net) -> float:
    """Largest peak-to-trough fall of cumulative profit, in units (positive number)."""
    cum = np.concatenate([[0.0], np.cumsum(np.asarray(net, float))])
    return float((np.maximum.accumulate(cum) - cum).max())


def longest_losing_run(results) -> int:
    best = cur = 0
    for r in results:
        if r == "loss":
            cur += 1
            best = max(best, cur)
        elif r == "win":
            cur = 0
    return best


def calibration_table(p, y, width: float = 0.05, lo: float = 0.0) -> pd.DataFrame:
    """Reliability table in ``width`` buckets: stated probability vs actual hit rate."""
    df = pd.DataFrame({"p": np.asarray(p, float), "y": np.asarray(y, float)})
    df = df[df.p >= lo]
    df["bucket_lo"] = np.minimum(np.floor(df.p / width + 1e-9) * width, 1 - width)
    g = df.groupby("bucket_lo").agg(n=("y", "size"), mean_model_prob=("p", "mean"), hit_rate=("y", "mean"))
    g["se"] = np.sqrt(g.hit_rate * (1 - g.hit_rate) / g.n)
    g["gap"] = g.hit_rate - g.mean_model_prob
    g.index = [f"{a:.0%}-{a + width:.0%}" for a in g.index]
    g.index.name = "bucket"
    return g.round(4)


def bet_summary(bets: pd.DataFrame) -> dict:
    """bets needs: result ('win'/'loss'/'void'), net_units, stake_units; optional
    model_prob, clv. Rows must already be in bet-time order."""
    if len(bets) == 0:
        return {"bets": 0}
    settled = bets[bets.result != "void"]
    staked = bets.stake_units.sum()
    out = {
        "bets": int(len(bets)),
        "wins": int((bets.result == "win").sum()),
        "voids": int((bets.result == "void").sum()),
        "win_rate": round(float((settled.result == "win").mean()), 4) if len(settled) else np.nan,
        "units": round(float(bets.net_units.sum()), 2),
        "roi": round(float(bets.net_units.sum() / staked), 4) if staked else np.nan,
        "max_drawdown": round(max_drawdown(bets.net_units), 2),
        "longest_losing_run": longest_losing_run(bets.result),
    }
    if "model_prob" in bets:
        out["avg_model_prob"] = round(float(settled.model_prob.mean()), 4)
    if "clv" in bets and bets.clv.notna().any():
        out["avg_clv"] = round(float(bets.clv.mean()), 4)
        out["beat_close_rate"] = round(float((bets.clv.dropna() > 0).mean()), 4)
    return out


def roi_bootstrap_ci(net, n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    """95% bootstrap interval for ROI per unit staked (flat stakes)."""
    net = np.asarray(net, float)
    if len(net) < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = net[rng.integers(0, len(net), size=(n_boot, len(net)))].mean(axis=1)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))
