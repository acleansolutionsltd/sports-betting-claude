# SKILL: Premier League (EPL) Context

> **Purpose:** Sport-specific knowledge for English Premier League football — three-way markets, draw pricing, fixture congestion, and the factors the base model (built for two-outcome US sports) doesn't capture.

---

## Why football needs its own rules

The core edge-detection skill assumes two outcomes. Football match-result markets have **three** (home / draw / away), draws land ~25% of the time, and goals are low-count events (~2.8 per game). Every calculation below adjusts for that.

---

## Step 1 — Three-way vig removal (1X2)

Convert all three prices to implied probability, then normalise across all three:

```
Implied P = 1 / decimal odds     (or use the American-odds formulas in edge-detection)
Total implied = P(home) + P(draw) + P(away)     [typically 1.04–1.08]
True P(x) = P(x) / Total implied

Example: Sunderland +199 / Draw +246 / Brighton +130
  Implied: 33.4% / 28.9% / 43.5%  → total 105.8%
  True:    31.6% / 27.3% / 41.1%
```

**Never** remove vig from only two of the three outcomes — that overstates both sides.

Odds format conversions (UK books quote fractional):
```
Fractional a/b → decimal = (a / b) + 1        e.g. 13/8 → 2.625
Decimal → American: ≥ 2.00 → (dec − 1) × 100;  < 2.00 → −100 / (dec − 1)
```

---

## Step 2 — Estimate true probability

Weight inputs in this order:

```
Expected goals (xG / xGA, last 10 league games, venue-split):   35%
Market consensus from sharp books (Pinnacle, exchanges):        25%
Team news (lineups, injuries, rotation):                        20%
Situational (congestion, travel, motivation):                   15%
Head-to-head / venue history:                                    5%
```

- Use a Poisson model from each side's attacking and defensive xG rates to derive home/draw/away and total-goals probabilities.
- Treat prediction markets (Kalshi, Polymarket) and exchange prices (Betfair) as market consensus, not as an independent model.
- A single third-party model (e.g. Dimers, Covers) is one input. If it's your only source of edge, drop one confidence tier.

### Home advantage
```
League-average home edge: ~0.25–0.35 goals (≈ +5 to +8 pts on home win %)
Newly promoted side at home: no extra boost — markets already overrate early-season home form
```

### Draw pricing
- Draws are systematically underbet by the public. Fair draw probability usually sits at 24–30%.
- Draw likelihood rises when: both sides are evenly matched (fair win probabilities within 10 pts), the total is ≤ 2.25, or both managers are defensively set up.
- Draw likelihood falls when: one side's fair win probability > 55%, or a high total (≥ 3.0).

---

## Step 3 — Team news (highest-impact factor)

Lineups are confirmed **60 minutes before kick-off**. Pre-match injury news comes from manager press conferences (Thursday/Friday for weekend games).

**Impact adjustments to win probability:**
```
First-choice goalkeeper out:            −3 to −5 pts
Top scorer / primary creator out:       −3 to −6 pts
Two+ first-choice centre-backs out:     −4 to −7 pts
Key defensive midfielder out:           −2 to −4 pts
Squad-depth player out:                  ~0 (do not adjust)
```

Mark a key player as "doubtful" in the model at 50% availability, not 0% or 100%.

---

## Step 4 — Situational spots

### Fixture congestion
- Team played European football (UCL/UEL/UECL) on Wednesday/Thursday → −2 to −4 pts on win probability for Saturday early kick-offs; −1 to −2 for Sunday games.
- Thursday Europa/Conference League → Sunday game: smaller but still measurable fatigue.
- Rotation risk: check the manager's history of rotating after European nights.

### International breaks
- First weekend after a break: elevated injury news and reduced training time for international players.
- Players returning from South America / long-haul trips on Thursday: lean against them starting or playing 90 minutes.
- Treat form from before the break with slightly less weight.

### Managerial change
- New manager bounce: first 3–5 games after a sacking, +3 to +5 pts — but the market usually prices this by game 2.
- Manager under pressure (sacking rumours): no adjustment unless backed by xG trend.

### Motivation (late season only)
- Title race, European places, relegation: genuine motivation gaps from April onward.
- Mid-table with nothing to play for in the final 4–5 games: −2 to −4 pts.

### Derbies
- Local derbies compress outcomes: shade the favourite down 3–5 pts and the draw up 2–3 pts.

---

## Step 5 — Market selection

| Market | Edge characteristics |
|---|---|
| 1X2 (match result) | Most liquid, most efficient. Edge mostly from late team news |
| Asian handicap | Removes the draw; lower margins (2–3%). Prefer over 1X2 for favourites |
| Draw no bet | Asian handicap 0. Good for evenly matched sides where you like one team |
| Totals (O/U 2.5) | Public overbets overs. Edge from xG, weather, lineups |
| Both teams to score (BTTS) | Edge when one side's defence is clearly leaky AND the other creates chances |
| Corners / cards | Soft markets but low limits; referee card averages matter |
| Player props (shots, SOT) | Highest inefficiency; depends on confirmed lineups |

**Asian handicap quick reference:**
```
−0.5 = team must win (same as 1X2 win)
 0.0 = draw no bet (stake refunded on draw)
−0.25 = half stake on 0.0, half on −0.5
+0.5 = team wins or draws (double chance)
```

### BTTS / totals from xG
```
P(team scores ≥ 1) = 1 − e^(−λ)     where λ = that team's expected goals in this match
P(BTTS) ≈ P(home scores) × P(away scores)
P(Over 2.5) = 1 − P(0, 1 or 2 total goals) using Poisson with λ_total = λ_home + λ_away
```

---

## Step 6 — Line movement and sharp signals

- Asian markets (Pinnacle, Asian books) move first. UK recreational books follow.
- Movement of 10+ cents on Pinnacle within 24 hours of kick-off = meaningful sharp action.
- Price drifts after the lineup announcement = market reacting to team news. Don't chase.
- Prices quoted on preview sites are often 24–48 hours stale — always re-check.

---

## EPL-specific red flags (lean to pass)

```
❌ Lineup not confirmed and a key player is doubtful — wait for the team sheet
❌ Edge only exists at one outlier book price that may be stale or unavailable
❌ Only one external model supports the edge and no sharp-book data available
❌ Backing a "big six" club purely on name (name/brand bias)
❌ Head-to-head trend from fewer than 20 meetings
❌ Team played in Europe midweek and you haven't checked rotation
❌ Betting 1X2 favourite at shorter than 1.40 (−250) — use Asian handicap instead
```

---

## Sizing notes

- The bankroll skill applies unchanged.
- Three-way markets have higher variance than two-way spreads at the same EV. For any 1X2 bet on a side priced at +200 or longer, cap at Tier B sizing (3 units) regardless of edge.
- Kelly uses the same formula — be sure to use the three-way vig-removed market probability for the edge.

---

## Sources to search for EPL context

```
"Premier League fixtures [date]"
"[team] team news press conference [date]"
"[team] predicted lineup [opponent]"
"[home] vs [away] odds" / oddschecker [home]-v-[away]
"[team] xG last 10 games" (FBref, Understat, FotMob)
"Premier League injury table" (premierinjuries.com, fantasyfootballscout.co.uk)
"[home] vs [away] Asian handicap"
"[referee name] cards per game [season]"
```
