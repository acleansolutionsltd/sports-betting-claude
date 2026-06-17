# SKILL: Performance Tracking

> **Purpose:** The feedback loop that tells you if your edge is real or imaginary. Without this, you're gambling. With it, you're running a business.

---

## Why tracking is non-negotiable

You cannot improve what you don't measure. The tracking system serves three purposes:

1. **Verify your edge is real** — ROI and CLV over 200+ bets is proof. Without it, all winning streaks and losing streaks are just noise.
2. **Identify where you're strongest and weakest** — maybe your NFL edge is real but your NBA model is broken. You can't know without data.
3. **Recalibrate bankroll sizing** — unit size adjusts monthly based on actual results.

---

## The bet log format

Every single bet gets logged in this format. Paste results back into the Claude Project after they're settled.

```
BET LOG ENTRY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Date:         [YYYY-MM-DD]
Sport:        [NFL / NBA / MLB / NHL / NCAAF / NCAAB]
Game:         [Away Team] @ [Home Team]
Market:       [Spread / ML / Total / Prop]
Pick:         [Team/Side + number]
Line taken:   [odds, e.g. -110]
Book:         [where you placed it]
Stake:        [$amount] = [X units]
Confidence:   [Tier A / B / C]
EV% at time:  [calculated edge]

Closing line: [what line closed at]
CLV:          [+/- half points or % depending on market]

Result:       [Win / Loss / Push / Void]
P&L:         [+$XX.XX or -$XX.XX]
Notes:       [anything unusual — injury news broke after, bad beat, etc.]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Monthly performance review

At the start of each month, run this analysis on the previous month's bets:

### Overall summary

```
Total bets:
Wins / Losses / Pushes:
Win rate (%):
Units won/lost:
ROI (%):       = (Net P&L) / (Total amount wagered) × 100
Closing line value (avg): = average CLV across all bets
```

### By sport

```
| Sport  | Bets | W-L | Win% | Units | ROI  | Avg CLV |
|--------|------|-----|------|-------|------|---------|
| NFL    |      |     |      |       |      |         |
| NBA    |      |     |      |       |      |         |
| MLB    |      |     |      |       |      |         |
| NHL    |      |     |      |       |      |         |
| NCAAF  |      |     |      |       |      |         |
| NCAAB  |      |     |      |       |      |         |
```

### By bet type

```
| Market | Bets | Win% | ROI  |
|--------|------|------|------|
| Spread |      |      |      |
| ML     |      |      |      |
| Total  |      |      |      |
| Props  |      |      |      |
```

### By confidence tier

```
| Tier | Bets | Win% | ROI  | Expected Win% |
|------|------|------|------|---------------|
| A    |      |      |      | ~58%+         |
| B    |      |      |      | ~55-58%       |
| C    |      |      |      | ~53-55%       |
```

### CLV analysis

Closing line value is the most important long-term metric:

```
Average CLV positive = you are finding real edges before the market closes
Average CLV negative = the market knows better than your model (serious problem)

Target: Positive CLV on 55%+ of bets
Green flag: Avg CLV > +0.5 points/0.5%
Yellow flag: Avg CLV between 0 and +0.5 
Red flag: Avg CLV negative — model needs reassessment
```

---

## Model calibration (quarterly)

Every quarter, run a calibration check on your probability estimates:

### Probability calibration

Group bets by your predicted win probability and check actual results:

```
Predicted P(win): 53-55% → Expected actual win%: ~54%
Predicted P(win): 55-58% → Expected actual win%: ~56.5%
Predicted P(win): 58-62% → Expected actual win%: ~60%

If actual win% is consistently below predicted P:
  Your model is overconfident → reduce edge threshold or increase uncertainty
  
If actual win% is consistently above predicted P:
  Your model is underconfident → you may be leaving money on the table
```

### Brier score (simplified)

```
For each bet:
  Brier contribution = (P_predicted - Actual_outcome)²
  Actual_outcome = 1 if won, 0 if lost

Average Brier score:
  < 0.22: Good calibration
  0.22-0.25: Acceptable
  > 0.25: Recalibrate model
```

---

## Red flag patterns to watch for

After every 50 bets, scan for these warning signs:

```
⚠️  Win rate below 50% over last 20 bets on -110 lines (expected >52.4%)
⚠️  Negative CLV trend — market consistently smarter than your timing
⚠️  One sport responsible for most losses — model may be broken for that sport
⚠️  High EV predictions but actual results diverging significantly
⚠️  Bankroll down 15%+ from high — approaching stop-loss territory
⚠️  Bet frequency increasing (are you forcing action when there's no edge?)
⚠️  Increasing unit sizes on losers (tilt behavior)
```

---

## Monthly bankroll update

After running the monthly review, update the project configuration:

```
Previous bankroll: $X
Monthly P&L: +/- $Y
New bankroll: $Z
New unit size: $Z × 0.02 = $W

Key insight this month: [what worked, what didn't]
Model adjustments: [any changes to edge thresholds, sport focus, etc.]
```

---

## Sharing back to Claude

Paste your bet log into the Project conversation with this prompt:

```
"Update my performance log with these results: [paste bet log entries]
Then give me my current ROI, units won this month, and your assessment 
of whether my edge looks real or like variance."
```

Claude will parse the log, update the running statistics, and give you an honest assessment.

---

## Sample running totals format

Keep a running total in the Project so Claude can reference it:

```
RUNNING TOTALS (as of [date])
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total bets all-time:     [N]
Overall W-L:             [W]-[L]-[P]
Total units wagered:     [X]
Net units:               [+/- Y]
Overall ROI:             [Z%]
Current bankroll:        $[amount]
Unit size:               $[amount]
Best sport (ROI):        [sport] at [%]
Worst sport (ROI):       [sport] at [%]
Avg CLV (all-time):      [+/- X pts]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
