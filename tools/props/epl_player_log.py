#!/usr/bin/env python3
"""Premier League player match log from Sofascore.

Usage:
  python3 tools/props/epl_player_log.py "Bukayo Saka"
  python3 tools/props/epl_player_log.py "Bukayo Saka" --matches 10 --json

Prints one row per finished Premier League match (most recent first) plus
per-match and per-90 averages, ready to feed into prop_calc.py.
"""
import argparse
import json
import sys
import urllib.parse

from _common import get_json, mean_var

API = "https://www.sofascore.com/api/v1"
PREMIER_LEAGUE_ID = 17

# Sofascore field -> column name
STATS = {
    "minutesPlayed": "min",
    "totalShots": "shots",
    "onTargetScoringAttempt": "sot",
    "goals": "goals",
    "expectedGoals": "xg",
    "goalAssist": "ast",
    "keyPass": "keyp",
    "totalTackle": "tkl",
    "interceptionWon": "int",
    "fouls": "fouls",
    "wasFouled": "fouled",
    "totalPass": "passes",
    "totalCross": "crosses",
    "saves": "saves",
}
# Sofascore omits zero-valued keys, so a missing key means 0.


def find_player(name):
    data = get_json(f"{API}/search/all?q={urllib.parse.quote(name)}&page=0")
    for r in data.get("results", []):
        if r.get("type") == "player":
            e = r["entity"]
            return e["id"], e["name"], e.get("team", {}).get("name", "?")
    sys.exit(f"No Sofascore player found for '{name}'")


def finished_league_events(player_id, wanted):
    events, page = [], 0
    while len(events) < wanted and page < 6:
        data = get_json(f"{API}/player/{player_id}/events/last/{page}")
        batch = [e for e in data.get("events", [])
                 if e["status"]["type"] == "finished"
                 and e["tournament"]["uniqueTournament"]["id"] == PREMIER_LEAGUE_ID]
        events.extend(sorted(batch, key=lambda e: -e["startTimestamp"]))
        if not data.get("hasNextPage"):
            break
        page += 1
    return sorted(events, key=lambda e: -e["startTimestamp"])[:wanted]


def match_row(event, player_id):
    try:
        stats = get_json(f"{API}/event/{event['id']}/player/{player_id}/statistics").get("statistics", {})
    except Exception:
        stats = {}  # unused substitute / no data
    row = {"date": event["startTimestamp"]}
    home, away = event["homeTeam"]["name"], event["awayTeam"]["name"]
    row["fixture"] = f"{home} v {away}"
    for key, col in STATS.items():
        row[col] = stats.get(key, 0) or 0
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("player")
    ap.add_argument("--matches", type=int, default=10)
    ap.add_argument("--json", action="store_true", help="print raw rows as JSON")
    args = ap.parse_args()

    pid, name, team = find_player(args.player)
    events = finished_league_events(pid, args.matches)
    rows = [match_row(e, pid) for e in events]
    played = [r for r in rows if r["min"] > 0]

    if args.json:
        print(json.dumps({"player": name, "team": team, "matches": rows}, indent=2))
        return

    cols = list(STATS.values())
    print(f"{name} ({team}) — last {len(rows)} Premier League matches, {len(played)} played\n")
    print(f"{'fixture':40}" + "".join(f"{c:>8}" for c in cols))
    for r in rows:
        print(f"{r['fixture'][:39]:40}" + "".join(
            f"{r[c]:>8.2f}" if isinstance(r[c], float) else f"{r[c]:>8}" for c in cols))

    if not played:
        return
    total_min = sum(r["min"] for r in played)
    print(f"\n{'per match (played)':40}" + "".join(
        f"{mean_var([r[c] for r in played])[0]:>8.2f}" for c in cols))
    print(f"{'variance':40}" + "".join(
        f"{mean_var([r[c] for r in played])[1]:>8.2f}" for c in cols))
    print(f"{'per 90':40}" + "".join(
        f"{'':>8}" if c == "min" else f"{sum(r[c] for r in played) / total_min * 90:>8.2f}" for c in cols))
    print(f"\nAvg minutes when playing: {total_min / len(played):.0f}")
    print("Sample values for prop_calc.py --samples, e.g. shots: "
          + ",".join(str(r["shots"]) for r in played))


if __name__ == "__main__":
    main()
