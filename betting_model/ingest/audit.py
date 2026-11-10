"""Stage 2 - data quality audit.

Reads the raw downloads, writes cleaned tables to data/clean/ and a report to
data/audit_reports/YYYY-MM-DD.md. Nothing is deleted silently: every change is
logged as a correction (row, old value, new value, reason) and anything that
cannot be fixed safely is listed as unresolved and left in the data, flagged.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ..config import AUDIT_REPORTS, CLEAN, load_config
from .fetch import Fetcher

# One ID map per sport. football-data.co.uk is the only football source in use,
# so its names are canonical; add rows here when a second source is joined.
FOOTBALL_NAME_MAP = {"Man Utd": "Man United", "Manchester United": "Man United",
                     "Manchester City": "Man City", "Nottingham Forest": "Nott'm Forest"}
# nflverse stats files and games.csv differ only for the Rams (LAR vs LA).
NFL_TEAM_MAP = {"LAR": "LA"}

# Was the value knowable before kickoff? Used to stop leakage (Stage 1).
FOOTBALL_AVAILABILITY = [
    ("Div, Date, Time, HomeTeam, AwayTeam", True, "fixture list"),
    ("Referee", True, "appointed days before; confirm on the day"),
    ("B365H/D/A, PSH/D/A, BFEH/D/A, AvgH/D/A, *>2.5, *<2.5, AHh, *AHH/AHA", True,
     "pre-match snapshot collected Friday afternoon (weekend) or Tuesday afternoon (midweek)"),
    ("B365CH.., PSCH.., BFECH.., *C>2.5, AHCh (closing prices)", False,
     "exist only at kickoff; used for closing-line value, never as a model input for an earlier bet"),
    ("FTHG, FTAG, FTR, HTHG, HTAG, HTR", False, "result; usable only from earlier matches"),
    ("HS, AS, HST, AST, HF, AF, HC, AC, HY, AY, HR, AR, HxG, AxG", False,
     "post-match stats; usable only from earlier matches"),
]
NFL_AVAILABILITY = [
    ("game_id, season, week, gameday, gametime, teams, location, roof, surface, rest", True, "schedule"),
    ("spread_line, total_line, moneylines, spread/total odds", False,
     "nflverse stores one consensus line per game, effectively the closing line; "
     "treated as a bet-at-close price in the backtest"),
    ("temp, wind", False, "recorded at kickoff; a forecast must be used for earlier bets"),
    ("home_qb_*, away_qb_*", False, "actual starter, known for certain only at kickoff"),
    ("home_score, away_score, result, total, overtime", False, "result"),
    ("player weekly stats", False, "post-game; usable only from earlier weeks"),
]


class AuditLog:
    def __init__(self):
        self.corrections: list[dict] = []
        self.unresolved: list[dict] = []
        self.summary: list[str] = []

    def fix(self, table, row, column, old, new, reason):
        self.corrections.append(dict(table=table, row=row, column=column, old=old, new=new, reason=reason))

    def flag(self, table, row, issue):
        self.unresolved.append(dict(table=table, row=row, issue=issue))


def _parse_uk_kickoff(date_s: pd.Series, time_s: pd.Series) -> pd.Series:
    """football-data.co.uk dates are dd/mm/yy or dd/mm/yyyy, times are UK local."""
    d = pd.to_datetime(date_s, format="%d/%m/%Y", errors="coerce")
    d2 = pd.to_datetime(date_s, format="%d/%m/%y", errors="coerce")
    d = d.fillna(d2)
    t = time_s.fillna("15:00").astype(str).str.strip()
    local = pd.to_datetime(d.dt.strftime("%Y-%m-%d") + " " + t, errors="coerce")
    return local.dt.tz_localize("Europe/London", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")


def audit_football(cfg: dict, log: AuditLog) -> pd.DataFrame:
    f = Fetcher(cfg)
    frames = []
    for league in cfg["football"]["leagues"]:
        for season in cfg["football"]["seasons"]:
            entry = f.latest("football_data", f"{league}_{season}.csv")
            if entry is None:
                log.flag("football", f"{league}_{season}", "raw file missing - not fetched")
                continue
            df = pd.read_csv(f.path_of(entry), encoding="utf-8-sig", encoding_errors="replace")
            df = df.dropna(how="all")
            df = df[df["HomeTeam"].notna() | df["AwayTeam"].notna()].copy()
            df.insert(0, "season", season)
            df["raw_file"] = entry["path"]
            df["raw_row"] = np.arange(2, len(df) + 2)  # line number in the raw CSV
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    m = pd.concat(frames, ignore_index=True).copy()
    m = m.assign(Time=m["Time"] if "Time" in m else np.nan, kickoff_utc=pd.NaT, kickoff_time_known=False,
                 match_date=pd.NaT, outlier_flag="").copy()
    key = lambda r: f"{r.raw_file}:{r.raw_row}"

    # names: trim whitespace, apply the ID map
    for col in ("HomeTeam", "AwayTeam"):
        cleaned = m[col].astype(str).str.strip().replace(FOOTBALL_NAME_MAP)
        for i in m.index[cleaned != m[col].astype(str)]:
            log.fix("football", key(m.loc[i]), col, m.at[i, col], cleaned[i], "name normalised via ID map")
        m[col] = cleaned

    # dates and kickoff times in UTC
    no_time = m["Time"].isna().sum()
    m["kickoff_utc"] = _parse_uk_kickoff(m["Date"], m["Time"])
    m["kickoff_time_known"] = m["Time"].notna()
    for i in m.index[m["kickoff_utc"].isna()]:
        log.flag("football", key(m.loc[i]), f"unparseable date/time: {m.at[i, 'Date']} {m.at[i, 'Time']}")
    if no_time:
        log.summary.append(f"football: {no_time} rows have no kickoff time; 15:00 UK assumed and flagged "
                           "(kickoff_time_known=False)")
    m["match_date"] = m["kickoff_utc"].dt.tz_convert("Europe/London").dt.tz_localize(None).dt.normalize()

    # duplicates: exact repeats are dropped (logged); conflicting repeats are kept and flagged
    dup_key = ["Div", "season", "HomeTeam", "AwayTeam"]
    for _, grp in m[m.duplicated(dup_key, keep=False)].groupby(dup_key):
        stats = grp.drop(columns=["raw_file", "raw_row"]).astype(str)
        if stats.nunique().max() == 1:
            for i in grp.index[1:]:
                log.fix("football", key(m.loc[i]), "(row)", "duplicate", "dropped",
                        "exact duplicate of an earlier row")
                m = m.drop(index=i)
        else:
            for i in grp.index:
                log.flag("football", key(m.loc[i]),
                         f"fixture appears {len(grp)} times in the season with different values "
                         "(postponed/replayed?) - kept, review manually")

    # results consistency
    played = m["FTHG"].notna() & m["FTAG"].notna()
    exp = np.where(m["FTHG"] > m["FTAG"], "H", np.where(m["FTHG"] < m["FTAG"], "A", "D"))
    for i in m.index[played & (m["FTR"] != exp)]:
        log.flag("football", key(m.loc[i]), f"FTR={m.at[i, 'FTR']} disagrees with score "
                 f"{m.at[i, 'FTHG']}-{m.at[i, 'FTAG']}")
    for i in m.index[~played]:
        log.flag("football", key(m.loc[i]), "no final score recorded")

    # outliers: flagged for manual review, never altered
    checks = {"total goals above 9": (m["FTHG"] + m["FTAG"]) > 9}
    for c in ("HxG", "AxG"):
        if c in m:
            checks[f"{c} above 6"] = m[c] > 6
    price_cols = [c for c in m.columns if c.endswith(("H", "D", "A", ">2.5", "<2.5"))
                  and c[:3] in ("B36", "PSH", "PSD", "PSA", "PSC", "BFE", "Avg", "P>2", "P<2", "PC>", "PC<")]
    for c in price_cols:
        bad = pd.to_numeric(m[c], errors="coerce")
        checks[f"{c} price outside 1.01-1000"] = (bad < 1.01) | (bad > 1000)
    for label, mask in checks.items():
        for i in m.index[mask.fillna(False)]:
            m.at[i, "outlier_flag"] = (m.at[i, "outlier_flag"] + "; " + label).strip("; ")
            log.flag("football", key(m.loc[i]), f"outlier - {label}")

    # missing values per column and season (key columns only)
    keycols = [c for c in ["FTHG", "HST", "AST", "HxG", "B365H", "B365>2.5", "B365CH", "PSH", "P>2.5",
                           "PSCH", "BFEH", "BFE>2.5", "BFECH", "AvgH", "Referee"] if c in m]
    miss = m.groupby("season")[keycols].apply(lambda g: g.isna().sum())
    miss.insert(0, "rows", m.groupby("season").size())
    log.summary.append("football missing values per season (count of rows with no value):\n\n"
                       + miss.to_markdown())
    by_team = pd.concat([m.assign(team=m.HomeTeam), m.assign(team=m.AwayTeam)])
    tm = by_team[by_team[["HST", "AST"]].isna().any(axis=1)].groupby(["season", "team"]).size()
    if len(tm):
        log.summary.append("football teams with missing shot data (season, team, rows): "
                           + ", ".join(f"{s} {t} {n}" for (s, t), n in tm.items()))
    return m.sort_values("kickoff_utc").reset_index(drop=True)


def audit_nfl(cfg: dict, log: AuditLog):
    f = Fetcher(cfg)
    entry = f.latest("nflverse", "games.csv")
    if entry is None:
        log.flag("nfl_games", "games.csv", "raw file missing - not fetched")
        return pd.DataFrame(), pd.DataFrame()
    g = pd.read_csv(f.path_of(entry))
    g["raw_row"] = np.arange(2, len(g) + 2)
    for gid, grp in g[g.duplicated("game_id", keep=False)].groupby("game_id"):
        log.flag("nfl_games", gid, f"game_id appears {len(grp)} times - kept, review manually")
    # kickoff in UTC (gametime is US Eastern)
    local = pd.to_datetime(g["gameday"] + " " + g["gametime"].fillna("13:00"), errors="coerce")
    g["kickoff_utc"] = local.dt.tz_localize("America/New_York", ambiguous="NaT",
                                            nonexistent="NaT").dt.tz_convert("UTC")
    for i in g.index[g["kickoff_utc"].isna()]:
        log.flag("nfl_games", g.at[i, "game_id"], "unparseable kickoff date/time")
    now = pd.Timestamp.now(tz="UTC")
    past = g["kickoff_utc"] < now - pd.Timedelta(hours=30)
    for i in g.index[past & g["home_score"].isna()]:
        log.flag("nfl_games", g.at[i, "game_id"], "kicked off more than 30h ago but has no score")
    hi = (g["home_score"] > 60) | (g["away_score"] > 60)
    for i in g.index[hi.fillna(False)]:
        log.flag("nfl_games", g.at[i, "game_id"], f"outlier - score above 60 "
                 f"({g.at[i, 'away_score']:.0f}-{g.at[i, 'home_score']:.0f}), verify")
    since = g["season"] >= cfg["nfl"]["pool_start_season"]
    # sign convention check: positive spread_line means the home team is favoured
    incons = since & (g["spread_line"].abs() >= 3) & \
        ((g["spread_line"] > 0) != (g["home_moneyline"] < g["away_moneyline"]))
    for i in g.index[incons.fillna(False)]:
        log.flag("nfl_games", g.at[i, "game_id"], "spread sign and moneyline favourite disagree")
    intl = g[since & (g["location"] == "Neutral")]
    log.summary.append(f"nfl: {len(intl)} neutral-site games since {cfg['nfl']['pool_start_season']} "
                       "(international/Super Bowl); kickoff converted from US Eastern to UTC - spot-check: "
                       + ", ".join(f"{r.game_id} {r.kickoff_utc:%Y-%m-%d %H:%M}Z" for r in intl.tail(4).itertuples()))
    cols = ["home_score", "away_score", "home_moneyline", "away_moneyline", "spread_line",
            "home_spread_odds", "away_spread_odds", "total_line", "over_odds", "under_odds"]
    miss = g[since & past].groupby("season")[cols].apply(lambda d: d.isna().sum())
    log.summary.append("nfl missing values per season, completed games:\n\n" + miss.to_markdown())

    # player weekly stats
    frames = []
    for season in cfg["nfl"]["stats_seasons"]:
        e = f.latest("nflverse", f"stats_player_week_{season}.csv")
        if e is None:
            log.flag("nfl_player_weeks", season, "raw file missing - not fetched")
            continue
        keep = ["player_id", "player_display_name", "position", "season", "week", "season_type", "team",
                "opponent_team", "attempts", "passing_tds", "carries", "rushing_yards", "rushing_tds",
                "receptions", "targets", "receiving_yards", "receiving_tds"]
        frames.append(pd.read_csv(f.path_of(e), usecols=keep, low_memory=False))
    p = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if len(p):
        n_noid = int(p["player_id"].isna().sum())
        if n_noid:
            log.flag("nfl_player_weeks", "player_id", f"{n_noid} rows without a gsis player_id - kept, "
                     "excluded from player projections")
        dups = p[p.duplicated(["player_id", "season", "week", "season_type"], keep=False) & p.player_id.notna()]
        for (pid, s, w, _), grp in dups.groupby(["player_id", "season", "week", "season_type"]):
            log.flag("nfl_player_weeks", f"{pid} {s} wk{w}", f"{len(grp)} rows for one player-week "
                     "(traded mid-week?) - kept")
        mapped = p["team"].replace(NFL_TEAM_MAP)
        n = int((mapped != p["team"]).sum())
        if n:
            log.fix("nfl_player_weeks", f"{n} rows", "team", "LAR", "LA",
                    "team abbreviation mapped to the games.csv convention")
        p["team"] = mapped
        p["opponent_team"] = p["opponent_team"].replace(NFL_TEAM_MAP)
        unknown = sorted(set(p["team"].dropna()) - set(g["home_team"]))
        if unknown:
            log.flag("nfl_player_weeks", "team", f"abbreviations not found in games.csv: {unknown}")
    return g, p


def run_audit(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    log = AuditLog()
    fb = audit_football(cfg, log)
    games, players = audit_nfl(cfg, log)
    CLEAN.mkdir(parents=True, exist_ok=True)
    AUDIT_REPORTS.mkdir(parents=True, exist_ok=True)
    fb.to_csv(CLEAN / "football_matches.csv", index=False)
    games.to_csv(CLEAN / "nfl_games.csv", index=False)
    players.to_csv(CLEAN / "nfl_player_weeks.csv", index=False)

    now = datetime.now(timezone.utc)
    lines = [f"# Data audit - {now:%Y-%m-%d %H:%M} UTC", "",
             f"Rows: football {len(fb)}, NFL games {len(games)}, NFL player-weeks {len(players)}.",
             f"Corrections applied: {len(log.corrections)}. Unresolved issues: {len(log.unresolved)}.", "",
             "## Summary", ""]
    lines += [s + "\n" for s in log.summary]
    lines += ["## Available at kickoff?", "", "| sport | columns | usable for a pre-kickoff bet on the same game | when the value exists |",
              "|---|---|---|---|"]
    lines += [f"| football | {c} | {'yes' if a else 'no'} | {w} |" for c, a, w in FOOTBALL_AVAILABILITY]
    lines += [f"| NFL | {c} | {'yes' if a else 'no'} | {w} |" for c, a, w in NFL_AVAILABILITY]
    lines += ["", "## Corrections", ""]
    if log.corrections:
        lines += ["| table | row | column | old | new | reason |", "|---|---|---|---|---|---|"]
        lines += [f"| {c['table']} | {c['row']} | {c['column']} | {c['old']} | {c['new']} | {c['reason']} |"
                  for c in log.corrections]
    else:
        lines.append("None.")
    lines += ["", "## Unresolved issues (data left unchanged)", ""]
    if log.unresolved:
        lines += ["| table | row | issue |", "|---|---|---|"]
        lines += [f"| {u['table']} | {u['row']} | {u['issue']} |" for u in log.unresolved]
    else:
        lines.append("None.")
    report = AUDIT_REPORTS / f"{now:%Y-%m-%d}.md"
    report.write_text("\n".join(lines) + "\n")
    return {"report": report, "corrections": len(log.corrections), "unresolved": len(log.unresolved),
            "football_rows": len(fb), "nfl_games": len(games), "nfl_player_weeks": len(players)}


if __name__ == "__main__":
    print(run_audit())
