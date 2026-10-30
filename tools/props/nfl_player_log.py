#!/usr/bin/env python3
"""NFL player game log from ESPN.

Usage:
  python3 tools/props/nfl_player_log.py "Jahmyr Gibbs"
  python3 tools/props/nfl_player_log.py "Jalen Hurts" --season 2026 --json

Prints every stat ESPN logs for the player this season (passing, rushing,
receiving, defense — whichever apply), one row per game, plus mean and
standard deviation per column for prop_calc.py.
"""
import argparse
import datetime
import json
import sys
import urllib.parse

from _common import get_json, mean_var

SEARCH = "https://site.web.api.espn.com/apis/search/v2?limit=5&query={}"
GAMELOG = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{}/gamelog?season={}"


def find_player(name):
    data = get_json(SEARCH.format(urllib.parse.quote(name)))
    for group in data.get("results", []):
        if group.get("type") != "player":
            continue
        for c in group.get("contents", []):
            uid = c.get("uid", "")
            if "l:28" in uid:  # l:28 = NFL
                return uid.split("a:")[-1], c.get("displayName")
    sys.exit(f"No ESPN NFL player found for '{name}'")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("player")
    ap.add_argument("--season", type=int, default=datetime.date.today().year)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    athlete_id, name = find_player(args.player)
    data = get_json(GAMELOG.format(athlete_id, args.season))
    labels = data.get("labels", [])
    names = data.get("names", [])
    meta = data.get("events", {})

    rows = []
    for season_type in data.get("seasonTypes", []):
        if "Regular" not in season_type.get("displayName", ""):
            continue
        for cat in season_type.get("categories", []):
            for ev in cat.get("events", []):
                info = meta.get(ev["eventId"], {})
                opp = info.get("opponent", {}).get("abbreviation", "?")
                at = info.get("atVs", "")
                week = info.get("week", 0)
                rows.append({"week": week, "game": f"wk{week} {at} {opp}",
                             **{n: _num(v) for n, v in zip(names, ev["stats"])}})
    rows.sort(key=lambda r: r["week"])

    if args.json:
        print(json.dumps({"player": name, "season": args.season, "games": rows}, indent=2))
        return
    if not rows:
        sys.exit(f"{name}: no regular-season games logged for {args.season}")

    width = 9
    print(f"{name} — {args.season} regular season, {len(rows)} games\n")
    print(f"{'game':14}" + "".join(f"{l[:width - 1]:>{width}}" for l in labels))
    for r in rows:
        print(f"{r['game'][:13]:14}" + "".join(f"{r[n]:>{width}g}" for n in names))
    print(f"\n{'mean':14}" + "".join(f"{mean_var([r[n] for r in rows])[0]:>{width}.1f}" for n in names))
    print(f"{'std dev':14}" + "".join(f"{mean_var([r[n] for r in rows])[1] ** 0.5:>{width}.1f}" for n in names))
    print("\nColumns: " + ", ".join(f"{l}={n}" for l, n in zip(labels, names)))


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return 0.0


if __name__ == "__main__":
    main()
