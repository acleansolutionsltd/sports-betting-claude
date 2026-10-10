#!/usr/bin/env python3
"""Opponent-adjusted team ratings with home/away splits for NFL and the Premier League.

Data: NFL results from ESPN, Premier League results (and match xG) from Sofascore.
Standard library only.

  python3 tools/ratings/team_ratings.py ratings nfl
  python3 tools/ratings/team_ratings.py matchup nfl JAX PHI --spread -7.5 --total 41.5 --ml -380 300
  python3 tools/ratings/team_ratings.py matchup epl Sunderland Brighton --odds +199 +246 +130
  python3 tools/ratings/team_ratings.py backtest nfl --season 2025

Model (per game, scores in points / goals):
  home score = mu_home + off[H] + oh[H] + dfn[A] - dh[A]
  away score = mu_away + off[A] - oh[A] + dfn[H] + dh[H]
  off  = team's scoring above league average      (+ is good)
  dfn  = score allowed above league average       (+ is bad)
  oh   = how much better the team's offence is at home than away
  dh   = how much more the team's defence concedes at home than away
Every team's off/dfn is pulled toward last season's ratings (regressed toward
average by the carry factor); the home/away splits are pulled hard toward zero
so they only move once there is real evidence. Opponent strength is handled
automatically because every score is explained by both teams' ratings.
"""
import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "props"))
from _common import get_json, parse_odds, poisson_pmf, normal_p_over  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "cache")

CONFIG = {
    "nfl": {
        "label": "NFL", "unit": "pts",
        "carry": 0.35,        # share of last season's rating kept for this season
        "lam_main": 6.0,      # prior worth this many games for off/dfn
        "lam_split": 200.0,    # prior worth this many games for home/away splits
        "lam_prior_season": 3.0,
        "sd_margin": 13.2, "sd_total": 9.5,
    },
    "epl": {
        "label": "Premier League", "unit": "goals",
        "carry": 0.7, "lam_main": 8.0, "lam_split": 40.0, "lam_prior_season": 3.0,
        "xg_weight": 0.5,     # share of the fitted target taken from xG when available
    },
}

NFL_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={}&seasontype=2&week={}"
SOFA = "https://www.sofascore.com/api/v1"
EPL_ID = 17


# ───────────────────────── data ─────────────────────────

def default_season():
    today = date.today()
    return today.year if today.month >= 8 else today.year - 1


def _cache_file(sport, season):
    return os.path.join(CACHE_DIR, f"{sport}_{season}.json")


def _load(sport, season):
    try:
        with open(_cache_file(sport, season)) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"games": {}, "done": [], "teams": {}}


