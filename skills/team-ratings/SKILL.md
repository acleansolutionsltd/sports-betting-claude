# SKILL: Team Ratings & Matchups

> **Purpose:** Replace "gut feel" team strength with opponent-adjusted offence/defence ratings, so every game is judged on how each side's attack matches up against the other's defence, with home/away form and schedule strength accounted for. Used for NFL and Premier League.

---

## When to use this skill

Run it **before** estimating a true probability for any side, spread, total or 1X2 market (edge-detection Step 2). It gives you the base number; lineups, injuries and situational spots then adjust it.

It is *not* a replacement for team news. It rates teams, not players: a missing quarterback or goalkeeper is invisible to it.

---

## What the ratings are

For every game, each side's score is explained by **its own attack** and **the opponent's defence**, plus a home edge:

```
home score = league home average + home offence + opponent's defence (away)
away score = league away average + away offence + opponent's defence (home)
```

Fitted over every game so far, so a team that has scored a lot against weak defences is rated lower than one that has scored the same against strong ones (schedule strength is built in).

| Column | Meaning |
|---|---|
| `off` | points (goals) per game above league average scored |
| `def` | points (goals) per game above average **prevented** (+ is good) |
| `net` | `off + def`: the rating gap between two teams is their projected margin before home edge |
| `off / def home/away` | how much better (+) the side is at home than on the road |

**Small samples are pulled toward last season.** Ratings start from last season's (regressed toward average: NFL keeps 35%, Premier League 70%), and are replaced by this season's evidence as games accumulate. Promoted Premier League clubs start from the average of last season's three weakest sides. Premier League ratings blend goals with **match xG** (50/50), which is far less noisy than goals alone.

---

## Commands

```bash
# Rating table
python3 tools/ratings/team_ratings.py ratings nfl
python3 tools/ratings/team_ratings.py ratings epl

# One game against the market: pass whatever prices you have
python3 tools/ratings/team_ratings.py matchup nfl TEN HOU --spread 7.5 --total 38.5 --ml 310 -390
python3 tools/ratings/team_ratings.py matchup nfl JAX PHI --neutral --spread -7.5      # London game
python3 tools/ratings/team_ratings.py matchup epl Sunderland Brighton --odds +199 +246 +130 --ou-odds -110 -110

# Check the model on a finished season (walk-forward, no peeking)
python3 tools/ratings/team_ratings.py backtest nfl --season 2025
python3 tools/ratings/team_ratings.py backtest epl --season 2025 --start 6
```

Home team is the first name, away the second. Names match by abbreviation or any part of the team name. `--neutral` removes home edge (use for NFL international games). Results are cached in `tools/ratings/cache/` and only new games are fetched.

No code environment? Search the same inputs by hand: points/goals scored and allowed per game, strength of schedule, home and away splits (`"[team] points allowed per game home away"`, FBref/Understat/FotMob team xG tables), and apply the "no-code" checklist below.

---

## How to use the output

### 1. Look at the gap, not the label
The `net` gap plus home edge is the projected margin. Compare it with the market line, not with the team rankings you remember.

### 2. Anchor to the market (`--trust`)
Ratings are team-level and blind to lineups, injuries and weather, so the tool blends its probability with the market's vig-free price (`--trust 0.30` = 30% model / 70% market). This is deliberate: a raw model that disagrees wildly with a sharp line is almost always the model that is missing something.

Large disagreement triggers a warning (≥ 3.5 points in the NFL, ≥ 8 percentage points in the Premier League). Treat it as a question to investigate:

```
□ Is a QB / goalkeeper / key starter out that the ratings can't see?
□ Did one blow-out game distort a 4-game sample?
□ Is last season's carry-over wrong (new coach, new QB, big transfers)?
□ Is the line stale (check timestamp), or has it already moved?
```

Only if you can say why the market is wrong does the edge count.

### 3. Feed the edge-detection skill
The anchored probability is your "Your P(win)". Then apply:
- lineup/injury adjustments (sport skill, `lineup-check`)
- situational spots (rest, travel, motivation)
- anti-bias checklist, Kelly sizing and tier caps as usual

Do **not** apply a second home-field bump: home edge is already inside the projection.

---

## Home/away form: what the evidence shows

The model estimates a separate home and away offence/defence for every team but shrinks them heavily toward zero. Walk-forward backtests on 2024 and 2025 (see below) showed that **freeing the home/away split made predictions slightly worse in both sports**: a team's home and away numbers are mostly noise over fewer than ~10 games per venue.

So:
- The projection uses the split only to the small extent the data supports.
- Don't bet a team "because they're great at home" off 2–3 home games.
- The split column becomes worth reading late in the season (NFL: week 12+; Premier League: after ~15 home and 15 away games).

---

## Sample-size rules

| Games played | Treatment |
|---|---|
| < 4 | Ratings are mostly last season: treat projections as rough |
| 4–8 | Usable; lean on the market anchor (`--trust` ≤ 0.35) |
| 9+ | Usable; may raise `--trust` to 0.40–0.50 if backtests on your own bets support it |
| First week after a coaching or QB change | Carry-over is unreliable: lower `--carry` or discount the rating |

---

## Backtest results

Walk-forward tests: each week from week 5 is predicted using only earlier games. Average error in the predicted margin (points; lower is better), 208 games per season:

| NFL model | 2024 | 2025 |
|---|---|---|
| Last season's ratings only | 11.09 | 11.27 |
| This season's results only (no prior) | 10.11 | 10.57 |
| Opponent-adjusted + last-season prior (**default**) | 10.01 | 10.66 |
| ... plus freed home/away split | 10.01 | 10.69 |

Reading it honestly:
- Opponent-adjusted ratings clearly beat carrying last season's ratings forward.
- The last-season prior helps in one season and is neutral-to-slightly-negative in the other, so it is kept deliberately small.
- A typical NFL margin error of about 10 points is large: a team-ratings model alone gets you to "roughly right", not to "better than the market". That is why matchup output is anchored to the market price.
- These tests compare against naive baselines, not bookmaker lines. Beating the closing line is the real test: log CLV on every bet.

*Premier League backtest results: to be added.*

---

## Red flags (lean to pass)

```
❌ Model edge exists only at raw trust (--trust 1) and vanishes when anchored to the market
❌ Warning printed (model far from the market) and you can't explain it
❌ Team has fewer than 4 games and a coaching, QB or squad overhaul since last season
❌ Rating is driven by one outlier result (check with that game removed)
❌ Using the home/away split of a team with under 5 home games
❌ A big ratings edge on a team whose key player (QB, goalkeeper, top scorer) is out
```

---

## Output block

Add to the standard bet output:

```
Ratings:      [Home] net [+x.x] ([n] GP) vs [Away] net [+x.x] ([n] GP)
Projection:   [score line / xG], margin [+x.x]
Market:       [line], model vs market gap [x.x]
Model P:      raw [X]% → anchored [X]% (trust [0.30])
```
