"""Stage 8 - the daily workflow.

    python -m betting_model.pipeline.run_daily                 # full run
    python -m betting_model.pipeline.run_daily --steps run     # models only, cached data
    python -m betting_model.pipeline.run_daily --steps fetch,run --kickoff-within 90   # news-window re-run

Steps: fetch (cached, rate-limited, capped) -> audit -> grade the tracker ->
price snapshot with staleness check -> run the models with fixed seeds -> save
timestamped selections -> alerts.

This is the administrative job. It is the only code that downloads data or
writes selections; the tracker report (``python -m betting_model.tracker.tracker
report``) only reads. The pipeline never changes model formulas or thresholds:
it reads config.yaml and logs its hash with every run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ..backtest.football import add_anchor, load_matches
from ..config import CLEAN, OUTPUTS, config_hash, load_config
from ..ev.acca import Leg, build_acca
from ..ev.odds import american_to_decimal_array
from ..ingest.audit import _parse_uk_kickoff, run_audit
from ..ingest.fetch import FetchBudgetExceeded, Fetcher, fetch_all
from ..models.football import dixon_coles as dc
from ..models.football import sim as fsim
from ..models.nfl import props as nprops
from ..models.nfl import score_pair as sp
from ..tracker import tracker

THIRD_PARTY = "(third-party - check the price in the bet365 app before placing)"


def event_seed(base_seed: int, event_id: str) -> int:
    """Stable per-event seed: re-running one game never changes another's draws."""
    return int.from_bytes(hashlib.sha256(f"{base_seed}|{event_id}".encode()).digest()[:8], "big")


def _age_minutes(entry: dict | None, now: datetime) -> float | None:
    """Minutes since the source last changed; None when the source does not say."""
    ts = entry and entry.get("source_last_modified_utc")
    return None if not ts else (now - datetime.fromisoformat(ts)).total_seconds() / 60


def _stale_alert(name: str, age: float | None, limit: int) -> str:
    if age is None:
        return f"{name}: the source does not report when its prices were last updated - flagged stale"
    return f"{name}: price file is {age:.0f} min old (limit {limit}) - prices flagged stale"


# --------------------------------------------------------------------------- grading
def grade_tracker(alerts: list[str]) -> int:
    """Grade open tracker legs whose event has a final score in the clean data."""
    b = tracker.load()
    open_legs = b[b.result.isna() & (b.market_key != "") & (b.event_id != "")]
    if open_legs.empty:
        return 0
    fb = pd.read_csv(CLEAN / "football_matches.csv", low_memory=False).dropna(subset=["FTHG", "FTAG"])
    fb["event_id"] = fb.Div + "|" + fb.match_date.astype(str).str[:10] + "|" + fb.HomeTeam + "|" + fb.AwayTeam
    fb = fb.set_index("event_id")
    nfl = pd.read_csv(CLEAN / "nfl_games.csv", low_memory=False).dropna(subset=["home_score"]).set_index("game_id")
    n = 0
    for r in open_legs.itertuples():
        try:
            if r.event_id in fb.index:
                m = fb.loc[r.event_id]
                res, src = fsim.settle(r.market_key, int(m.FTHG), int(m.FTAG)), "football-data.co.uk"
            elif r.event_id in nfl.index:
                g = nfl.loc[r.event_id]
                res, src = sp.settle(r.market_key, int(g.home_score), int(g.away_score)), "nflverse games.csv"
            else:
                continue
        except (KeyError, ValueError):
            alerts.append(f"tracker: cannot auto-grade {r.bet_id} ({r.market_key}) - grade it manually")
            continue
        tracker.record_result(r.bet_id, res, src)
        n += 1
    return n


