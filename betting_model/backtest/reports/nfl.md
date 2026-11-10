# NFL walk-forward backtest

Generated 2026-11-10 22:11 UTC from nflverse games.csv. Test seasons [2022, 2023, 2024, 2025, 2026] (regular season, completed games: 1223). Pool: all regular-season games since 2015 that kicked off before the week being predicted.

Caveats: nflverse holds one consensus line per game, effectively the closing line, so this is a bet-at-the-close test and the prices are not bet365 prices. Alternative lines and team totals have no historical prices, so they are tested for accuracy and calibration only.

## Fit quality

Largest error matching the three market probabilities: 1.07e-05. Effective sample size of the weighted pool: median 1055, minimum 85 (games below 150: 6).

## Derived markets: bootstrap vs baselines (all legs, lower log loss is better)

| family      |   legs |   kernel bootstrap (model) |   uniform bootstrap |   normal baseline |
|:------------|-------:|---------------------------:|--------------------:|------------------:|
| alt spread  |  24094 |                    0.5939  |             0.59511 |           0.5956  |
| alt total   |  24116 |                    0.61331 |             0.61543 |           0.61253 |
| team total  |  24460 |                    0.55788 |             0.56084 |           0.55734 |
| all derived |  72670 |                    0.58822 |             0.59032 |           0.58834 |

Paired difference, kernel bootstrap minus normal, resampling whole games: -0.00014 (95% CI -0.00142 to +0.00115): **no significant difference**.

## Calibration of derived legs at or above the 65% floor

| bucket   |    n |   mean_model_prob |   hit_rate |     se |    gap |
|:---------|-----:|------------------:|-----------:|-------:|-------:|
| 65%-70%  | 6004 |            0.678  |     0.6904 | 0.006  | 0.0124 |
| 70%-75%  | 6576 |            0.7228 |     0.7321 | 0.0055 | 0.0093 |
| 75%-80%  | 5199 |            0.7733 |     0.7763 | 0.0058 | 0.003  |
| 80%-85%  | 3028 |            0.8192 |     0.8402 | 0.0067 | 0.021  |
| 85%-90%  | 1102 |            0.8732 |     0.8811 | 0.0097 | 0.008  |
| 90%-95%  |  595 |            0.9203 |     0.9496 | 0.009  | 0.0292 |
| 95%-100% |   67 |            0.9578 |     0.9851 | 0.0148 | 0.0273 |

By family:

| family     |    n |   mean_model_prob |   hit_rate |
|:-----------|-----:|------------------:|-----------:|
| alt spread | 7826 |            0.7424 |     0.7493 |
| alt total  | 7180 |            0.7226 |     0.7354 |
| team total | 7565 |            0.78   |     0.7927 |

## Moneyline legs at or above 65% (consensus closing price, flat 1 unit)

The model's moneyline probability equals the de-vigged market, so this row is the market-only baseline; the second row backs every favourite regardless of price.

|                  |   bets |   wins |   voids |   win_rate |   units |     roi |   max_drawdown |   longest_losing_run |   avg_model_prob |
|:-----------------|-------:|-------:|--------:|-----------:|--------:|--------:|---------------:|---------------------:|-----------------:|
| moneyline >= 65% |    594 |    438 |       2 |     0.7399 |  -24.03 | -0.0404 |          29.35 |                    3 |           0.7557 |
| every favourite  |   1218 |    823 |       4 |     0.6779 |   -6.28 | -0.0052 |          35.17 |                    5 |           0.6668 |

By season:

|      |   bets |   wins |   voids |   win_rate |   units |     roi |   max_drawdown |   longest_losing_run |   avg_model_prob |
|-----:|-------:|-------:|--------:|-----------:|--------:|--------:|---------------:|---------------------:|-----------------:|
| 2022 |    130 |     97 |       1 |     0.7519 |   -1.26 | -0.0097 |          11.49 |                    3 |           0.7449 |
| 2023 |    119 |     82 |       0 |     0.6891 |  -14.16 | -0.119  |          14.84 |                    3 |           0.7628 |
| 2024 |    134 |    104 |       0 |     0.7761 |    2.68 |  0.02   |           8.75 |                    3 |           0.7473 |
| 2025 |    147 |    107 |       1 |     0.7329 |  -10.74 | -0.073  |          15.6  |                    3 |           0.771  |
| 2026 |     64 |     48 |       0 |     0.75   |   -0.55 | -0.0087 |           5.83 |                    3 |           0.747  |

| bucket   |   n |   mean_model_prob |   hit_rate |     se |     gap |
|:---------|----:|------------------:|-----------:|-------:|--------:|
| 65%-70%  | 168 |            0.6756 |     0.6667 | 0.0364 | -0.009  |
| 70%-75%  | 137 |            0.724  |     0.7226 | 0.0382 | -0.0014 |
| 75%-80%  | 131 |            0.7736 |     0.6947 | 0.0402 | -0.079  |
| 80%-85%  |  80 |            0.8174 |     0.8    | 0.0447 | -0.0174 |
| 85%-90%  |  53 |            0.8781 |     0.8868 | 0.0435 |  0.0087 |
| 90%-95%  |  24 |            0.9149 |     1      | 0      |  0.0851 |
| 95%-100% |   1 |            0.9526 |     1      | 0      |  0.0474 |
