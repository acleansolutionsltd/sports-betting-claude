# SKILL: Edge Detection

> **Purpose:** Convert raw data into a calculated edge. This is the mathematical core of the system. If there is no edge, there is no bet.

---

## Core principle

The market (sportsbook) sets an implied probability for every outcome after taking their cut (the vig). Your job is to estimate the *true* probability better than the market does, then bet when your estimate exceeds theirs by enough to overcome variance.

```
Edge = Your P(win) − Market P(win) [after vig removal]
Bet only when: Edge ≥ [EDGE THRESHOLD from Project settings]
```

---

## Step 1 — Remove the vig

Sportsbooks build profit margin into every line. You must strip it out before comparing probabilities.

### Converting American odds to true implied probability

**For negative odds (favorites):**
```
Implied P = |odds| / (|odds| + 100)
Example: -150 → 150 / 250 = 0.600 = 60.0%
```

**For positive odds (underdogs):**
```
Implied P = 100 / (odds + 100)
Example: +130 → 100 / 230 = 0.435 = 43.5%
```

### Removing the vig (two-outcome markets)

```
Total implied = P(home) + P(away)   [will be > 1.0, that's the vig]
True P(home) = P(home) / Total implied
True P(away) = P(away) / Total implied

Example:
  Home: -110 → implied 52.38%
  Away: -110 → implied 52.38%
  Total: 104.76% (vig = 4.76%)
  True P(home) = 52.38 / 104.76 = 50.0%
  True P(away) = 52.38 / 104.76 = 50.0%
```

---

## Step 2 — Estimate your true probability

This is where skill separates from luck. Your model probability comes from combining:

### Factor weighting framework

```
Base probability (from historical matchup data):     30%
Recent form (last 10 games / 3 games for NFL):       20%
Injury adjustments:                                  25%
Situational factors (home/away, rest, travel):       15%
Market signal (sharp money, CLV trend):              10%
```

### Injury adjustments

Apply these point adjustments to the market's vig-removed probability:

**NFL:**
```
Starting QB out:          -15 to -20 points (situational)
Starting QB limited:      -5 to -8 points
Key OL starter out:       -3 to -5 points (especially vs top pass rush)
WR1 out:                  -2 to -4 points
CB1 out:                  +2 to +4 for opposing offense
```

**NBA:**
```
Star player out (30+ min): -6 to -10 points on spread
Two starters out:          -10 to -15 points
Key bench wing out:        -1 to -2 points
```

**MLB:**
```
Ace → replacement starter: -1.5 to -2.5 run line shift
Closer out:                -0.2 to -0.4 runs
Key lineup spot out:       context-dependent (vs LHP/RHP matters)
```

**NHL:**
```
Starting goalie scratched: -0.3 to -0.6 on puck line
Top center out:            -0.2 to -0.3
```

### Situational adjustments

```
Home field advantage:
  NFL: +2.5 to +3 points (3 PPG historically)
  NBA: +3 to +4 points
  MLB: +0.2 to +0.3 runs
  NHL: +0.15 puck line

Rest advantage (days of rest difference):
  0 days vs 2+ days: +1.5 to +2 points
  Back-to-back (NBA): -3 to -5 points for B2B team

Travel fatigue:
  Cross-country west-to-east for 1pm ET game: -1 to -2 points
  3+ time zone shift: -1.5 to -2.5 points

Divisional games:
  Reduce spread by 20-25% (familiarity reduces edge for favorites)

Weather (totals, outdoor only):
  Wind > 20mph blowing in: -1.5 to -2.5 on total
  Precipitation: -0.5 to -1 on total
```

---

## Step 3 — Calculate EV

```
EV% = (Your P_win × Profit per unit) − (Your P_loss × Stake per unit)

Example:
  Bet: Team A -3.5 at -110
  Your P(win): 57%  |  Market P(win): 52.4%  |  Edge: 4.6%
  
  Decimal odds: 100/110 + 1 = 1.909
  Profit if win: $90.91 on $100 stake
  
  EV = (0.57 × $90.91) − (0.43 × $100)
     = $51.82 − $43.00
     = +$8.82 per $100 staked
     = +8.82% EV  ✅ exceeds 2% threshold
```

---

## Step 4 — Closing line value (CLV) as the real signal

CLV is the most important long-term metric in sports betting. If you consistently beat the closing line, you are finding real edge.

```
CLV = Closing odds − Your odds taken

Example:
  You bet -3.5 (-110)
  Game closes at -4.5 (-110)
  CLV = +1 point (you got the better number)
  
  You bet +130 on an underdog
  Game closes at +115
  CLV = negative (you got a worse number than the market settled at)
```

**Target:** Positive CLV on 55%+ of your bets over 200+ sample size = model is working.

Log CLV for every bet in your performance tracker.

---

## Step 5 — Market confidence tiers

Rate every candidate bet before sizing:

```
TIER A — HIGH CONFIDENCE
  Required: Edge ≥ 4% + sharp money aligned + sport context clean + CLV positive recent trend
  Units: 4–5

TIER B — MEDIUM CONFIDENCE
  Required: Edge ≥ 2.5% + no sharp-against signal + context clean
  Units: 2–3

TIER C — LOW CONFIDENCE / SPECULATIVE
  Required: Edge ≥ 2% + one of: sharp aligned or strong context signal
  Units: 1

PASS
  Edge < 2% OR anti-bias check flags a red flag OR data is incomplete/stale
```

---

## Step 6 — Market types and their edge characteristics

### Spreads
- Most efficient market (hardest to beat)
- Best edge source: line movement + injury adjustments the public hasn't priced yet
- Avoid: Betting on stale lines when news broke in the last few hours

### Totals
- More inefficient than spreads (easier to find edge)
- Best edge source: weather, pace mismatches, key pitching/goalie props
- Watch for: Public love for overs (public bias inflates over odds)

### Moneylines
- High variance, but can find value on dogs
- Best edge source: injury to opposing star not yet priced
- Avoid: Heavy favorites at -200+ (very little value even when right)

### Player props
- Highest inefficiency (books offer hundreds, can't set them all perfectly)
- Best edge source: minutes projections vs injury news, opponent defensive matchup
- Caution: Sharp books limit winners quickly — protect access

---

## Quick reference: when to pass, always

| Situation | Action |
|-----------|--------|
| Edge < 2% | Pass |
| Data is from yesterday or older | Refresh, then decide |
| Starter not confirmed | Wait until confirmed or pass |
| Anti-bias check flagged | Rerun analysis cold — if same result, proceed |
| Already at MAX UNITS for the day | Pass even on good edges |
| Bankroll at stop-loss level | Pass — pause and reassess first |
| Sharp money against your model | Reduce confidence tier by one; re-examine |