# --------------------------------------------------------------------------- football
def run_football(cfg, fetcher: Fetcher, now, rng_base, alerts, kickoff_within=None):
    fc = cfg["football"]
    entry = fetcher.latest("football_data", "fixtures.csv")
    if entry is None:
        alerts.append("football: no fixtures file - nothing priced")
        return []
    age = _age_minutes(entry, now)
    stale = age is None or age > cfg["stale_minutes"]
    src = (f"football-data.co.uk fixtures.csv, source updated {entry.get('source_last_modified_utc')} "
           f"{THIRD_PARTY}")
    if stale:
        alerts.append(_stale_alert("football", age, cfg["stale_minutes"]))
    fx = pd.read_csv(fetcher.path_of(entry), encoding="utf-8-sig")
    fx = fx[fx.Div.isin(fc["leagues"])].copy()
    fx["kickoff_utc"] = _parse_uk_kickoff(fx.Date, fx.Time)
    gone = fx[fx.kickoff_utc <= now]
    fx = fx[fx.kickoff_utc > now]
    if len(gone):
        alerts.append(f"football: {len(gone)} fixtures in the price file have already kicked off - excluded")
    if kickoff_within is not None:
        fx = fx[fx.kickoff_utc <= now + pd.Timedelta(minutes=kickoff_within)]
    if fx.empty:
        alerts.append("football: no upcoming top-league fixtures with prices in the source file "
                      "(international break, or the file has not been refreshed yet)")
        return []
    fx = add_anchor(fx)
    hist = load_matches()
    today = pd.Timestamp(now.date())
    legs = []
    for div, grp in fx.groupby("Div"):
        lg = hist[hist.Div == div]
        model = dc.fit(lg, today, fc["time_decay_xi"], fc["ridge"], fc["history_days"])
        form = dc.shots_form(lg, today, fc["shots_window"])
        for r in grp.itertuples():
            eid = f"{div}|{r.kickoff_utc:%Y-%m-%d}|{r.HomeTeam}|{r.AwayTeam}"
            if not np.isfinite(r.a_home):
                alerts.append(f"football: {eid} has no sharp price - skipped (the market is the anchor)")
                continue
            rho = model.rho if model else 0.0
            mkt = dc.lambdas_from_market(r.a_home, r.a_draw, r.a_away, r.a_over, rho, fc["dispersion"])
            team = model.lambdas(r.HomeTeam, r.AwayTeam, fc["min_team_matches"]) if model else None
            shots = dc.shots_lambdas(form, r.HomeTeam, r.AwayTeam)
            blend, used = fsim.blend_lambdas(mkt, team, shots, fc["blend"])
            live = blend if fc["blend_passed_stage5"] else mkt
            rng = np.random.default_rng(event_seed(rng_base, eid))
            hg, ag = fsim.simulate_scores(live[0], live[1], rho, cfg["n_sims"], rng, fc["dispersion"])
            hits = fsim.leg_hits(hg, ag)
            fit_err = max(abs((hg > ag).mean() - r.a_home), abs((hg < ag).mean() - r.a_away),
                          abs(((hg + ag) > 2.5).mean() - r.a_over) if np.isfinite(r.a_over) else 0.0)
            if fit_err > 0.02:
                alerts.append(f"football: {eid} simulation is {fit_err:.3f} away from the sharp price")
            prices = {"1x2:home": r.B365H, "1x2:draw": r.B365D, "1x2:away": r.B365A,
                      "total:over_2.5": getattr(r, "_" + str(fx.columns.get_loc("B365>2.5") + 1), np.nan),
                      "total:under_2.5": getattr(r, "_" + str(fx.columns.get_loc("B365<2.5") + 1), np.nan)}
            if np.isfinite(r.AHh) and float(r.AHh * 2).is_integer():
                prices[f"ah:home_{r.AHh:+.1f}"] = r.B365AHH
                prices[f"ah:away_{-r.AHh:+.1f}"] = r.B365AHA
            for key, (win, push) in hits.items():
                p_push = float(push.mean()) if push is not None else 0.0
                p = float(win.mean()) / max(1 - p_push, 1e-9)
                price = prices.get(key, np.nan)
                legs.append({
                    "sport": "Football", "league": fc["leagues"][div], "event": f"{r.HomeTeam} v {r.AwayTeam}",
                    "event_id": eid, "event_start_utc": r.kickoff_utc.isoformat(), "market_key": key,
                    "model_prob": round(p, 4), "push_prob": round(p_push, 4),
                    "price_decimal": price if pd.notna(price) else np.nan,
                    "price_source_and_time": src if pd.notna(price) else "",
                    "price_stale": bool(stale) if pd.notna(price) else None,
                    "anchor_source": r.anchor_source, "lambda_home": round(live[0], 3),
                    "lambda_away": round(live[1], 3),
                    "blend_lambda_home": round(blend[0], 3), "blend_lambda_away": round(blend[1], 3),
                    "blend_weights_used": json.dumps({k: round(v, 3) for k, v in used.items()}),
                    "probability_basis": "standing blend" if fc["blend_passed_stage5"] else "market only (blend has not passed Stage 5)",
                })
    return legs


