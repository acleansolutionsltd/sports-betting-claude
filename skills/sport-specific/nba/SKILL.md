# SKILL: NBA Context

> **Purpose:** NBA-specific factors that dramatically affect line value and are frequently mispriced by the market.

---

## Why NBA is one of the most bettable sports

- Long season (82 games) = massive data sample
- Injuries announced same-day but often predictable if you follow beat reporters
- Rest/fatigue effects are measurable and consistent
- Back-to-back performance decline is well-documented
- Public overweights star names; sharps exploit team-level factors

---

## Highest-impact NBA factors

### 1. Rest and back-to-backs (single biggest edge)

```
B2B: Team playing second game of back-to-back

Historical performance drop (B2B road game):
  Win rate: ~4-5% below expected
  Point differential: -2.5 to -4.5 points vs rested opponent

B2B home game:
  Slightly better than road, but still -1.5 to -2.5 points
  
Second road game in 3 nights:
  -3 to -5 points adjustment
  
Stars on B2B:
  Rest management common — check if star is likely to sit
  Search: "[player] rest [tonight's date]" or "[team] load management"
```

**Key context:** The line often doesn't fully adjust for B2B because public bets on names, not schedules. This is one of the most consistent edges in the NBA.

### 2. Load management and rest days

```
Signs a star might sit:
  - B2B with low-stakes game
  - Minor nagging injury reported in week
  - Teams that have historically load-managed (Lakers, Clippers, Spurs-era)
  - Returning from recent absence

If star sits: adjust line -6 to -10 points depending on player
If you suspect rest but it's not confirmed: reduce confidence tier by one
```

### 3. Pace and totals

```
Calculate expected pace:
  Team A pace rank (possessions per 48 min) + Team B pace rank / 2 vs league average

Fast-fast matchup: over-lean on total
Slow-slow matchup: under-lean on total
Fast vs slow: total is usually set correctly, look elsewhere

Source: Search "[team] pace per 100 possessions [season]" or Basketball-Reference
```

### 4. Three-point variance

NBA totals have high variance due to three-point volume. Adjust:

```
High-3PT-attempt teams: total variance is higher, widen your confidence intervals
Games with two high-3PT teams: avoid totals unless edge is very large (>4%)
Regression: if team shot 45% from 3 last week, expect regression to 36-38%
```

### 5. Officiating crew

```
Fast whistle refs = more free throws = more points (lean over on totals)
Slow whistle refs = fewer stoppages = lean under

Search: "NBA referee [tonight] crew" 
        "NBA referee foul rate stats [season]"

Source: Official NBA referee assignments usually posted day-of
```

### 6. Defensive matchup (for props)

```
For player props:
  [Player position] vs [opponent defensive rating vs that position]
  Example: PG prop → check opponent's defensive rating against PGs

Source: Search "[team] defensive rating vs [position] [season]"
NBA.com has positional defensive tracking
```

### 7. Home court advantage

```
Standard: +3 to +4 points
Exceptions (higher HCA):
  - Denver Nuggets (altitude factor) → +5 to +6
  - Oklahoma City (crowd, new era): +4 to +5
  - Miami (road team fatigue in humidity): slight lean
  
Diminished HCA:
  - Teams with poor home record in current season (check standings)
  - Rivalry games with large away fan presence in market
```

---

## NBA-specific red flags

```
❌ Starting lineup not confirmed when you're betting a prop — wait until official
❌ Total set around a major number (210, 220, 230) — sharpest markets cluster here
❌ Home favorite in a 0-game (meaningless game, playoff positioning locked up)
❌ B2B team on BOTH sides — variance spike, no directional edge
❌ Returning from injury game — star playing but minutes restriction likely
❌ Teams that have played 4 games in 6 nights — cumulative fatigue
```

---

## Sources to search

```
"[team] injury report [today]"
"[player] sitting out tonight [date]"
"NBA schedule rest teams tonight"
"[team] pace per 100 possessions [season]"
"NBA referees tonight assignment"
"[team] back-to-back schedule [month]"
"[player] load management history [season]"
```

---

## Quick adjustments table

| Situation | Adjustment |
|---|---|
| Away team on B2B | -3.5 to -4.5 points |
| Home team on B2B | -2 to -3 points |
| Star sitting (confirmed) | -7 to -10 points |
| Back-to-back total (both rested) | Use pace model |
| Back-to-back total (one tired) | -4 to -6 on total |
| Altitude game (Denver) | +1 to +2 to home side |
| High foul-rate ref crew | +3 to +5 on total |
| Low foul-rate ref crew | -2 to -4 on total |
