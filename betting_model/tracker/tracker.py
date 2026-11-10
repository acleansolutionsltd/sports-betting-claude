"""Stage 7 - transparent, append-only performance tracker.

Two CSV files, both only ever appended to:
  bets.csv     one row per leg, written when the bet is recorded (before kickoff)
  results.csv  one row per grading event (bet_id, result), written afterwards

Keeping results in a second file means bets.csv never has to be edited. Each
bets.csv row carries a hash of itself plus the previous row's hash, so any later
edit or deletion is detected by ``verify``. Losing picks stay; qualification
rules are not re-applied after the fact; missing or unverifiable records are
flagged in the report, never filled in.

Usage:
    python -m betting_model.tracker.tracker report
    python -m betting_model.tracker.tracker verify
"""
from __future__ import annotations

import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ..backtest import metrics as mx

DIR = Path(__file__).resolve().parent
BETS = DIR / "bets.csv"
RESULTS = DIR / "results.csv"

BET_COLUMNS = ["bet_id", "placed_at_utc", "sport", "league", "event", "event_id", "event_start_utc",
               "market", "selection", "market_key", "bookmaker", "price_decimal", "price_source_and_time",
               "model_prob", "implied_prob", "slip_id", "leg_no", "slip_price_decimal", "stake_units",
               "flags", "prev_hash", "row_hash"]
RESULT_COLUMNS = ["bet_id", "graded_at_utc", "result", "source", "correction_reason"]
REQUIRED = ["bet_id", "placed_at_utc", "sport", "event", "market", "selection", "bookmaker",
            "price_decimal", "price_source_and_time", "model_prob", "slip_id", "leg_no", "stake_units"]
VALID_RESULTS = {"win", "loss", "void"}


def _utc(ts) -> datetime:
    d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError(f"timestamp has no timezone: {ts}")
    return d.astimezone(timezone.utc)


def _hash(prev: str, row: dict) -> str:
    body = "|".join(str(row.get(c, "")) for c in BET_COLUMNS[:-2])
    return hashlib.sha256((prev + "|" + body).encode()).hexdigest()[:16]


def _read(path: Path, cols) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=cols)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _append(path: Path, cols, rows) -> None:
    new = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def append_bets(rows: list[dict], bets_path: Path = BETS) -> list[str]:
    """Record legs. Refuses duplicates and incomplete rows; a leg recorded after
    its event started is accepted but flagged 'recorded_after_start' so the
    record stays honest. Returns the bet_ids written."""
    existing = _read(bets_path, BET_COLUMNS)
    seen = set(existing.bet_id)
    prev = existing.row_hash.iloc[-1] if len(existing) else ""
    out = []
    for r in rows:
        r = dict(r)
        missing = [c for c in REQUIRED if str(r.get(c, "")).strip() == ""]
        if missing:
            raise ValueError(f"bet {r.get('bet_id')}: missing {missing}")
        if r["bet_id"] in seen:
            raise ValueError(f"bet_id already recorded (rows are never replaced): {r['bet_id']}")
        placed = _utc(r["placed_at_utc"])
        price, p = float(r["price_decimal"]), float(r["model_prob"])
        if price <= 1 or not 0 < p < 1:
            raise ValueError(f"bet {r['bet_id']}: bad price or probability")
        flags = [f for f in str(r.get("flags", "")).split(";") if f]
        if r.get("event_start_utc") and placed > _utc(r["event_start_utc"]):
            flags.append("recorded_after_start")
        if "bet365 app" not in str(r["price_source_and_time"]).lower():
            flags.append("third_party_price")
        r.update(placed_at_utc=placed.isoformat(timespec="seconds"), implied_prob=round(1 / price, 4),
                 flags=";".join(dict.fromkeys(flags)), prev_hash=prev)
        r["row_hash"] = prev = _hash(prev, r)
        seen.add(r["bet_id"])
        out.append(r)
    _append(bets_path, BET_COLUMNS, out)
    return [r["bet_id"] for r in out]