# --------------------------------------------------------------------------- NFL
def run_nfl(cfg, fetcher: Fetcher, now, rng_base, alerts, kickoff_within=None, horizon_days=8):
    nc = cfg["nfl"]
    entry = fetcher.latest("nflverse", "games.csv")
    if entry is None:
        alerts.append("nfl: no games file - nothing priced")
        return [], []
    age = _age_minutes(entry, now)
    stale = age is None or age > cfg["stale_minutes"]
    if stale:
        alerts.append(_stale_alert("nfl", age, cfg["stale_minutes"]))
    src = f"nflverse games.csv consensus line, fetched {entry.get('fetched_at_utc')}, source update time not reported {THIRD_PARTY}"
    games = pd.read_csv(CLEAN / "nfl_games.csv", low_memory=False)
    games["kickoff_utc"] = pd.to_datetime(games.kickoff_utc, utc=True)
    pw = pd.read_csv(CLEAN / "nfl_player_weeks.csv", low_memory=False)
    games = sp.add_team_volumes(games, pw).join(sp.market_targets(games))
    limit = now + (pd.Timedelta(minutes=kickoff_within) if kickoff_within is not None
                   else pd.Timedelta(days=horizon_days))
    up = games[(games.kickoff_utc > now) & (games.kickoff_utc <= limit)]
    if up.empty:
        alerts.append("nfl: no upcoming games in the window")
        return [], []
    pool = sp.build_pool(games, now, nc["pool_start_season"])
    vol_cols = [f"{s}_{c}" for s in ("home", "away") for c in sp.VOLUME_COLS]
    with_vol = pool.dropna(subset=vol_cols)
    if len(with_vol) >= 0.95 * len(pool):
        pool = with_vol.reset_index(drop=True)  # every draw then carries play volumes for the props
    else:
        alerts.append(f"nfl props: only {len(with_vol)} of {len(pool)} pool games have play volumes - props skipped")
        pool = pool.drop(columns=vol_cols)
    legs, props = [], []
    for r in up.itertuples():
        if not all(np.isfinite([r.p_home, r.p_cover, r.p_over, r.spread_line, r.total_line])):
            alerts.append(f"nfl: {r.game_id} has no complete line yet - skipped (the market is the anchor)")
            continue
        w, diag = sp.fit_weights(pool, r.spread_line, r.total_line, r.p_home, r.p_cover, r.p_over,
                                 nc["kernel_bw"]["spread"], nc["kernel_bw"]["total"])
        if diag["effective_sample"] < nc["min_effective_sample"]:
            alerts.append(f"nfl: {r.game_id} effective sample {diag['effective_sample']:.0f} is below "
                          f"{nc['min_effective_sample']} - tails are thin, treat alt lines with care")
        rng = np.random.default_rng(event_seed(rng_base, r.game_id))
        draws = sp.simulate(pool, w, cfg["n_sims"], rng)
        dec = dict(zip(["ml:home", "ml:away", f"spread:home_{-r.spread_line:+.1f}",
                        f"spread:away_{r.spread_line:+.1f}", f"total:over_{r.total_line:.1f}",
                        f"total:under_{r.total_line:.1f}"],
                       american_to_decimal_array([r.home_moneyline, r.away_moneyline, r.home_spread_odds,
                                                  r.away_spread_odds, r.over_odds, r.under_odds])))
        common = {"sport": "NFL", "league": "NFL", "event": f"{r.away_team} @ {r.home_team}",
                  "event_id": r.game_id, "event_start_utc": r.kickoff_utc.isoformat()}
        for key, (win, push) in sp.leg_hits(draws["home"], draws["away"], r.spread_line, r.total_line).items():
            p_push = float(push.mean()) if push is not None else 0.0
            price = dec.get(key, np.nan)
            legs.append({**common, "market_key": key,
                         "model_prob": round(float(win.mean()) / max(1 - p_push, 1e-9), 4),
                         "push_prob": round(p_push, 4), "price_decimal": price if np.isfinite(price) else np.nan,
                         "price_source_and_time": src if np.isfinite(price) else "",
                         "price_stale": bool(stale) if np.isfinite(price) else None,
                         "anchor_source": "nflverse consensus",
                         "probability_basis": "score-pair bootstrap matched to de-vigged moneyline, spread and total",
                         "effective_sample": round(diag["effective_sample"])})
        # player props: projections only (no prices, not yet backtested)
        for side, team, opp in (("home", r.home_team, r.away_team), ("away", r.away_team, r.home_team)):
            inp = nprops.player_inputs(pw, team, r.season, r.week)
            if inp.empty:
                alerts.append(f"nfl props: no player history for {team} - props skipped")
                continue
            active = inp[inp.last_played_games_ago <= 1]
            opp_f = nprops.opponent_rush_factor(pw, opp, r.season, r.week)
            rec_p = active[active.position.isin(["WR", "TE", "RB"])].nlargest(5, "target_share")
            rush_p = active[active.position.isin(["RB", "QB"])].nlargest(3, "carry_share")
            for q in rec_p.itertuples():
                for pr in nprops.sim_receiving(q.player, draws.get(f"{side}_pass_att"), q.target_share,
                                               q.catch_rate, q.yards_per_rec, rng):
                    props.append({**common, "team": team, **pr.summary()})
            for q in rush_p.itertuples():
                for pr in nprops.sim_rushing(q.player, draws.get(f"{side}_carries"), q.carry_share,
                                             q.yards_per_carry, rng, opp_f):
                    props.append({**common, "team": team, **pr.summary()})
            scorers = pd.concat([rec_p, rush_p]).drop_duplicates("player")
            tds = nprops.sim_touchdowns(
                draws.get(f"{side}_rush_td"), draws.get(f"{side}_pass_td"),
                {q.player: q.rush_td_share for q in scorers.itertuples()},
                {q.player: q.rec_td_share for q in scorers.itertuples() if q.position != "QB"}, rng)
            for pr in tds.values():
                s = pr.summary()
                if not pr.skipped:
                    s["anytime_td_prob"] = round(float((pr.draws > 0).mean()), 4)
                props.append({**common, "team": team, **s})
    return legs, props


