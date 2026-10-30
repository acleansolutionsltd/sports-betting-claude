# SKILL: Lineup Confirmation Check

> **Purpose:** Re-run every pending bet once official lineups or inactives are released, quantify what the confirmed personnel changes do to the edge, and output a final CONFIRM / RESIZE / CANCEL / NEW decision before the bet is placed.

---

## When to use this skill

Use it when the user asks any of:
- "Lineups are out — re-check my bets"
- "Run the lineup check for [game]"
- "Is [bet] still good now the team is confirmed?"

Also use it on any pre-match recommendation flagged `PENDING LINEUP` in the daily output.

**Rule:** Any bet whose edge depends on a player who is not yet confirmed is a **provisional** bet. Do not treat it as final until this check has run.

---

## Lineup release windows

| Sport | What is released | When | Re-check at |
|---|---|---|---|
| EPL / football | Starting XI + bench | 60 min before kick-off | T−55 min |
| NFL | Inactives list | 90 min before kick-off | T−85 min |
| NFL | Final injury report (Out / Doubtful / Questionable) | Friday afternoon (Sun games), Wed/Sat for TNF/MNF | Friday evening |
| NBA | Starting lineups | ~30 min before tip (status updates through the day) | T−25 min |
| MLB | Batting lineups (starting pitcher known earlier) | 2–4 hours before first pitch | Once posted |
| NHL | Starting goalie confirmation | Morning skate / ~60 min before puck drop | T−60 min |

Search queries:
```
"[home] vs [away] confirmed lineup"          (football)
"[home] [away] starting XI"                  (football)
"[team] inactives week [N]"                  (NFL)
"[team] starting lineup tonight"             (NBA)
"[team] lineup today [date]"                 (MLB)
"[team] starting goalie tonight"             (NHL)
```

Sources (in order): official club / team accounts on X → league app → beat reporters → Rotowire / FotMob / Fantasy Football Scout.

---

## Step 1 — Diff the confirmed lineup against your assumptions

For every pending bet, list what the original analysis **assumed** and what is now **confirmed**:

```
GAME: [Away] @ [Home]  |  Bet: [pick + line]

ASSUMED (at time of analysis):     CONFIRMED (now):
  [Player A] starts                  [Player A] — STARTS / BENCH / OUT
  [Player B] out                     [Player B] — STARTS / BENCH / OUT
  [Formation / QB / goalie]          [Formation / QB / goalie]

SURPRISES (not in original analysis):
  [Player C] — [unexpected start / omission]
```

Only players whose status **changed** versus the assumption move the number. A confirmed absence you already priced in is not new information.

---

## Step 2 — Re-price the probability

Apply the sport skill's player-impact table to each change. Reference values:

**Football (EPL):** win-probability points
```
First-choice GK out:                   −3 to −5
Top scorer / main creator out:         −3 to −6
Two+ first-choice CBs out:             −4 to −7
Key defensive midfielder out:          −2 to −4
Heavy rotation (5+ changes from last league XI): −4 to −8
Doubtful player actually starts:       reverse the 50% discount applied earlier
```

**NFL:** points on the spread (≈ 3% win probability per point near pick'em)
```
Starting QB inactive:                  −5 to −20 (see NFL skill backup tiers)
2+ OL starters inactive:               −3 to −5
WR1 / RB1 inactive:                    −1 to −3
Top pass rusher inactive:              +1 to +2 for opposing offense
CB1 inactive:                          +2 to +4 for opposing offense
```

**Totals and props:** a missing primary scorer or QB also moves the total. Re-price totals with the same personnel changes, not just the side.

Then:
```
New model P(win) = Original model P(win) + Σ(adjustments for changed players)
New market P(win) = vig-removed CURRENT price (re-pull it — prices move on lineup news)
New edge = New model P − New market P
```

**Important:** Markets react to lineups within minutes. If the price has already moved to reflect the change, the edge may be gone even if your model moved the same way. Always compare against the post-lineup price.

---

## Step 3 — Decide

```
New edge ≥ original tier threshold          → CONFIRM (bet as sized)
New edge still ≥ 2% but tier drops          → RESIZE (re-run Kelly at new edge, new tier cap)
New edge < 2%                               → CANCEL
Lineup created an edge on a game you passed → NEW (full 6-step analysis, but cap at Tier B —
                                               you have minutes, not hours, to verify)
Lineup still not posted at T−15             → CANCEL any bet that depends on it
```

Bets already placed before the lineup check cannot be cancelled. Record them as "pre-lineup" in the log so CLV analysis can separate them out. Over 50+ bets, compare ROI of pre-lineup vs post-lineup bets to learn whether early prices or lineup certainty is worth more for your model.

---

## Step 4 — Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧾 LINEUP CHECK — [Game] | [time checked]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Original bet:     [pick] [line] — [X] units, edge +[X]%
Lineup changes:   [player — status — adjustment], ...
Price now:        [line] (was [line])
Model P now:      [X]%   |   Market P now: [X]%
New edge:         [+/− X]%

DECISION:         ✅ CONFIRM / 🔁 RESIZE to [X] units / ❌ CANCEL / 🆕 NEW
Reason:           [one sentence]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Red flags (lean to cancel)

```
❌ The lineup confirms the change you bet on, but the price already moved past your number
❌ A key player is named in the XI / active but was limited all week (may be a decoy or partial game)
❌ Unexpected rotation with no explanation — check for late injury news before re-pricing
❌ You are re-sizing UP on a bet only because a lineup "looks good" with no edge recalculation
❌ Lineup source is a leak or rumour, not an official team release
```
