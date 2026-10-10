# SKILL: Player Props

> **Purpose:** Turn player game logs into a projected stat line, price the prop as a probability, and bet only when the projection beats the vig-free book price by the edge threshold. Covers football (shots, shots on target, goals, tackles, fouls, passes, saves) and NFL (passing/rushing/receiving yards, receptions, attempts, TDs).

---

## When to use this skill

- "Any good prop bets for [game]?"
- "Should I take [player] over [line] [stat]?"
- After the `lineup-check` skill confirms a player starts. **Props are always lineup-dependent**: never finalise one before the XI or inactives are out.

---

## Step 1 — Pull the game log

Use the tools in `tools/props/` when you can run code (Claude Code, or any environment with Python 3). Otherwise, use web search.

```bash
# Premier League (Sofascore): last N league matches, per-match + per-90 + variance
python3 tools/props/epl_player_log.py "Bukayo Saka" --matches 10

# NFL (ESPN): this season's game log with mean and std dev per column
python3 tools/props/nfl_player_log.py "Jahmyr Gibbs"
```

Without code, search:
```
"[player] stats per 90 [season]"         → FotMob, Sofascore, Understat
"[player] game log [season]"             → ESPN, Pro Football Reference
"[opponent] shots conceded per game"     → FotMob team stats
"[opponent] yards allowed to RBs/WRs"    → FantasyPros, Sharp Football Analysis
```

Record, per game: **minutes / snaps**, the stat, and the opponent. Ten games is the target sample. Fewer than five means the sample is too small to use without a prior (Step 2c).

---

## Step 2 — Project the mean

### 2a. Rate × opportunity
Props are driven by **volume first, efficiency second**.

```
Football:  projected stat = per-90 rate × (expected minutes / 90)
NFL:       projected stat = per-game volume (targets, carries, attempts) × per-touch rate
```

Expected minutes: use the average when the player starts (from the log), not the season average including sub appearances. Reduce it for:
```
Returning from injury (first 1–2 games back):   −15 to −30 min
Fixture congestion / rotation risk:              −10 to −20 min
Yellow card risk for defenders on 4 bookings:    no change (books ignore it too)
```

### 2b. Opponent adjustment (`--opp-adj`)
```
opp-adj = opponent's stat conceded per game / league average conceded

Football: shots / SOT conceded, tackles attempted against (higher opp possession → more tackles for your player)
NFL:      yards per target / per carry allowed to the position, pace (plays per game)
```
Cap the adjustment at 0.80–1.25 — beyond that you are fitting noise.

### 2c. Shrink small samples (`--prior`, `--games`)
Early-season and small samples overstate both hot and cold streaks. Always blend toward a longer-run rate (last season, career, or position average):

```
projection = (n_recent × recent_rate + 6 × prior_rate) / (n_recent + 6)
```

Example: 4 games at 88 rushing yards vs a 70-yard prior → 77 yards, not 88. That difference alone can erase an apparent 10% edge.

### 2d. Game script (NFL)
- Big favourite → more rushing attempts for its RB late, fewer passing yards for its QB.
- Big underdog → more pass attempts and targets, fewer carries.
- Shift volume by 10–15% when the spread is 7+.

---

## Step 3 — Price it

```bash
# Count stats: shots, SOT, tackles, receptions, attempts
python3 tools/props/prop_calc.py --line 2.5 --over -120 --under -105 \
    --per90 3.23 --minutes 84 --samples 2,4,4,2,3 --opp-adj 1.10 --prior 2.8 --games 5

# Yardage: normal model, SD from the game log
python3 tools/props/prop_calc.py --line 74.5 --over -115 --under -115 \
    --mean 88.2 --sd 51 --dist normal --prior 70 --games 4

# Anytime scorer / anytime TD: one-sided market
python3 tools/props/prop_calc.py --line 0.5 --over +150 --mean 0.45
```