# --------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--steps", default="fetch,audit,grade,run", help="comma list of fetch,audit,grade,run")
    ap.add_argument("--as-of", default=None, help="replay the run as if it were this UTC time (ISO format); "
                    "outputs go to outputs/replay/ and are marked as not a live record")
    ap.add_argument("--kickoff-within", type=int, default=None,
                    help="only re-run events kicking off within this many minutes (news window)")
    args = ap.parse_args(argv)
    steps = set(args.steps.split(","))
    cfg = load_config()
    now = datetime.now(timezone.utc)
    replay = args.as_of is not None
    if replay:
        now = datetime.fromisoformat(args.as_of.replace("Z", "+00:00")).astimezone(timezone.utc)
        steps &= {"run"}  # a replay never downloads, audits or grades
    alerts: list[str] = []
    fetcher = Fetcher(cfg)
    log = {"run_started_utc": now.isoformat(timespec="seconds"), "config_hash": config_hash(),
           "seed": cfg["seed"], "n_sims": cfg["n_sims"], "prob_floor": cfg["prob_floor"], "steps": sorted(steps)}

    if "fetch" in steps:
        try:
            fetcher = fetch_all(cfg)
            alerts += fetcher.errors
            log["downloads"] = fetcher.calls
        except FetchBudgetExceeded as exc:
            alerts.append(f"fetch stopped: {exc}")
    if "audit" in steps:
        a = run_audit(cfg)
        log["audit"] = {k: str(v) for k, v in a.items()}
    if "grade" in steps:
        log["legs_graded"] = grade_tracker(alerts)
    problems = tracker.verify()
    alerts += [f"tracker integrity: {p}" for p in problems]

    if "run" in steps:
        out_dir = OUTPUTS / ("replay" if replay else "") / f"{now:%Y-%m-%d}" / f"{now:%H%M%S}"
        log["replay"] = replay  # a replay is a test of the code path, never an honest pre-kickoff record
        out_dir.mkdir(parents=True, exist_ok=True)
        fb_legs = run_football(cfg, fetcher, now, cfg["seed"], alerts, args.kickoff_within)
        nfl_legs, props = run_nfl(cfg, fetcher, now, cfg["seed"], alerts, args.kickoff_within)
        legs = pd.DataFrame(fb_legs + nfl_legs)
        saved = now if replay else datetime.now(timezone.utc)
        if len(legs):
            legs.insert(0, "saved_at_utc", saved.isoformat(timespec="seconds"))
            legs["meets_floor"] = legs.model_prob >= cfg["prob_floor"]
            legs["implied_prob"] = (1 / legs.price_decimal).round(4)
            legs["ev_per_unit"] = (legs.model_prob * (1 - legs.push_prob) * (legs.price_decimal - 1)
                                   - (1 - legs.model_prob) * (1 - legs.push_prob)).round(4)
            legs.to_csv(out_dir / "all_legs.csv", index=False)
            sel = legs[legs.meets_floor].sort_values("model_prob", ascending=False)
            sel.to_csv(out_dir / "selections.csv", index=False)
            late = sel[pd.to_datetime(sel.event_start_utc, utc=True) <= saved]
            if len(late):
                alerts.append(f"{len(late)} selections kicked off before they were saved - do not use them")
            priced = sel[sel.price_decimal.notna()]
            acca_legs = [Leg(r.event_id, f"{r.event}: {r.market_key}", r.model_prob, r.price_decimal,
                             r.price_source_and_time) for r in priced.itertuples()]
            slip = build_acca(acca_legs, tuple(cfg["acca"]["price_band"]), cfg["prob_floor"])
            log["selections"] = int(len(sel))
            log["priced_selections"] = int(len(priced))
            if slip:
                slip_out = {**{k: v for k, v in slip.items() if k != "legs"},
                            "band": cfg["acca"]["price_band"],
                            "legs": [{"event": l.description, "model_prob": l.model_prob,
                                      "price_decimal": l.price_decimal, "price_source": l.price_source}
                                     for l in slip["legs"]],
                            "note": "Prices are third-party snapshots. Re-check every price in the bet365 app; "
                                    "a high joint probability is not the same as positive expected value."}
                (out_dir / "example_slip.json").write_text(json.dumps(slip_out, indent=1))
                log["example_slip"] = {"n_legs": slip["n_legs"], "price": round(slip["price_decimal"], 3),
                                       "model_joint_prob": round(slip["model_joint_prob"], 4),
                                       "ev_per_unit": round(slip["ev_per_unit"], 4)}
            else:
                log["example_slip"] = "no combination of qualifying priced legs lands in the price band"
        else:
            log["selections"] = 0
        if props:
            pd.DataFrame(props).assign(
                status="projection only - no prices, not yet backtested").to_csv(out_dir / "nfl_props.csv", index=False)
            log["props"] = len(props)
        log["alerts"] = alerts
        log["run_finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        (out_dir / "run.json").write_text(json.dumps(log, indent=1))
        (out_dir / "alerts.txt").write_text("\n".join(alerts) + ("\n" if alerts else ""))
        print(f"outputs: {out_dir}")
    print(json.dumps({k: v for k, v in log.items() if k != "alerts"}, indent=1))
    for a in alerts:
        print("ALERT:", a, file=sys.stderr)
    return 1 if alerts else 0


if __name__ == "__main__":
    sys.exit(main())
