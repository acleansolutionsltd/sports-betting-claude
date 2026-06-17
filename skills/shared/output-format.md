# Output Format

> Every bet recommendation uses this exact format. Consistency makes it fast to read, log, and act on.

---

## Daily output template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅  [DATE]
🏦  BANKROLL: $[amount] | UNIT: $[unit size]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[TIER A BETS FIRST, THEN TIER B, THEN TIER C]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔵 BET #[N] — [HIGH / MEDIUM / LOW] CONFIDENCE ([X] units)

Sport:      [NFL / NBA / MLB / NHL / NCAAF / NCAAB]
Market:     [Spread / Moneyline / Total / Prop]
Pick:       [Team or side + number]
Book:       [Best available book for this line]
Line:       [odds, e.g. -110 or +145]
Stake:      $[dollar amount] ([X] units)
EV%:        +[X.X]%

Reasoning:
[2-4 sentences max. State the specific edge: what data point creates the value,
what the market is missing, what the model shows vs what the line implies.
No narrative fluff — just the signal.]

Closing target: [What line you expect it to close at — used for CLV tracking]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Repeat block for each bet]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⛔ PASS: [N] other games reviewed — no qualifying edge.
[One-line note on the closest near-miss if useful, e.g. "Lakers came close at +1.8% EV but below threshold."]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 LOG ENTRIES (copy-paste after results):

[Pre-formatted bet log entries for each recommended bet, ready to paste back]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Confidence tier indicators

```
🔵 Blue = Tier A (High) — 4-5 units — EV ≥ 4%, all signals aligned
🟡 Yellow = Tier B (Medium) — 2-3 units — EV ≥ 2.5%, clean context
⚪ White = Tier C (Low) — 1 unit — EV ≥ 2%, one strong signal
⛔ Red = Pass — insufficient edge
```

---

## "No bets today" output

When no qualifying edges are found, don't force recommendations:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅  [DATE]
🏦  BANKROLL: $[amount] | UNIT: $[unit size]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⛔ NO QUALIFYING BETS TODAY

[N] games reviewed. Strongest candidate was [game] at +[X]% EV — below the
[threshold]% minimum. Passing is the right move.

Bankroll protected. Check back tomorrow.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Single game analysis output

When asked "should I bet [specific game]?":

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANALYSIS: [Away] @ [Home] | [Market]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CURRENT LINE:     [line + odds at best book]
OPENING LINE:     [opening]
MOVEMENT:         [direction + what it signals]

MY P(WIN):        [X]%
MARKET P(WIN):    [X]% (vig-removed)
EDGE:             [+/- X]%

INJURY IMPACT:    [key notes or "none significant"]
SITUATIONAL:      [key notes or "clean"]
WEATHER:          [if outdoor, or "N/A"]
SHARP ACTION:     [signal or "neutral"]
BIAS CHECK:       [passed / flagged — reason]

VERDICT:          [BET — Tier X, Y units] or [PASS — reason]
REASONING:        [2-3 sentences]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Performance review output

When asked for a performance update:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERFORMANCE REVIEW — [Period]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OVERALL
  Record:       [W]-[L]-[P]
  Units:        [+/- X]
  ROI:          [X]%
  Avg CLV:      [+/- X pts]

BY SPORT       Record    ROI
  NFL:         [W-L]     [%]
  NBA:         [W-L]     [%]
  MLB:         [W-L]     [%]
  NHL:         [W-L]     [%]

ASSESSMENT
  Edge status: [Real / Variance / Concern — with brief explanation]
  
  Strongest area:   [sport/market at best ROI]
  Weakest area:     [sport/market to examine]
  
  Recommendation:   [continue / adjust / pause — with reason]

UPDATED UNIT SIZE: $[new unit at 2% of current bankroll]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