def _save(sport, season, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(_cache_file(sport, season), "w") as fh:
        json.dump(data, fh)


def fetch_nfl(season, refresh=False):
    c = _load("nfl", season)
    if refresh:
        c = {"games": {}, "done": [], "teams": {}}
    for week in range(1, 19):
        if week in c["done"]:
            continue
        events = get_json(NFL_SCOREBOARD.format(season, week)).get("events", [])
        finished = 0
        for e in events:
            if not e["status"]["type"]["completed"]:
                continue
            comp = e["competitions"][0]
            side = {t["homeAway"]: t for t in comp["competitors"]}
            home, away = side["home"], side["away"]
            c["games"][e["id"]] = {
                "week": week, "home": home["team"]["abbreviation"], "away": away["team"]["abbreviation"],
                "hs": int(home["score"]), "as": int(away["score"]), "neutral": bool(comp.get("neutralSite")),
            }
            c["teams"][home["team"]["abbreviation"]] = home["team"]["displayName"]
            c["teams"][away["team"]["abbreviation"]] = away["team"]["displayName"]
            finished += 1
        if events and finished == len(events):
            c["done"].append(week)
        if finished == 0:
            break
    _save("nfl", season, c)
    return c


def _epl_season_id(season):
    for s in get_json(f"{SOFA}/unique-tournament/{EPL_ID}/seasons")["seasons"]:
        yy = s.get("year", "")  # "26/27"
        if yy[:2].isdigit() and 2000 + int(yy[:2]) == season:
            return s["id"]
    sys.exit(f"Sofascore has no Premier League season starting {season}")


def _event_xg(event_id):
    try:
        stats = get_json(f"{SOFA}/event/{event_id}/statistics")["statistics"]
    except Exception:
        return None, None
    for period in stats:
        if period.get("period") != "ALL":
            continue
        for group in period["groups"]:
            for item in group["statisticsItems"]:
                if item["key"] == "expectedGoals":
                    return float(item["homeValue"]), float(item["awayValue"])
    return None, None


def fetch_epl(season, with_xg=True, refresh=False):
    c = _load("epl", season)
    if refresh:
        c = {"games": {}, "done": [], "teams": {}}
    sid = _epl_season_id(season)
    for rnd in range(1, 39):
        if rnd in c["done"]:
            continue
        events = get_json(f"{SOFA}/unique-tournament/{EPL_ID}/season/{sid}/events/round/{rnd}").get("events", [])
        finished = 0
        for e in events:
            if e["status"]["type"] != "finished":
                continue
            gid = str(e["id"])
            home, away = e["homeTeam"]["name"], e["awayTeam"]["name"]
            g = c["games"].setdefault(gid, {"round": rnd, "home": home, "away": away, "neutral": False})
            g["hs"], g["as"] = e["homeScore"]["current"], e["awayScore"]["current"]
            c["teams"][home] = home
            c["teams"][away] = away
            finished += 1
        if events and finished == len(events):
            c["done"].append(rnd)
        if finished == 0:
            break
    if with_xg:
        missing = [gid for gid, g in c["games"].items() if "hxg" not in g]
        for i, gid in enumerate(missing):
            c["games"][gid]["hxg"], c["games"][gid]["axg"] = _event_xg(gid)
            time.sleep(0.05)
            if i and i % 40 == 0:
                _save("epl", season, c)
    _save("epl", season, c)
    return c


def load_games(sport, season, refresh=False, with_xg=True):
    data = fetch_nfl(season, refresh) if sport == "nfl" else fetch_epl(season, with_xg, refresh)
    return list(data["games"].values()), data["teams"]


# ───────────────────────── model ─────────────────────────

def make_target(sport, xg_weight):
    if sport == "epl" and xg_weight > 0:
        def target(g):
            hxg, axg = g.get("hxg"), g.get("axg")
            if hxg is None or axg is None:
                return g["hs"], g["as"]
            return (1 - xg_weight) * g["hs"] + xg_weight * hxg, (1 - xg_weight) * g["as"] + xg_weight * axg
        return target
    return lambda g: (g["hs"], g["as"])


def _rows(games, target):
    rows = []
    for g in games:
        h, a = g["home"], g["away"]
        yh, ya = target(g)
        if g.get("neutral"):
            rows.append((yh, [(("mu_h",), .5), (("mu_a",), .5), (("off", h), 1), (("dfn", a), 1)]))
            rows.append((ya, [(("mu_h",), .5), (("mu_a",), .5), (("off", a), 1), (("dfn", h), 1)]))
        else:
            rows.append((yh, [(("mu_h",), 1), (("off", h), 1), (("oh", h), 1), (("dfn", a), 1), (("dh", a), -1)]))
            rows.append((ya, [(("mu_a",), 1), (("off", a), 1), (("oh", a), -1), (("dfn", h), 1), (("dh", h), 1)]))
    return rows


def _ridge(rows, lam, prior, sweeps=3000, tol=1e-9):
    keys = set(prior)
    by_key = defaultdict(list)
    for row in rows:
        for k, _ in row[1]:
            keys.add(k)
            by_key[k].append(row)
    theta = {k: prior.get(k, 0.0) for k in keys}
    for _ in range(sweeps):
        worst = 0.0
        for k in keys:
            num, den = lam.get(k, 0.0) * prior.get(k, 0.0), lam.get(k, 0.0)
            for y, terms in by_key[k]:
                ck = sum(c for kk, c in terms if kk == k)
                num += ck * (y - sum(c * theta[kk] for kk, c in terms if kk != k))
                den += ck * ck
            if den > 0:
                new = num / den
                worst = max(worst, abs(new - theta[k]))
                theta[k] = new
        if worst < tol:
            break
    return theta


def fit(games, prior, cfg, target, lam_main=None, lam_split=None):
    """Fit ratings. `prior` is a ratings dict (already carried) or None."""
    lam_main = cfg["lam_main"] if lam_main is None else lam_main
    lam_split = cfg["lam_split"] if lam_split is None else lam_split
    teams = {g["home"] for g in games} | {g["away"] for g in games}
    if prior:
        teams |= {t for t in prior["off"] if t != "__new__"}
    lam, pri = {("mu_h",): 0.01, ("mu_a",): 0.01}, {}
    if games:
        ys = [target(g) for g in games]
        pri[("mu_h",)] = sum(y[0] for y in ys) / len(ys)
        pri[("mu_a",)] = sum(y[1] for y in ys) / len(ys)
        lam[("mu_h",)] = lam[("mu_a",)] = 0.0
    elif prior:
        pri[("mu_h",)], pri[("mu_a",)] = prior["mu_h"], prior["mu_a"]
    for t in teams:
        pri[("off", t)] = prior["off"].get(t, 0.0) if prior else 0.0
        pri[("dfn", t)] = prior["dfn"].get(t, 0.0) if prior else 0.0
        pri[("oh", t)] = pri[("dh", t)] = 0.0
        lam[("off", t)] = lam[("dfn", t)] = lam_main
        lam[("oh", t)] = lam[("dh", t)] = lam_split
    theta = _ridge(_rows(games, target), lam, pri)
    gp = defaultdict(int)
    for g in games:
        gp[g["home"]] += 1
        gp[g["away"]] += 1
    return {
        "mu_h": theta[("mu_h",)], "mu_a": theta[("mu_a",)],
        **{part: {t: theta[(part, t)] for t in teams} for part in ("off", "dfn", "oh", "dh")},
        "gp": dict(gp),
    }


def carry_prior(prev, carry):
    """Turn last season's fitted ratings into this season's prior."""
    if not prev:
        return None
    strength = sorted(prev["off"], key=lambda t: prev["off"][t] - prev["dfn"][t])
    worst = strength[:3]
    out = {"mu_h": prev["mu_h"], "mu_a": prev["mu_a"], "gp": {}}
    for part in ("off", "dfn"):
        out[part] = {t: v * carry for t, v in prev[part].items()}
        out[part]["__new__"] = sum(out[part][t] for t in worst) / len(worst)  # promoted / unknown teams
    out["oh"], out["dh"] = {}, {}
    return out


def _with_new_team_default(prior, teams):
    if not prior:
        return prior
    for part in ("off", "dfn"):
        for t in teams:
            prior[part].setdefault(t, prior[part]["__new__"])
    return prior


def build_ratings(sport, season, refresh=False, carry=None, lam_main=None, lam_split=None, xg_weight=None):
    cfg = CONFIG[sport]
    xgw = cfg.get("xg_weight", 0) if xg_weight is None else xg_weight
    games, teams = load_games(sport, season, refresh, with_xg=xgw > 0)
    prev_games, _ = load_games(sport, season - 1, refresh, with_xg=False)
    prev = fit(prev_games, None, cfg, make_target(sport, 0), lam_main=cfg["lam_prior_season"]) if prev_games else None
    prior = carry_prior(prev, cfg["carry"] if carry is None else carry)
    prior = _with_new_team_default(prior, {g[s] for g in games for s in ("home", "away")})
    ratings = fit(games, prior, cfg, make_target(sport, xgw), lam_main, lam_split)
    return ratings, games, teams, prior


def predict(r, home, away, neutral=False, use_split=True):
    oh = r["oh"].get(home, 0) if use_split and not neutral else 0
    dh_h = r["dh"].get(home, 0) if use_split and not neutral else 0
    oa = r["oh"].get(away, 0) if use_split and not neutral else 0
    dh_a = r["dh"].get(away, 0) if use_split and not neutral else 0
    mu_h = (r["mu_h"] + r["mu_a"]) / 2 if neutral else r["mu_h"]
    mu_a = (r["mu_h"] + r["mu_a"]) / 2 if neutral else r["mu_a"]
    hs = mu_h + r["off"].get(home, 0) + oh + r["dfn"].get(away, 0) - dh_a
    as_ = mu_a + r["off"].get(away, 0) - oa + r["dfn"].get(home, 0) + dh_h
    return hs, as_


# ───────────────────────── presentation ─────────────────────────

def resolve(name, teams):
    key = name.lower()
    for t in teams:
        if t.lower() == key:
            return t
    hits = [t for t, full in teams.items() if key in full.lower() or key in t.lower()]
    if len(hits) == 1:
        return hits[0]
    sys.exit(f"Team '{name}' {'is ambiguous: ' + ', '.join(hits) if hits else 'not found'}. Options: " + ", ".join(sorted(teams)))


def cmd_ratings(args):
    sport = args.sport
    cfg = CONFIG[sport]
    r, games, teams, prior = build_ratings(sport, args.season, args.refresh, args.carry, args.lam_main, args.lam_split, args.xg_weight)
    rows = sorted((t for t in r["off"] if t in teams or not teams), key=lambda t: -(r["off"][t] - r["dfn"][t]))
    unit = cfg["unit"]
    print(f"{cfg['label']} {args.season} — opponent-adjusted ratings ({unit} per game vs league average, + is good)")
    print(f"{len(games)} games played; prior = {'last season × ' + str(args.carry or cfg['carry']) if prior else 'none'}; "
          f"home scoring {r['mu_h']:.2f}, away {r['mu_a']:.2f} (home edge {r['mu_h'] - r['mu_a']:+.2f})\n")
    print(f"{'#':>2} {'team':<26}{'GP':>3}{'off':>7}{'def':>7}{'net':>7}  {'off home/away':>14}{'def home/away':>15}")
    for i, t in enumerate(rows, 1):
        print(f"{i:>2} {teams.get(t, t)[:25]:<26}{r['gp'].get(t, 0):>3}{r['off'][t]:>+7.2f}{-r['dfn'][t]:>+7.2f}"
              f"{r['off'][t] - r['dfn'][t]:>+7.2f}  {r['oh'][t]:>+14.2f}{-r['dh'][t]:>+15.2f}")
    print("\noff/def: points (goals) above average scored / prevented.  home/away columns: extra at home vs on the road "
          "(shrunk hard toward 0; treat as noise unless clearly non-zero).")


def _norm_ppf(p):
    lo, hi = -8.0, 8.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if 0.5 * math.erfc(-mid / math.sqrt(2)) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _ev_line(label, p, dec, fair=None, raw=None):
    ev = p * dec - 1
    edge = f"{p - fair:+.1%}" if fair is not None else "    -"
    flag = "  <== candidate" if ev >= 0.02 and (fair is None or p - fair >= 0.02) else ""
    shown = f"{p:6.1%}" + (f" (raw {raw:.1%})" if raw is not None else "")
    print(f"  {label:<26}model {shown:<19} book {1 / dec:6.1%}{'' if fair is None else f' (fair {fair:.1%})':<15} edge {edge:>6}   EV {ev:+7.1%}{flag}")


def _anchor(model, market, trust):
    return trust * model + (1 - trust) * market


def cmd_matchup(args):
    sport = args.sport
    cfg = CONFIG[sport]
    w = args.trust
    r, games, teams, prior = build_ratings(sport, args.season, args.refresh, args.carry, args.lam_main, args.lam_split, args.xg_weight)
    home, away = resolve(args.home, teams), resolve(args.away, teams)
    hs, as_ = predict(r, home, away, args.neutral)
    hs0, as0 = predict(r, home, away, args.neutral, use_split=False)
    hn, an = teams.get(home, home), teams.get(away, away)
    print(f"{an} @ {hn}{' (neutral site)' if args.neutral else ''} — {cfg['label']} {args.season}, {len(games)} games of data")
    print(f"  Ratings (net {cfg['unit']}/game): {hn} {r['off'][home] - r['dfn'][home]:+.2f} ({r['gp'].get(home, 0)} GP), "
          f"{an} {r['off'][away] - r['dfn'][away]:+.2f} ({r['gp'].get(away, 0)} GP)")
    print(f"  Home/away split effect on the margin: {(hs - as_) - (hs0 - as0):+.2f} {cfg['unit']}")

    if sport == "nfl":
        sd = cfg["sd_margin"]
        margin, total = hs - as_, hs + as_
        # market-implied margin: from the spread if given, else from the vig-free moneyline
        mkt_margin = None
        if args.ml:
            dh, da = parse_odds(args.ml[0]), parse_odds(args.ml[1])
            fh = (1 / dh) / (1 / dh + 1 / da)
        if args.spread is not None:
            mkt_margin = -args.spread
        elif args.ml:
            mkt_margin = sd * _norm_ppf(fh)
        used_margin = margin if mkt_margin is None else _anchor(margin, mkt_margin, w)
        used_total = total if args.total is None else _anchor(total, args.total, w)
        p_home_raw = normal_p_over(0, margin, sd)
        p_home = normal_p_over(0, used_margin, sd)
        print(f"\n  Team-ratings projection: {hn} {hs:.1f} – {an} {as_:.1f}   (margin {margin:+.1f}, total {total:.1f}), "
              f"{hn} win {p_home_raw:.1%}")
        if mkt_margin is not None:
            print(f"  Market margin {mkt_margin:+.1f}; anchored margin at {w:.0%} model / {1 - w:.0%} market = {used_margin:+.1f}"
                  f"  → {hn} win {p_home:.1%}")
            if abs(margin - mkt_margin) >= 3.5:
                print(f"  ⚠ The model is {abs(margin - mkt_margin):.1f} pts away from the market. The market sees injuries, QB news and "
                      f"matchups this team-level model cannot. Find out WHY before trusting any edge below.")
        if args.spread is not None:
            line = -args.spread
            p, raw = normal_p_over(line, used_margin, sd), normal_p_over(line, margin, sd)
            dec = parse_odds(args.spread_odds)
            print(f"\n  Spread {hn} {args.spread:+g}:")
            _ev_line(f"{hn} {args.spread:+g}", p, dec, raw=raw)
            _ev_line(f"{an} {-args.spread:+g}", 1 - p, dec, raw=1 - raw)
            print("  (pushes and the key numbers 3 and 7 are ignored — shade accordingly)")
        if args.total is not None:
            p, raw = normal_p_over(args.total, used_total, cfg["sd_total"]), normal_p_over(args.total, total, cfg["sd_total"])
            dec = parse_odds(args.total_odds)
            print(f"\n  Total {args.total:g} (model {total:.1f}, anchored {used_total:.1f}):")
            _ev_line(f"Over {args.total:g}", p, dec, raw=raw)
            _ev_line(f"Under {args.total:g}", 1 - p, dec, raw=1 - raw)
        if args.ml:
            print("\n  Moneyline:")
            _ev_line(hn, p_home, dh, fh, raw=p_home_raw)
            _ev_line(an, 1 - p_home, da, 1 - fh, raw=1 - p_home_raw)
        return

    lh, la = max(hs, 0.15), max(as_, 0.15)
    n = 10
    grid = [[poisson_pmf(i, lh) * poisson_pmf(j, la) for j in range(n + 1)] for i in range(n + 1)]
    z = sum(map(sum, grid))
    p_h = sum(grid[i][j] for i in range(n + 1) for j in range(n + 1) if i > j) / z
    p_d = sum(grid[i][i] for i in range(n + 1)) / z
    p_a = 1 - p_h - p_d
    line = args.total if args.total is not None else 2.5
    p_over = sum(grid[i][j] for i in range(n + 1) for j in range(n + 1) if i + j > line) / z
    p_btts = sum(grid[i][j] for i in range(1, n + 1) for j in range(1, n + 1)) / z
    best = max(((i, j) for i in range(n + 1) for j in range(n + 1)), key=lambda ij: grid[ij[0]][ij[1]])
    print(f"\n  Team-ratings projection: {hn} {lh:.2f} – {an} {la:.2f} expected goals   (most likely score {best[0]}-{best[1]})")
    print(f"  1X2: {hn} {p_h:.1%} | draw {p_d:.1%} | {an} {p_a:.1%}")
    print(f"  Over {line:g}: {p_over:.1%} | BTTS: {p_btts:.1%}")
    if args.odds:
        decs = [parse_odds(o) for o in args.odds]
        imp = [1 / d for d in decs]
        fair = [x / sum(imp) for x in imp]
        raw = [p_h, p_d, p_a]
        used = [_anchor(m, f, w) for m, f in zip(raw, fair)]
        print(f"\n  1X2, anchored at {w:.0%} model / {1 - w:.0%} market (book margin {sum(imp) - 1:.1%}):")
        for label, p, d, f, rw in zip((hn, "Draw", an), used, decs, fair, raw):
            _ev_line(label, p, d, f, raw=rw)
        gap = max(abs(m - f) for m, f in zip(raw, fair))
        if gap >= 0.08:
            print(f"  ⚠ The model is up to {gap:.0%} away from the market. The market sees lineups and injuries this team-level "
                  f"model cannot. Find out WHY before trusting any edge above.")
    if args.ou_odds:
        do, du = parse_odds(args.ou_odds[0]), parse_odds(args.ou_odds[1])
        fo = (1 / do) / (1 / do + 1 / du)
        p = _anchor(p_over, fo, w)
        print(f"\n  Total {line:g}:")
        _ev_line(f"Over {line:g}", p, do, fo, raw=p_over)
        _ev_line(f"Under {line:g}", 1 - p, du, 1 - fo, raw=1 - p_over)
    print("\n  Independent-Poisson model: it slightly under-rates draws and 0-0 — be cautious on draw/under value.")


def cmd_backtest(args):
    sport, season = args.sport, args.season
    cfg = dict(CONFIG[sport])
    for key in ("carry", "lam_main", "lam_split"):
        if getattr(args, key.replace("-", "_"), None) is not None:
            cfg[key] = getattr(args, key)
    xgw = 0  # keep the backtest on goals so every season is comparable
    games, _ = load_games(sport, season, with_xg=False)
    prev_games, _ = load_games(sport, season - 1, with_xg=False)
    if not games or not prev_games:
        sys.exit("Need results for both the backtest season and the one before it.")
    key = "week" if sport == "nfl" else "round"
    period_of = lambda g: g.get(key, g.get("round", g.get("week", 0)))  # noqa: E731
    periods = sorted({period_of(g) for g in games})
    start = args.start
    target = make_target(sport, xgw)
    prev = fit(prev_games, None, cfg, target, lam_main=cfg["lam_prior_season"])
    variants = {
        "prior only (last season)":        dict(use_games=False, carry=cfg["carry"], split=True),
        "this season only, no prior":      dict(use_games=True, carry=0.0, split=False),
        "adjusted + prior, NO home/away":  dict(use_games=True, carry=cfg["carry"], split=False),
        "adjusted + prior + home/away":    dict(use_games=True, carry=cfg["carry"], split=True),
    }
    errs = {name: [] for name in variants}
    ll = {name: [] for name in variants}
    base = defaultdict(int)
    for g in games:
        base["h" if g["hs"] > g["as"] else "d" if g["hs"] == g["as"] else "a"] += 1
    for p in periods:
        if p < start:
            continue
        test = [g for g in games if period_of(g) == p]
        train = [g for g in games if period_of(g) < p]
        for name, v in variants.items():
            prior = carry_prior(prev, v["carry"])
            prior = _with_new_team_default(prior, {g[s] for g in train + test for s in ("home", "away")})
            ratings = fit(train if v["use_games"] else [], prior, cfg, target,
                          lam_split=None if v["split"] else 1e9)  # cfg overrides flow in via lam_main/lam_split defaults
            for g in test:
                hs, as_ = predict(ratings, g["home"], g["away"], g.get("neutral", False))
                errs[name].append(((hs - as_) - (g["hs"] - g["as"])))
                if sport == "epl":
                    lh, la = max(hs, .15), max(as_, .15)
                    ph = pd = 0.0
                    for i in range(11):
                        for j in range(11):
                            q = poisson_pmf(i, lh) * poisson_pmf(j, la)
                            if i > j: ph += q
                            elif i == j: pd += q
                    pa = 1 - ph - pd
                    res = ph if g["hs"] > g["as"] else pd if g["hs"] == g["as"] else pa
                    ll[name].append(-math.log(max(res, 1e-9)))
    n = len(next(iter(errs.values())))
    print(f"{cfg['label']} {season} backtest — predict each {key} from games before it (from {key} {start}); {n} games\n")
    print(f"{'model':<34}{'margin MAE':>11}{'RMSE':>8}" + (f"{'1X2 log-loss':>14}" if sport == 'epl' else ""))
    for name, e in errs.items():
        mae = sum(abs(x) for x in e) / len(e)
        rmse = math.sqrt(sum(x * x for x in e) / len(e))
        extra = f"{sum(ll[name]) / len(ll[name]):>14.4f}" if sport == "epl" else ""
        print(f"{name:<34}{mae:>11.2f}{rmse:>8.2f}{extra}")
    if sport == "epl":
        tot = sum(base.values())
        const = -sum(base[k] / tot * math.log(base[k] / tot) for k in base)
        print(f"{'(constant base-rate 1X2)':<34}{'':>11}{'':>8}{const:>14.4f}")
    print("\nLower is better. Bookmaker lines are not in this table: beating a naive baseline is necessary but not sufficient to beat the market.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("sport", choices=["nfl", "epl"])
        p.add_argument("--season", type=int, default=default_season(), help="season start year (default: current)")
        p.add_argument("--refresh", action="store_true", help="ignore the cache and refetch results")
        p.add_argument("--carry", type=float, help="share of last season's rating kept (default per sport)")
        p.add_argument("--lam-main", type=float, help="prior weight, in games, for offence/defence")
        p.add_argument("--lam-split", type=float, help="prior weight, in games, for home/away splits")
        p.add_argument("--xg-weight", type=float, help="EPL: share of the target taken from xG (0 = goals only)")

    p = sub.add_parser("ratings", help="print the rating table")
    common(p)
    p.set_defaults(fn=cmd_ratings)

    p = sub.add_parser("matchup", help="project one game and compare with the market")
    common(p)
    p.add_argument("home")
    p.add_argument("away")
    p.add_argument("--trust", type=float, default=0.30,
                   help="weight on the team-ratings model when blending with the market price (default 0.30; 1 = raw model)")
    p.add_argument("--neutral", action="store_true", help="neutral site (e.g. NFL London): no home edge or splits")
    p.add_argument("--spread", type=float, help="NFL: home team's spread, e.g. -7.5 if the home team is favoured")
    p.add_argument("--spread-odds", default="-110")
    p.add_argument("--total", type=float, help="total line (NFL points / EPL goals, default 2.5)")
    p.add_argument("--total-odds", default="-110", help="NFL total price")
    p.add_argument("--ml", nargs=2, metavar=("HOME", "AWAY"), help="NFL moneyline prices")
    p.add_argument("--odds", nargs=3, metavar=("HOME", "DRAW", "AWAY"), help="EPL 1X2 prices")
    p.add_argument("--ou-odds", nargs=2, metavar=("OVER", "UNDER"), help="EPL over/under prices")
    p.set_defaults(fn=cmd_matchup)

    p = sub.add_parser("backtest", help="walk-forward check of the model on a finished season")
    p.add_argument("sport", choices=["nfl", "epl"])
    p.add_argument("--season", type=int, default=default_season() - 1)
    p.add_argument("--start", type=int, default=5, help="first week/round to predict")
    p.add_argument("--carry", type=float)
    p.add_argument("--lam-main", dest="lam_main", type=float)
    p.add_argument("--lam-split", dest="lam_split", type=float)
    p.add_argument("--quiet", action="store_true", help="print one summary line per variant")
    p.set_defaults(fn=cmd_backtest)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
