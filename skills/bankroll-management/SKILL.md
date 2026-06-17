# SKILL: Bankroll Management

> **Purpose:** Tell Claude exactly how much to bet on every bet. The math that prevents going broke even when the model is right long-term.

---

## The single most important rule

**You can have a winning model and still go broke if you bet too much.**

Variance is real. A 58% win-rate model will lose 5, 6, 7 in a row — this is mathematically expected, not a sign the system is broken. Proper sizing ensures you survive the losing streaks that will inevitably come.

---

## The unit system

Everything is denominated in units. A unit = 2% of your current bankroll.

```
Starting bankroll: $2,000
Unit size: $40

Month 1 end bankroll: $2,400 (after +20%)
New unit size: $48  ← recalculate monthly
```

**Why 2%?** At 2% per unit and a maximum of 5 units per bet, your largest single bet is 10% of bankroll. Even a 10-bet losing streak (extremely rare with a positive EV model) costs 50–60% — painful but survivable. At 5% units, the same streak wipes you out.

---

## Kelly criterion

Kelly gives the mathematically optimal fraction of bankroll to bet to maximize long-term growth.

### Full Kelly formula

```
Kelly % = (Edge × (1 + Win odds)) / Win odds

Where:
  Edge = your P(win) − market P(win) [after vig]
  Win odds = decimal odds − 1

Example:
  Your P(win): 57%  |  Market P(win): 52.4%  |  Edge: 4.6% = 0.046
  Decimal odds: 1.909 (from -110)
  Win odds: 0.909
  
  Kelly % = (0.046 × 1.909) / 0.909 = 0.0879 / 0.909 = 9.67%
```

### Fractional Kelly (what you actually use)

Full Kelly is mathematically optimal only if your probability estimate is perfectly accurate — which it never is. Use **quarter-Kelly (0.25×)** as the default:

```
Fractional Kelly stake = Full Kelly × 0.25
  
Example continued:
  Full Kelly: 9.67% of bankroll
  Quarter Kelly: 9.67% × 0.25 = 2.42% of bankroll
  At $2,000 bankroll: $48.40 stake ≈ 1.2 units
```

### Converting Kelly to units

```
Kelly stake ($) / Unit size ($) = Units to bet
Round to nearest 0.5 unit
Cap at MAX UNITS PER BET from project settings (default: 5)
```

---

## Bet sizing by confidence tier

Combine Kelly with confidence tier for final sizing:

```
TIER A (High confidence):
  Kelly result: any    → bet Kelly amount, max 5 units
  Typical range: 3–5 units

TIER B (Medium confidence):
  Kelly result: any    → bet Kelly amount, max 3 units
  Typical range: 2–3 units

TIER C (Low confidence):
  Kelly result: any    → bet Kelly amount, max 1 unit
  Flat: 1 unit

PASS:                  → 0 units
```

---

## Daily exposure limits

```
Maximum units per day:       10 units total (from project settings)
Maximum units per bet:       5 units
Maximum units per sport:     6 units (don't over-concentrate)
Maximum same-team exposure:  8 units total in one day (spread + ML + prop)
```

If you've already placed 10 units of bets today and find another edge, **log it for tomorrow** rather than exceeding the daily cap.

---

## Bankroll growth recalibration

Recalculate unit size on the first of each month:

```
New unit size = Current bankroll × 0.02

If bankroll has grown:
  Example: $2,000 → $2,450 after month 1
  New unit: $2,450 × 0.02 = $49

If bankroll has declined:
  Example: $2,000 → $1,750
  New unit: $1,750 × 0.02 = $35
  (This automatically reduces exposure during losing periods)
```

**Never manually inflate unit size to chase losses.** The 2% rule already adjusts for you.

---

## Stop-loss rules

### Daily stop-loss
```
If you lose 5+ units in a single day:
  → Stop betting for the rest of the day
  → Review what happened (bad luck, bad model, bad data, tilt?)
  → Resume tomorrow with a clear head
```

### Drawdown stop-loss
```
If bankroll drops 20% from its highest point:
  → Pause all betting for 48 hours
  → Review the last 30 bets in your log
  → Identify: is this variance or model failure?
  → Assess: has something changed that your model isn't capturing?
  → Resume only when you can clearly articulate why the edge still exists
```

### Identifying model failure vs variance

This is the hardest judgment call. Use these signals:

| Variance (keep going) | Model failure (reassess) |
|---|---|
| Win% is close to expected (±5%) | Win% is significantly below model predictions |
| CLV is positive (you're beating the close) | CLV is negative (market consistently beats you) |
| Losing streaks cluster in one sport | Losses spread across all sports |
| Edge% looks right in retrospect | Edge% was calculated incorrectly |
| Injury variance, bad luck spots | You keep missing significant injuries |

---

## Parlay and same-game parlay rules

```
Parlays: Maximum 1 unit on any parlay, regardless of confidence
         Only parlay legs that are uncorrelated (different sports, different games)
         Never build a parlay to "juice up" a low-confidence play

Same-game parlays: Treat as speculative entertainment, not +EV plays
                   Maximum 0.5 units
                   Never let SGP count toward daily unit total (track separately)

Teasers: Only use 6-point NFL teasers through key numbers (3, 7, 10)
         Requires both legs to have genuine independent value
```

---

## Quick reference: sizing table

At $2,000 bankroll ($40/unit):

| Confidence | Units | Stake |
|---|---|---|
| High (Tier A) | 4–5 | $160–$200 |
| Medium (Tier B) | 2–3 | $80–$120 |
| Low (Tier C) | 1 | $40 |
| Parlay/SGP | 0.5–1 | $20–$40 |
| Pass | 0 | $0 |
