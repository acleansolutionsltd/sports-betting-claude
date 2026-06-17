# Kelly Criterion Explained

The single most important concept in this system. Most bettors lose not because they pick wrong, but because they bet too much.

---

## The problem Kelly solves

Imagine you have a 55% edge on every coin flip — you win 55% of the time, lose 45%. Should you bet everything on each flip?

No. A losing streak (which will happen) would wipe you out before your edge plays out. But if you bet too little, your bankroll grows too slowly. Kelly finds the mathematically optimal middle ground.

---

## The formula

```
Kelly % = (b × p − q) / b

Where:
  b = net odds (decimal odds − 1)
  p = your probability of winning
  q = your probability of losing (1 − p)

Example:
  Bet: Team A -3.5 at -110
  Your P(win) = 57% = 0.57
  
  Decimal odds from -110: (100/110) + 1 = 1.909
  b = 1.909 − 1 = 0.909
  p = 0.57
  q = 0.43
  
  Kelly = (0.909 × 0.57 − 0.43) / 0.909
        = (0.518 − 0.43) / 0.909
        = 0.088 / 0.909
        = 9.7% of bankroll
```

This says: bet 9.7% of your bankroll on this play.

---

## Why we use fractional Kelly (0.25×)

Full Kelly is mathematically optimal only if:
- Your probability estimate is exactly correct
- You have infinite time horizon
- You can bet fractional amounts

In the real world, your probability estimate is always uncertain. If your model says 57% but the true probability is 54%, full Kelly will over-bet and cause larger drawdowns.

**Fractional Kelly multiplies the result by a fraction to account for model uncertainty:**

```
Quarter Kelly (0.25×):
  Full Kelly was 9.7%
  Quarter Kelly = 9.7% × 0.25 = 2.4% of bankroll

At $2,000 bankroll:
  Full Kelly bet: $194
  Quarter Kelly bet: $48 ≈ 1.2 units
```

Quarter Kelly is the standard. Some bettors use half Kelly (0.5×) when very confident; never go above half Kelly.

---

## Why not just flat-bet?

Many bettors use a flat unit system (same amount every bet). Kelly beats flat betting because:

- High-edge bets get more money (more edge captured)
- Low-edge bets get less money (variance controlled)
- Bankroll automatically adjusts — you bet more when winning, less when losing

However, the difference between Kelly and flat betting narrows significantly with quarter Kelly. The more important benefit is discipline: Kelly removes the temptation to "go big" on a hunch.

---

## The bankroll growth math

With a 55% win rate at -110 odds (consistent with a solid model):

```
ROI per bet ≈ +4.7%
Quarter Kelly stake ≈ 2-3% of bankroll per bet
Monthly growth (20 bets, 4-6 qualifying per week):
  Conservative: +8 to +12%
  Good month: +15 to +25%
  Great month: +25 to +40%
```

"20% monthly" is achievable in good months. It is not guaranteed every month. Variance is real.

---

## What happens when you ignore Kelly

| Behavior | Result |
|---|---|
| Bet too much (full Kelly or more) | Huge variance, 40-60% drawdowns even with positive EV model |
| Chase losses with larger bets | Systematic bankroll destruction |
| Flat bet regardless of edge | Leave money on table on high-edge plays; over-bet low-edge plays |
| Quarter Kelly, disciplined | Smooth bankroll growth with manageable drawdowns |

---

## Quick sizing reference

At $2,000 bankroll ($40/unit):

| Edge | Decimal Odds | Full Kelly | Quarter Kelly | Units |
|------|-------------|------------|---------------|-------|
| 2%   | 1.909 (-110) | 2.2%      | 0.55% = $11  | 0.3   |
| 3%   | 1.909 (-110) | 3.3%      | 0.83% = $17  | 0.4   |
| 5%   | 1.909 (-110) | 5.5%      | 1.4% = $28   | 0.7   |
| 8%   | 1.909 (-110) | 8.8%      | 2.2% = $44   | 1.1   |
| 4%   | 2.400 (+140) | 6.3%      | 1.6% = $32   | 0.8   |
| 6%   | 2.400 (+140) | 9.4%      | 2.4% = $48   | 1.2   |

In practice, the Tier system (A/B/C) in the bankroll skill file caps stakes at sensible levels without needing to calculate Kelly for every single bet. Use Kelly as a sanity check and the Tier caps as your operating system.
