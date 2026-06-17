# SKILL: Data Ingestion

> **Purpose:** Tell Claude exactly where to look for data, what to extract, and how to structure it before any analysis begins.

---

## When to use this skill

Load this skill any time you need current data before making a bet recommendation. This includes:
- Daily slate pull ("what games are on today?")
- Injury and roster updates
- Line movement tracking
- Weather and venue checks
- Sharp money signals

---

## Search sequence (always follow this order)

### 1. Today's slate

Search: `[sport] schedule today [date]`

Extract:
- Game time (convert to local time)
- Home team / Away team
- Venue
- TV/broadcast (indicates importance)

Sources (in order of reliability):
- ESPN.com schedule pages
- The Athletic
- Official league sites (nfl.com, nba.com, mlb.com, nhl.com)

### 2. Injury and roster reports

Search: `[team] injury report [today's date]`

For each game, pull both teams. Extract:
- Player name
- Status: Out / Doubtful / Questionable / Probable / GTD
- Position and role (starter? key rotation player?)
- Nature of injury if disclosed
- Trend: getting better or worse?

**Critical positions by sport:**
- NFL: QB, OL starters, CB1, pass rushers
- NBA: Any starter or 30+ MPG player
- MLB: Starting pitcher (non-negotiable), closer
- NHL: Starting goalie (non-negotiable), top-6 forwards

Sources:
- Rotoworld / NBC Sports edge
- Team official injury report (NFL mandated Wed/Thu/Fri)
- Beat reporters on Twitter/X for late scratches
- ESPN injury tracker

### 3. Line movement

Search: `[game] opening line vs current line` or `[game] line movement`

Extract:
- Opening line (what books opened at)
- Current line (where it sits now)
- Direction of movement
- Movement magnitude (e.g., -3 → -4.5 is significant)

**Interpret movement:**
```
Public bet % high on Team A AND line moves toward Team A = public steam (fade signal)
Public bet % high on Team A AND line moves AWAY from Team A = reverse line movement (sharp signal — follow)
Line moves with no public action = sharp/professional money
Line moves back after moving = two-way action, no clear signal
```

Sources:
- Action Network
- OddsShark
- VegasInsider
- Pregame.com

### 4. Best available line (line shopping)

Search: `[team] [market] odds comparison` or check directly:

For each candidate bet, find the best number available across:
- DraftKings
- FanDuel
- BetMGM
- Caesars
- PointsBet
- Any regional books in your state

**Why this matters:** Getting -3 instead of -3.5 on a spread, or -108 instead of -115 on a moneyline, compounds massively. A half-point on a spread moves win probability ~3%. Never take the worst number available.

### 5. Weather (outdoor games only)

Search: `[city] weather [game time] [date]`

Extract:
- Wind speed and direction (critical for totals)
- Temperature (affects outdoor football and baseball)
- Precipitation probability
- Dome or outdoor stadium?

**Wind thresholds for totals:**
```
< 8 mph:  negligible impact
8-15 mph: slight lean against total (especially blowing in)
15-20 mph: meaningful lean under on totals
> 20 mph: strong under lean, especially in baseball
Blowing in from CF: strongest suppression signal
```

### 6. Public betting percentages

Search: `[game] public betting percentage` or `[game] betting splits`

Extract:
- % of bets on each side
- % of money on each side (more important — follows sharp action)

**Interpretation:**
```
> 70% public on one side = potential fade spot (books don't move lines for public)
Money% > Bet% on one side = sharps loading that side
```

Sources:
- Action Network (best free tool)
- Covers.com
- OddsShark

### 7. Sport-specific context (hand off to sport skill)

After completing steps 1–6, hand the structured data to the appropriate sport-specific skill file for contextual interpretation. Do not skip this step.

---

## Data quality checklist

Before passing data to the edge detection skill, verify:

- [ ] All injury reports are from today (not yesterday's)
- [ ] Lines are current (check timestamp)
- [ ] Weather search includes game time, not just "today"
- [ ] Both teams' injury reports checked, not just the favorite
- [ ] Goalie/pitcher confirmation obtained (NHL/MLB only)

---

## Structured data output format

After pulling all data, structure it like this before passing to edge detection:

```
GAME: [Away] @ [Home]  |  [Time]  |  [Sport]

LINES (current best available):
  Spread: [Away] [line] / [Home] [line] | Book: [best book]
  Total: O/U [number] | Book: [best book]
  ML: [Away] [odds] / [Home] [odds] | Book: [best book]

OPENING vs CURRENT:
  Spread moved: [opening] → [current]
  Total moved: [opening] → [current]
  Signal: [public steam / sharp action / neutral]

INJURIES — [Away Team]:
  [Player] ([pos]): [status] — [note]

INJURIES — [Home Team]:
  [Player] ([pos]): [status] — [note]

WEATHER (if outdoor):
  Wind: [speed] mph [direction]
  Temp: [F/C]
  Precip: [%]

PUBLIC ACTION:
  Bets: [%] on [team] / [%] on [team]
  Money: [%] on [team] / [%] on [team]
  Signal: [follow / fade / neutral]
```

---

## Notes on data freshness

- Injury reports: check within 3 hours of game time for GTD designations
- Lines: always use real-time — never act on a line you saw hours ago without re-checking
- Weather: check day-of, not the day before
- Goalie/pitcher: confirm 1–2 hours before game time. If starter is scratched after you bet, evaluate the new situation immediately.
