# EV calculator - worked examples

Every number below was produced by the functions in `betting_model/ev/`. Prices are illustrative inputs, not quotes.

## 1. Converting odds

| input | format | decimal | implied probability |
|---|---|---|---|
| 10/1 | fractional | 11.0000 | 0.0909 |
| 4/6 | fractional | 1.6667 | 0.6000 |
| evens | fractional | 2.0000 | 0.5000 |
| +150 | american | 2.5000 | 0.4000 |
| -200 | american | 1.5000 | 0.6667 |
| 1.50 | decimal | 1.5000 | 0.6667 |

```python
from betting_model.ev import odds
odds.to_decimal('10/1')   # 11.0
odds.to_decimal('-200')   # 1.5
```

## 2. Bookmaker margin and removing it

A 1X2 market priced 1.91 / 3.6 / 4.2 has implied probabilities 0.5236, 0.2778, 0.2381, which sum to 1.0394. The margin (overround) is 3.94%.

| method | home | draw | away |
|---|---|---|---|
| multiplicative | 0.5037 | 0.2672 | 0.2291 |
| power | 0.5105 | 0.2643 | 0.2252 |
| shin | 0.5087 | 0.2653 | 0.2260 |

The power and Shin methods take more margin off the longer prices than the simple proportional method does, which matches how bookmakers load margin. The model uses the power method by default.

Two-way example, over/under priced 1.8 / 2.05: margin 4.34%, fair probabilities 0.5346 / 0.4654.

## 3. Expected value per £1

`EV = p x (decimal - 1) - (1 - p)`

| model probability | price | price-implied | EV per £1 | verdict |
|---|---|---|---|---|
| 0.651 | 1.50 | 0.667 | -0.0235 | negative |
| 0.700 | 1.50 | 0.667 | +0.0500 | positive |
| 0.700 | 1.40 | 0.714 | -0.0200 | negative |
| 0.650 | 1.60 | 0.625 | +0.0400 | positive |

The first row is the tracker example from the build plan (BTTS at 1.50 with a 65.1% model probability): it clears the 65% floor but is still a losing bet on expectation, because the price implies 66.7%. Clearing the floor and having positive EV are different tests.

## 4. Pushes and voids

A whole-number line can land exactly on the number, and the stake is returned. With win 48%, push 6%, lose 46% at 1.91: EV = 0.48 x 0.91 - 0.46 = -0.0232 per £1. Pushes are reported separately and never counted as wins. An NFL moneyline tie is treated the same way.

## 5. Prop probabilities come from the distribution

Simulated shots for a player (seed 20261110, 200,000 draws): mean 2.60, median 2, 10th-90th percentile 0-5.

- Over 2.5 shots: 0.4598; under 2.5: 0.5402.
- At a whole line of 3: over 0.2729, under 0.5402, push 0.1869.

The mean (2.60) is above the 2.5 line, yet the over is 46.0%, because the distribution is skewed. 'Projection minus line' cannot give that number; the distribution does.

## 6. Same-game legs: never multiply

One match simulated 200,000 times (expected goals 1.9 v 1.0, seed 20261110). Home win: 0.5777. Over 1.5 goals: 0.7917.

- Multiplying the singles: 0.4574 (wrong).
- Joint probability from the shared draws: 0.4806 (right).

The legs are positively correlated (a home win needs goals), so the true joint probability is higher than the product. bet365 prices Bet Builders with this correlation built in, so the Bet Builder price must be read from the app and compared with the joint probability from the draws.

## 7. Accumulator in a price band

13 candidate legs from different matches, one of them below the 65% floor. Target band 11.0-11.2 (a 10/1 shot).

| match | leg | model probability | price |
|---|---|---|---|
| match 10 | Under 4.5 | 0.85 | 1.14 |
| match 11 | Over 1.5 | 0.71 | 1.38 |
| match 12 | Home win | 0.73 | 1.35 |
| match 2 | Over 1.5 | 0.76 | 1.29 |
| match 3 | Away win | 0.74 | 1.33 |
| match 5 | Home win | 0.70 | 1.40 |
| match 6 | BTTS yes | 0.68 | 1.44 |
| match 7 | Over 2.5 | 0.66 | 1.50 |

Result: 8 legs, combined price 11.019, joint model probability 0.0778, price-implied probability 0.0908, EV per £1 -0.1423. Legs rejected for being under the floor: 1.

This is the highest joint probability of any combination that lands in the band (the search is exact, checked against brute force in the tests). Whether it is worth placing depends on the EV line, not on the joint probability alone. If no combination fits the band, the builder returns nothing; it does not lower the floor.