The calculator:
- uses **Poisson** for counts, switching to **negative binomial** automatically when the game log shows more variance than Poisson allows (shots and tackles often do)
- uses **normal** for yards
- removes the vig from the over/under pair (or assumes ~7% on one-sided markets)
- prints model vs market probability, edge, EV, and quarter-Kelly stake

**Without code**, use these approximations:
```
Count stat, Poisson:  P(X ≥ 1) = 1 − e^(−λ)
                      P(X ≥ 2) = 1 − e^(−λ)(1 + λ)
                      P(X ≥ 3) = 1 − e^(−λ)(1 + λ + λ²/2)
Yards, normal:        P(over) ≈ Φ((mean − line) / sd)   (sd ≈ 0.55 × mean for RB/WR yards)
Anytime goal (football): λ ≈ non-penalty xG per 90 × minutes/90 (+ penalty xG if on pens)
```

---

## Step 4 — Edge and sizing

Use the standard edge threshold (2%) and the bankroll skill, with prop-specific caps:

```
Max per prop:                      2 units (props are lower-limit, higher-variance markets)
Max per player per game:           3 units total across all their props
Max props per game:                3 (stacked props on one game are correlated)
Anytime scorer / anytime TD:       max 1 unit
```

Correlated props (e.g. QB passing yards + his WR1 receiving yards) are one bet for exposure purposes. Never parlay them as if they were independent.

---

## Step 5 — Lineup gate

Before placing any prop:
- [ ] Player confirmed in the starting XI / active list (`lineup-check`)
- [ ] Role unchanged (position, set-piece or penalty duty, snap share)
- [ ] Price re-checked after lineups (prop prices move fast on team news)

If the player is benched or inactive, most books void the bet. Check the book's rules: some settle "1 minute played", so a late sub cameo is a loss.

---

## Market-specific notes

### Football
| Prop | Key driver | Watch for |
|---|---|---|
| Shots / shots on target | Minutes, team's expected possession, opponent's shots conceded | Blocked shots count as shots but not SOT |
| Anytime goalscorer | Non-penalty xG + penalty duty | Books shade popular names (name/brand bias) |
| Tackles | Opponent possession share, player role (DM/FB) | Very sensitive to game state; use negative binomial |
| Fouls committed / won | Referee fouls-per-game, opponent dribble rate | Referee assignment is announced ~48h before |
| Passes | Team possession, minutes | Low-variance; edges are small but frequent |
| Goalkeeper saves | Opponent SOT per game | Saves = opponent SOT − goals conceded |

### NFL
| Prop | Key driver | Watch for |
|---|---|---|
| Receiving yards / receptions | Target share × team pass attempts | Shadow corners, injuries to other WRs (target redistribution) |
| Rushing yards / attempts | Snap share, carry share, game script | Goal-line back vs early-down back |
| Passing yards / attempts | Pace, spread, opponent pass defence | Weather (wind > 15 mph) |
| Anytime TD | Red-zone share | Heavily vigged — rarely +EV except on backups promoted by injury |

---

## Red flags (lean to pass)

```
❌ Fewer than 5 games in the sample and no prior used
❌ Edge comes from one outlier game (e.g. one 8-shot or 160-yard game) — re-run without it
❌ Player's role changed recently (new manager, position switch, new QB)
❌ Line already moved 0.5+ (counts) or 5+ yards since open in your direction
❌ Popular-name anytime scorer at short odds
❌ Lineup not confirmed
❌ The prop is in a game you already bet on the same side (correlated exposure)
```

---

## Output block

Use the standard output format with `Market: Prop`, plus:

```
Player:       [name] ([team], [position])
Prop:         [stat] [over/under] [line]
Projection:   [mean] (rate [x] × [minutes/volume], opp-adj [x], shrunk to prior [y])
Model P:      [X]%   |   Market P (vig-free): [X]%   |   Edge: [+X]%
Sample:       last [N] games: [values]
Lineup:       [CONFIRMED / PENDING — re-check at [time]]
```
