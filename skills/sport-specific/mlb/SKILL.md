# SKILL: MLB Context

> **Purpose:** MLB betting is dominated by two things: pitching and weather. Get these right and you have a structural edge most public bettors ignore.

---

## The hierarchy of MLB betting factors

```
1. Starting pitcher matchup           (most important by far)
2. Weather conditions                 (Wrigley wind → massive)
3. Bullpen strength and availability  (often mispriced)
4. Park factors                       (Coors vs Petco are different sports)
5. Platoon advantages                 (LHP vs RHH lineups)
6. Lineup construction and injuries   (secondary)
```

---

## Starting pitcher analysis

### The must-confirms before any MLB bet

```
ALWAYS verify before betting:
1. Starting pitcher is confirmed (don't bet on rumored starters)
2. Check: has this starter been rescheduled or pushed back?
3. Pitch count limits (especially early season or after long layoff)

Search: "[Pitcher name] pitching tonight [date]"
        "[Team] starting pitcher [today]"
```

### Pitcher metrics to pull

```
ERA: rough baseline, highly volatile in small samples
FIP (Fielding Independent Pitching): better predictor than ERA
xFIP: even better, controls for HR rate regression
WHIP: control proxy
K%: strikeout rate (sustainable skill)
BB%: walk rate (sustainable skill)
HR/9: home run rate (regresses toward mean)

Use: FIP and xFIP over ERA for any analysis
Source: FanGraphs.com — search "[pitcher] stats [season]"
```

### Splits that matter

```
vs LHH vs RHH: most pitchers have a dominant side
  If pitcher is LHP and lineup is RHH-heavy: disadvantage for pitcher
  
Home vs Away splits: some pitchers dramatically better at home
  Search: "[pitcher] home away splits [season]"
  
Recent form (last 3–5 starts):
  Velocity trend (up or down from season avg)?
  Command metrics improving or declining?
  
Day vs Night: smaller but real for some pitchers
First time through order vs second time:
  Many relievers used strategically to limit exposure
```

### Park-adjusted ERA

Some parks inflate or deflate offense significantly. Always apply park factor:

```
Hitter-friendly parks (lean over on totals):
  Coors Field (COL): +15-20% run inflation — always lean over here
  Great American Ballpark (CIN): +8-10%
  Globe Life Field (TEX): +5-8%
  Fenway Park (BOS): +5-7%

Pitcher-friendly parks (lean under on totals):
  Oracle Park (SF): -8 to -12% run suppression
  Petco Park (SD): -8 to -10%
  T-Mobile Park (SEA): -6 to -8%
  Dodger Stadium (LAD): -5 to -7%

Source: Search "MLB park factors [season]" — Baseball Savant has current data
```

---

## Bullpen analysis

Bullpen state is frequently mispriced because it changes day-to-day and public doesn't track it.

### Check before every bet

```
Search: "[team] bullpen usage last 3 days"
        "[team] reliever availability [date]"

Key questions:
- Closer available? (pitched 2+ consecutive days = likely unavailable)
- Setup men taxed in recent blown saves or extra-inning games?
- Any bullpen arms just called up or sent down?
```

### Bullpen adjustment

```
Taxed bullpen (key arms pitched 2 of last 3 days):
  Adjust total up by 0.3 to 0.6 runs
  Slight lean on opponent's offense for back half of game

Fresh bullpen:
  Slight under lean (games managed to close)
  
Notably bad bullpen (ERA > 5.00 entering game):
  Adjust up 0.5 to 1.0 runs on total
```

---

## Weather analysis

### Wind (most critical factor)

```
Wind direction at MLB parks varies by field orientation — always check:

Blowing OUT (toward OF fences):
  > 10 mph: lean over +0.5 runs
  > 15 mph: lean over +1.0 to +1.5 runs
  > 20 mph: lean over +2.0 runs

Blowing IN (toward home plate from OF):
  > 10 mph: lean under -0.5 runs
  > 15 mph: lean under -1.0 to -1.5 runs
  > 20 mph: lean under -2.0 runs

Cross wind: minimal impact on totals

Wrigley Field special case:
  Wind out to CF or L at 15+ mph: total can be 2-3 runs higher
  Wind in at 15+ mph: games frequently go under by 2+ runs
  Always check: "Wrigley Field wind forecast [game time]"
```

### Temperature

```
< 50°F: -0.3 to -0.5 runs on total (ball doesn't carry as far)
> 90°F: +0.2 to +0.4 runs (ball carries slightly further, fatigue factor)
```

---

## Platoon advantages

```
LHP vs heavy RHH lineup: pitcher disadvantage
RHP vs heavy LHH lineup: pitcher disadvantage

Strong platoon lineup vs LHP:
  Team with RHH-heavy lineup facing LHP: offensive lean

Check: "[team] lineup vs LHP/RHP splits [season]"
       "wRC+ vs LHP/RHP [team] [season]"
```

---

## MLB betting types

```
Runline (-1.5 / +1.5):
  Best for: Strong pitching matchups where ace should dominate
  Avoid: High-total games, Coors Field

Moneyline:
  Best for: Heavy underdog dogs with good pitching (price compression)
  Fade: -200+ favorites — poor value even at high win probability

Totals:
  Best bet in MLB — weather, park factors, pitching create genuine edges
  Most consistent edge source

First 5 innings (F5):
  Bet only the starting pitchers' contributions
  Eliminates bullpen variance
  Best when: Ace vs weak starter where run support is likely early
  
First inning:
  High-variance prop, but useful when: power lineup vs RHP first time through
```

---

## Red flags (lean to pass)

```
❌ Opener or bulk pitching game announced (eliminates starter edge)
❌ Game 3 of a series in late season with nothing on the line
❌ Starter has thrown 85+ pitches in each of last 2 starts (may be on limit)
❌ Coors Field total bet without confirming current wind forecast
❌ Bullpen game for both teams (total becomes coin flip)
❌ Extra-inning game yesterday — both bullpens taxed
```

---

## Key sources

```
FanGraphs: pitcher FIP, xFIP, splits — fangraphs.com
Baseball Savant: statcast data, park factors — baseballsavant.mlb.com
Rotoworld: injury and lineup news
Beat reporters: most reliable for day-of lineup changes
Weather Underground: ballpark-specific hourly forecasts

Searches:
"[pitcher] FanGraphs [season] stats"
"[team] lineup today [date]"
"[city] hourly weather forecast [date]"
"MLB park factors [current season]"
"[team] bullpen ERA [last 7 days]"
```