def record_result(bet_id: str, result: str, source: str, correction_reason: str = "",
                  bets_path: Path = BETS, results_path: Path = RESULTS) -> None:
    """Append a grading. Re-grading requires a stated reason; the earlier row
    stays in the file and the latest row is the one reports use."""
    if result not in VALID_RESULTS:
        raise ValueError(f"result must be one of {sorted(VALID_RESULTS)}")
    if bet_id not in set(_read(bets_path, BET_COLUMNS).bet_id):
        raise ValueError(f"unknown bet_id: {bet_id}")
    if bet_id in set(_read(results_path, RESULT_COLUMNS).bet_id) and not correction_reason:
        raise ValueError(f"{bet_id} is already graded; pass correction_reason to record a correction")
    _append(results_path, RESULT_COLUMNS, [{
        "bet_id": bet_id, "graded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "result": result, "source": source, "correction_reason": correction_reason}])


def verify(bets_path: Path = BETS) -> list[str]:
    """Check the hash chain. Returns a list of problems (empty = intact)."""
    df = _read(bets_path, BET_COLUMNS)
    problems, prev = [], ""
    for i, r in df.iterrows():
        if r.prev_hash != prev or r.row_hash != _hash(prev, r.to_dict()):
            problems.append(f"row {i + 2} ({r.bet_id}): edited, reordered or a row before it was removed")
        prev = r.row_hash
    if df.bet_id.duplicated().any():
        problems.append("duplicate bet_id present")
    return problems


def load(bets_path: Path = BETS, results_path: Path = RESULTS) -> pd.DataFrame:
    b = _read(bets_path, BET_COLUMNS)
    res = _read(results_path, RESULT_COLUMNS).drop_duplicates("bet_id", keep="last")
    b = b.merge(res[["bet_id", "result", "graded_at_utc"]], on="bet_id", how="left")
    for c in ("price_decimal", "model_prob", "implied_prob", "stake_units", "slip_price_decimal"):
        b[c] = pd.to_numeric(b[c], errors="coerce")
    b["leg_no"] = pd.to_numeric(b.leg_no, errors="coerce")
    return b


def slips(b: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Settle each slip from its legs. A void leg drops out of an accumulator
    (price 1.0). A Bet Builder (quoted slip price) with a void leg cannot be
    re-priced here and is flagged for the bookmaker's settlement."""
    rows, flags = [], []
    for sid, g in b.groupby("slip_id", sort=False):
        g = g.sort_values("leg_no")
        stake = g.stake_units.iloc[0]
        if g.stake_units.nunique() > 1:
            flags.append(f"slip {sid}: legs disagree on stake; first leg's stake used")
        if g.result.isna().any():
            started = pd.to_datetime(g.event_start_utc, utc=True, errors="coerce").max()
            if pd.notna(started) and started < pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=12):
                flags.append(f"slip {sid}: event finished but {int(g.result.isna().sum())} leg(s) ungraded")
            rows.append({"slip_id": sid, "placed_at_utc": g.placed_at_utc.iloc[0], "n_legs": len(g),
                         "stake_units": stake, "result": "open", "net_units": np.nan,
                         "model_prob": np.nan, "price": np.nan})
            continue
        quoted = g.slip_price_decimal.iloc[0]
        live = g[g.result != "void"]
        if (g.result == "loss").any():
            result, price = "loss", quoted if pd.notna(quoted) else g.price_decimal.prod()
        elif len(live) == 0:
            result, price = "void", 1.0
        elif pd.notna(quoted) and len(live) < len(g):
            flags.append(f"slip {sid}: Bet Builder with a void leg - enter the bookmaker's settled price manually")
            result, price = "unverifiable", np.nan
        else:
            result, price = "win", quoted if pd.notna(quoted) else live.price_decimal.prod()
        net = {"win": stake * (price - 1), "loss": -stake, "void": 0.0}.get(result, np.nan)
        rows.append({"slip_id": sid, "placed_at_utc": g.placed_at_utc.iloc[0], "n_legs": len(g),
                     "stake_units": stake, "result": result, "net_units": net,
                     "model_prob": np.nan if pd.notna(quoted) else live.model_prob.prod(), "price": price})
    return pd.DataFrame(rows), flags


def report(bets_path: Path = BETS, results_path: Path = RESULTS) -> str:
    b = load(bets_path, results_path)
    problems = verify(bets_path)
    L = ["# Tracker report", "", f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. "
         "Flat 1-unit stakes are the baseline; every recorded slip is included.", ""]
    L += ["Integrity: " + ("hash chain intact." if not problems else "PROBLEMS - " + "; ".join(problems)), ""]
    if b.empty:
        return "\n".join(L + ["No bets recorded yet."])
    s, flags = slips(b)
    done = s[s.result.isin(["win", "loss", "void"])].sort_values("placed_at_utc")
    L += [f"Slips: {len(s)} recorded, {len(done)} settled, {(s.result == 'open').sum()} open, "
          f"{(s.result == 'unverifiable').sum()} unverifiable.", ""]
    if len(done):
        L += ["## Slips", "", pd.DataFrame({"all slips": mx.bet_summary(done)}).T.to_markdown(), "",
              f"Cumulative profit: {done.net_units.sum():+.2f} units. Maximum drawdown: "
              f"{mx.max_drawdown(done.net_units):.2f} units.", ""]
    legs = b[b.result.isin(["win", "loss"])]
    if len(legs):
        L += ["## Legs", "", f"Graded legs: {len(legs)}; win rate {(legs.result == 'win').mean():.1%}; "
              f"average model probability {legs.model_prob.mean():.1%}.", "",
              "Calibration (model probability vs outcome):", "",
              mx.calibration_table(legs.model_prob, legs.result == "win", lo=0.0).to_markdown(), "",
              "By market:", "",
              legs.groupby("market").agg(legs=("result", "size"), win_rate=("result", lambda x: (x == "win").mean()),
                                         mean_model_prob=("model_prob", "mean")).round(4).to_markdown(), ""]
    flagged = b[b["flags"] != ""]
    flags += [f"{r.bet_id}: {r.flags}" for r in flagged.itertuples()]
    L += ["## Flags (missing or unverifiable records)", ""] + ([f"- {f}" for f in flags] or ["None."])
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "verify":
        probs = verify()
        print("\n".join(probs) or "hash chain intact")
        sys.exit(1 if probs else 0)
    print(report())
