"""Stage 6 - model improvement analysis.

Compares stated probabilities with outcomes, breaks the error down by segment
and separates repeatable weakness from noise with bootstrap intervals. It only
diagnoses: any change it suggests must win on the Stage 5 harness before it is
adopted.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..backtest import metrics as mx
from ..config import CLEAN, ROOT, load_config

REPORT = ROOT / "analysis" / "reports" / "error_analysis.md"


def calibration_slope(p, y) -> tuple[float, float]:
    """Logistic regression of outcome on logit(p): returns (intercept, slope).
    Slope below 1 means probabilities are too extreme (over-confident); above 1
    means too timid. Intercept away from 0 at slope 1 means a level bias."""
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, float)
    x = np.log(p / (1 - p))
    X = np.column_stack([np.ones_like(x), x])
    b = np.array([0.0, 1.0])
    for _ in range(50):  # Newton-Raphson
        mu = 1 / (1 + np.exp(-X @ b))
        H = X.T @ (X * (mu * (1 - mu))[:, None]) + 1e-9 * np.eye(2)
        step = np.linalg.solve(H, X.T @ (y - mu))
        b += step
        if np.abs(step).max() < 1e-10:
            break
    return float(b[0]), float(b[1])


def residual_ci(p, y, groups=None, n_boot: int = 2000, seed: int = 0) -> dict:
    """Mean residual (hit rate minus stated probability) with a 95% bootstrap
    interval. When ``groups`` is given, whole groups (matches) are resampled,
    because legs from the same match are not independent."""
    r = np.asarray(y, float) - np.asarray(p, float)
    rng = np.random.default_rng(seed)
    if groups is None:
        boots = r[rng.integers(0, len(r), size=(n_boot, len(r)))].mean(axis=1)
    else:
        g = pd.DataFrame({"r": r, "g": np.asarray(groups)}).groupby("g").r.agg(["sum", "count"])
        s, c = g["sum"].to_numpy(), g["count"].to_numpy()
        idx = rng.integers(0, len(g), size=(n_boot, len(g)))
        boots = s[idx].sum(axis=1) / c[idx].sum(axis=1)
    lo, hi = np.quantile(boots, [0.025, 0.975])
    return {"n": int(len(r)), "mean_residual": float(r.mean()), "ci_low": float(lo), "ci_high": float(hi)}


def breakdown(df: pd.DataFrame, by: str, group_col: str | None = None, min_n: int = 30) -> pd.DataFrame:
    """Residual by segment. ``verdict`` uses a Bonferroni-corrected interval so
    that scanning many segments does not turn noise into a 'finding'."""
    segs = [(k, g) for k, g in df.groupby(by) if len(g) >= min_n]
    alpha = 0.05 / max(len(segs), 1)
    rows = []
    for k, g in segs:
        r = (g.won - g.model_prob).to_numpy()
        rng = np.random.default_rng(0)
        if group_col:
            a = g.assign(r=r).groupby(group_col).r.agg(["sum", "count"])
            s, c = a["sum"].to_numpy(), a["count"].to_numpy()
            idx = rng.integers(0, len(a), size=(4000, len(a)))
            boots = s[idx].sum(axis=1) / c[idx].sum(axis=1)
        else:
            boots = r[rng.integers(0, len(r), size=(4000, len(r)))].mean(axis=1)
        lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
        verdict = "over-estimated" if hi < 0 else "under-estimated" if lo > 0 else "within noise"
        rows.append({by: k, "n": len(g), "mean_model_prob": g.model_prob.mean(), "hit_rate": g.won.mean(),
                     "residual": r.mean(), "corrected_ci_low": lo, "corrected_ci_high": hi, "verdict": verdict})
    return pd.DataFrame(rows).set_index(by).round(4).sort_values("residual")


def _section(title, df, group_col, dims) -> list[str]:
    L = [f"## {title}", ""]
    overall = residual_ci(df.model_prob, df.won, df[group_col])
    a, b = calibration_slope(df.model_prob, df.won)
    L += [f"Legs: {overall['n']}. Mean residual (hit rate minus stated probability): "
          f"{overall['mean_residual']:+.4f} (95% CI {overall['ci_low']:+.4f} to {overall['ci_high']:+.4f}, "
          f"resampling whole games). Calibration intercept {a:+.3f}, slope {b:.3f} (ideal 0 and 1).", "",
          "Stated probability vs hit rate:", "",
          mx.calibration_table(df.model_prob, df.won, lo=df.model_prob.min()).to_markdown(), ""]
    for d in dims:
        t = breakdown(df, d, group_col)
        flagged = t[t.verdict != "within noise"]
        L += [f"### By {d}", "", t.to_markdown() if len(t) <= 25 else
              f"{len(t)} segments; showing the five largest in each direction.\n\n"
              + pd.concat([t.head(5), t.tail(5)]).to_markdown(), "",
              (f"Segments whose interval excludes zero after correction (candidates for a Stage 5 test): "
               f"{', '.join(map(str, flagged.index))}." if len(flagged)
               else "No segment differs from zero beyond noise."), ""]
    return L


def run(cfg: dict | None = None) -> str:
    cfg = cfg or load_config()
    L = ["# Model error analysis (Stage 6)", "",
         f"Generated {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC from the out-of-sample (test season) "
         f"legs of the Stage 5 backtests. Only legs at or above the {cfg['prob_floor']:.0%} floor.", "",
         "Rule: nothing here changes the model. A proposed fix must improve out-of-sample results on the "
         "walk-forward harness first.", ""]
    fb_files = [CLEAN / "backtest_football_selections_test.csv", CLEAN / "backtest_football_unpriced_test.csv"]
    if all(f.exists() for f in fb_files):
        sel = pd.read_csv(fb_files[0]).assign(won=lambda d: (d.result == "win").astype(int))
        unp = pd.read_csv(fb_files[1])
        fb = pd.concat([sel, unp], ignore_index=True)
        fb["game"] = fb.league + "|" + fb.match_date.astype(str).str[:10] + "|" + fb.home_team
        fb["prob_range"] = (np.floor(fb.model_prob * 20) / 20).map(lambda v: f"{v:.0%}-{v + 0.05:.0%}")
        long = pd.concat([fb.assign(team=fb.home_team, venue="home"), fb.assign(team=fb.away_team, venue="away")])
        L += _section("Football", fb, "game", ["market", "market_group", "league", "season"])
        t = breakdown(long, "team", "game")
        flagged = t[t.verdict != "within noise"]
        L += ["### By team (each leg counted for both teams in the match)", "",
              pd.concat([t.head(5), t.tail(5)]).to_markdown(), "",
              (f"Teams whose interval excludes zero after correction: {', '.join(flagged.index)}." if len(flagged)
               else f"No team out of {len(t)} differs from zero beyond noise."), ""]
        opp = long.assign(side=np.where(long.market.isin(["home", "dc_1x"]), "backing home side",
                                        np.where(long.market.isin(["away", "dc_x2"]), "backing away side", "neutral market")))
        L += ["### By side backed", "", breakdown(opp[opp.venue == "home"], "side", "game").to_markdown(), ""]
    else:
        L += ["## Football", "", "No backtest output found - run `python -m betting_model.backtest.football`.", ""]
    nfl_file = CLEAN / "backtest_nfl_legs.csv"
    if nfl_file.exists():
        n = pd.read_csv(nfl_file)
        n = n[(n.result != "void") & (n.p_bootstrap >= cfg["prob_floor"])]
        n = n.assign(won=(n.result == "win").astype(int), model_prob=n.p_bootstrap)
        n["line_offset"] = n.market.str.extract(r"_([+-]?\d+\.?\d*)$")[0]
        L += _section("NFL derived markets", n, "game_id", ["family", "season"])
    else:
        L += ["## NFL", "", "No backtest output found - run `python -m betting_model.backtest.nfl`.", ""]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L))
    return str(REPORT)


if __name__ == "__main__":
    print(run())
