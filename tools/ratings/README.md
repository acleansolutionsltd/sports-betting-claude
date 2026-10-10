# Team ratings tool

`team_ratings.py` (Python 3, standard library only) fits opponent-adjusted offence/defence ratings with a home edge and shrunk home/away splits, then projects matchups and prices them against the market. Used by `skills/team-ratings/SKILL.md`.

| Command | What it does |
|---|---|
| `ratings nfl\|epl` | Rating table: offence, defence, net, home/away split per team |
| `matchup nfl\|epl HOME AWAY [prices]` | Projected score / xG, win and market probabilities, edge and EV vs the prices you pass |
| `backtest nfl\|epl --season YYYY` | Walk-forward test: predicts each week/round using only earlier games |

Data: NFL results from ESPN's scoreboard API; Premier League results and match xG from Sofascore. Both are unofficial public endpoints and can change or rate-limit. Results are cached in `tools/ratings/cache/` (git-ignored); only new games are fetched. Use `--refresh` to rebuild a cache.

Run from the repo root, for example:

```bash
python3 tools/ratings/team_ratings.py ratings epl
python3 tools/ratings/team_ratings.py matchup nfl TEN HOU --spread 7.5 --ml 310 -390
python3 tools/ratings/team_ratings.py backtest nfl --season 2025
```

Tuning flags (`--carry`, `--lam-main`, `--lam-split`, `--xg-weight`, `--trust`) are documented in `--help`.
