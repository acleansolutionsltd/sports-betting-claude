# Prop tools

Small Python 3 scripts (standard library only, no installs) used by `skills/player-props/SKILL.md`.

| Script | What it does | Data source |
|---|---|---|
| `epl_player_log.py "<player>"` | Last N Premier League matches: minutes, shots, SOT, goals, xG, assists, key passes, tackles, interceptions, fouls, passes, crosses, saves + per-match, variance, per-90 | Sofascore public API |
| `nfl_player_log.py "<player>"` | Current-season NFL game log (passing / rushing / receiving / defence) + mean and std dev | ESPN public API |
| `prop_calc.py` | Prices an over/under or one-sided prop (Poisson / negative binomial / normal), removes vig, prints edge, EV and quarter-Kelly | — |

Run from the repo root, for example:

```bash
python3 tools/props/epl_player_log.py "Bukayo Saka" --matches 10
python3 tools/props/prop_calc.py --line 2.5 --over -120 --under -105 --per90 3.23 --minutes 84 --samples 2,4,4,2,3
```

Both data sources are unofficial public endpoints: they can change or rate-limit without notice. If a fetch fails, fall back to the web-search queries in the skill file.

These scripts need an environment that can run code (e.g. Claude Code). In a plain Claude Project, the skill's no-code formulas apply instead.
