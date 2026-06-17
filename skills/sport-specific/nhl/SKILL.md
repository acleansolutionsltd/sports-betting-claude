# SKILL: NHL Context

> **Purpose:** NHL betting is fundamentally a goaltending market. Getting goalie right is 60% of the edge.

---

## The NHL betting hierarchy

```
1. Goalie matchup         (dominant factor — confirm before any bet)
2. PDO and regression     (luck normalization — massive edge source)
3. Corsi/Fenwick metrics  (possession-based true quality)
4. Schedule and fatigue   (B2B in NHL significant)
5. Power play differential (special teams matter in close games)
```

---

## Goaltending (most critical)

### Always confirm before betting

```
Starting goalies are NOT official until 30-60 minutes before puck drop.
Never bet an NHL game without confirmed goalies.

Search: "[team] starting goalie tonight [date]"
        "NHL starting goalies [today]"
        "@DailyFaceoff on Twitter/X" (most reliable source)
```

### Goalie quality tiers

```
Tier 1 (Elite): SV% > .920 (5-year), GAA < 2.50
Tier 2 (Above avg): SV% .912-.920
Tier 3 (Average): SV% .905-.912
Tier 4 (Below avg): SV% < .905

Matchup: T1 vs T4 → significant goalie edge
Matchup: T1 vs T3 → moderate edge
Matchup: T2 vs T2 → no goalie edge, use other factors

Backup goalie: adjust line -0.3 to -0.6 on puck line
Elite backup vs weak starter: may flip the value
```

### Goalie fatigue

```
Playing every other game: normal NHL rotation, no adjustment
Playing 3+ games in 5 nights: fatigue factor, slight lean against
Last start: was it a high-save-count game (40+ saves)? Fatigue risk
```

---

## PDO and regression (highest edge-per-insight ratio)

PDO = Team SH% + Team SV% (combined). League average is always ~100%.

```
PDO > 104 = team is unsustainably hot (expect regression to ~100%)
PDO < 96  = team is unsustainably cold (expect positive regression)

Teams with PDO > 104 in wins column are due for a correction.
Teams with PDO < 96 are likely better than their record suggests.

Lean: Fade high-PDO teams, back low-PDO teams (for value, not blindly)

Source: Search "[team] PDO [season]" or Natural Stat Trick (naturalstattrick.com)
```

---

## Corsi and Fenwick (possession metrics)

These measure shot attempt dominance — the best predictor of future performance.

```
CF% (Corsi For%): Team's shot attempts / (Team's + Opponent's shot attempts)
FF% (Fenwick For%): Same but excludes blocked shots

CF% > 55%: team is dominating possession
CF% 50-55%: slight possession edge
CF% < 45%: being dominated (even if winning via goaltending or power play)

Use: Teams with high CF% but bad record = value bet (process is right, results will follow)
     Teams with low CF% but good record = fade candidate

Source: naturalstattrick.com — sort by CF% at even strength
```

---

## Schedule and fatigue

```
Back-to-back adjustment:
  Road B2B: -0.2 to -0.4 on puck line
  Home B2B: -0.1 to -0.2 on puck line
  
3-in-4 nights (third game):
  -0.3 to -0.5 on puck line regardless of home/away

Note: NHL teams are experienced with B2B — effect smaller than NBA
      BUT: second game with backup goalie in net = significant value

Travel adjustment:
  Cross-country overnight travel: slight fatigue (-0.1 to -0.2)
  Within-division travel: minimal
```

---

## Special teams differential

```
Power play and penalty kill differential matters more than public thinks:

PP% difference > 8 points: 0.2 to 0.3 puck line adjustment toward better PP team
PK% difference > 8 points: 0.2 to 0.3 puck line adjustment toward better PK team

Source: Search "[team] power play percentage [season]"
NHL.com tracks this under team stats
```

---

## NHL totals (over/under puck totals)

```
Standard total: 5.5 or 6 goals

Lean over when:
  Both teams in top-third of pace (shots for/60)
  Both goalies are Tier 3 or below
  Both teams with positive PDO regression due
  Divisional game with recent history of high-scoring matchups
  
Lean under when:
  Elite goalie matchup (both Tier 1)
  Both teams with high PDO (regression due)
  One team dominant CF% → clean defensive structure
  Late-season game with playoff positioning locked
```

---

## Regulation result vs including OT

```
Most NHL bets are on "regulation and OT" or "including OT/SO"
Be aware: ~25% of NHL games go to OT/SO

Puck line (-1.5 / +1.5):
  Much harder to cover -1.5 when 25% of games go to 1-goal OT outcomes
  Best on: games with clear talent gap and strong starting goalie for favorite
  Avoid puck line when: teams evenly matched or close recent head-to-head
  
ML:
  Underdogs win more often than in other sports (goalies can steal games)
  +130 to +165 underdogs often offer positive EV in close matchups
```

---

## Red flags

```
❌ Goalie not confirmed — always wait, never assume
❌ Team with PDO > 106 riding a long win streak (peak fade spot)
❌ Backup goalie rumored but not confirmed — wait for official word
❌ Betting the total without checking both goalies' recent form
❌ Divisional playoff race game — motivational factor compresses line value
❌ Both teams coming off games last night in different cities
```

---

## Key sources

```
Natural Stat Trick: naturalstattrick.com (best advanced stats source, free)
DailyFaceoff: dailyfaceoff.com (goalie confirmations)
EliteProspects: lineup tracking
MoneyPuck: model-based projections

Search queries:
"[team] starting goalie tonight"
"NHL starting goalies confirmed [date]"
"[team] Corsi For% [season] [naturalstattrick.com]"
"[team] PDO [season]"
"[team] power play percentage [season]"
"[team] goals for per game [season]"
```
