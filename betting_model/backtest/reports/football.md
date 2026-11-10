# Football walk-forward backtest

Generated 2026-11-10 22:19 UTC from football-data.co.uk files (see data/raw/football_data/manifest.json). Leagues: Premier League, La Liga, Bundesliga, Serie A, Ligue 1.

Settings (frozen before the test seasons were scored): time decay xi=0.003/day, ridge=4.0, blend {'market': 0.8, 'team': 0.15, 'shots': 0.05}, probability floor 65%, flat 1-unit stakes.

How to read this: the team model is refitted before each match date using only earlier matches. Qualification and staking use the pre-match snapshot prices (Friday/Tuesday afternoon); closing prices appear only in the closing-line-value columns. Bet prices are bet365's pre-match prices as recorded by football-data.co.uk.

## Hyperparameter tuning (validation seasons only)

Team model alone, 1X2 log loss, lower is better. Top rows:

|    |     xi |   ridge |    n |   log_loss_1x2 |
|---:|-------:|--------:|-----:|---------------:|
|  0 | 0.003  |     4   | 3474 |       0.987287 |
|  1 | 0.003  |     2   | 3474 |       0.98759  |
|  2 | 0.0019 |     4   | 3474 |       0.987716 |
|  3 | 0.003  |     1   | 3474 |       0.987983 |
|  4 | 0.0019 |     2   | 3474 |       0.988059 |
|  5 | 0.003  |     0.5 | 3474 |       0.988266 |

## Validation seasons (used for tuning - not out of sample): 2223, 2324

### Does the model beat the market-only baseline?

| model                  |   matches |   1X2 log loss |   1X2 Brier |   O/U 2.5 log loss |   O/U 2.5 Brier |
|:-----------------------|----------:|---------------:|------------:|-------------------:|----------------:|
| market only (baseline) |      3474 |        0.96898 |     0.57646 |            0.66856 |         0.23775 |
| standing blend 80/15/5 |      3474 |        0.97071 |     0.57766 |            0.66912 |         0.23806 |
| team model alone       |      3474 |        0.98729 |     0.58889 |            0.67874 |         0.24267 |

Paired 1X2 log-loss difference, blend minus market only: +0.00161 per match (95% bootstrap CI +0.00012 to +0.00295, n=3578): **market only is better**.

Sharp-price source used as the anchor, matches per season:

|   season |   pinnacle |
|---------:|-----------:|
|     2223 |       1826 |
|     2324 |       1752 |

Matches where a model component was missing (promoted side or short shot history) and the blend fell back toward the market: 172.

### Every qualifying leg (model probability at least 65%) at bet365 prices

|                                       |   bets |   wins |   voids |   win_rate |   units |     roi |   max_drawdown |   longest_losing_run |   avg_model_prob |   avg_clv |   beat_close_rate |
|:--------------------------------------|-------:|-------:|--------:|-----------:|--------:|--------:|---------------:|---------------------:|-----------------:|----------:|------------------:|
| standing blend                        |   1125 |    831 |       0 |     0.7387 |   -8.54 | -0.0076 |          28.39 |                    6 |           0.7222 |    0.0007 |            0.3858 |
| market-only baseline (same floor)     |   1168 |    862 |       0 |     0.738  |   -7.26 | -0.0062 |          24.67 |                    6 |           0.7256 |    0.0004 |            0.3861 |
| flat favourite baseline (every match) |   3575 |   1957 |       0 |     0.5474 |  -20.54 | -0.0057 |          50.52 |                    8 |           0.5324 |   -0.0013 |            0.4059 |

Blend ROI 95% bootstrap interval: -0.043 to +0.027 per unit.

By market:

|           |   bets |   wins |   voids |   win_rate |   units |     roi |   max_drawdown |   longest_losing_run |   avg_model_prob |   avg_clv |   beat_close_rate |
|:----------|-------:|-------:|--------:|-----------:|--------:|--------:|---------------:|---------------------:|-----------------:|----------:|------------------:|
| away      |    129 |     93 |       0 |     0.7209 |   -4.32 | -0.0335 |           9.26 |                    3 |           0.7158 |   -0.0055 |            0.3333 |
| home      |    536 |    410 |       0 |     0.7649 |    0.19 |  0.0004 |          12.36 |                    5 |           0.7407 |   -0.0032 |            0.3526 |
| over_2.5  |    376 |    269 |       0 |     0.7154 |   -5.24 | -0.0139 |          16.65 |                    4 |           0.7083 |    0.0039 |            0.4096 |
| under_2.5 |     84 |     59 |       0 |     0.7024 |    0.83 |  0.0099 |           4.46 |                    4 |           0.6765 |    0.0213 |            0.5714 |

By league:

|     |   bets |   wins |   voids |   win_rate |   units |     roi |   max_drawdown |   longest_losing_run |   avg_model_prob |   avg_clv |   beat_close_rate |
|:----|-------:|-------:|--------:|-----------:|--------:|--------:|---------------:|---------------------:|-----------------:|----------:|------------------:|
| D1  |    287 |    207 |       0 |     0.7213 |  -10.68 | -0.0372 |          15.62 |                    6 |           0.7339 |   -0.0017 |            0.3728 |
| E0  |    312 |    240 |       0 |     0.7692 |    7.53 |  0.0241 |           9.56 |                    5 |           0.7286 |   -0.0001 |            0.375  |
| F1  |    157 |    111 |       0 |     0.707  |   -8.25 | -0.0525 |          11.47 |                    5 |           0.7166 |   -0.0015 |            0.3758 |
| I1  |    160 |    116 |       0 |     0.725  |   -2.09 | -0.0131 |           8.63 |                    7 |           0.7103 |   -0.0004 |            0.375  |
| SP1 |    209 |    157 |       0 |     0.7512 |    4.95 |  0.0237 |           5.19 |                    3 |           0.7101 |    0.0079 |            0.4354 |

By season:

|      |   bets |   wins |   voids |   win_rate |   units |     roi |   max_drawdown |   longest_losing_run |   avg_model_prob |   avg_clv |   beat_close_rate |
|-----:|-------:|-------:|--------:|-----------:|--------:|--------:|---------------:|---------------------:|-----------------:|----------:|------------------:|
| 2223 |    492 |    353 |       0 |     0.7175 |  -22.41 | -0.0455 |          28.39 |                    6 |           0.726  |   -0.0003 |            0.372  |
| 2324 |    633 |    478 |       0 |     0.7551 |   13.87 |  0.0219 |          10.05 |                    5 |           0.7193 |    0.0015 |            0.3965 |

Calibration of priced qualifying legs (5% buckets):

| bucket   |   n |   mean_model_prob |   hit_rate |     se |     gap |
|:---------|----:|------------------:|-----------:|-------:|--------:|
| 65%-70%  | 527 |            0.6734 |     0.7135 | 0.0197 |  0.0401 |
| 70%-75%  | 318 |            0.7219 |     0.7516 | 0.0242 |  0.0297 |
| 75%-80%  | 124 |            0.7718 |     0.75   | 0.0389 | -0.0218 |
| 80%-85%  |  87 |            0.8223 |     0.7011 | 0.0491 | -0.1211 |
| 85%-90%  |  52 |            0.8692 |     0.9038 | 0.0409 |  0.0347 |
| 90%-95%  |  16 |            0.9183 |     0.875  | 0.0827 | -0.0433 |
| 95%-100% |   1 |            0.9626 |     1      | 0      |  0.0374 |

### Markets with no historical bet365 price (calibration only, no ROI)

football-data.co.uk does not record BTTS, double chance or alternative totals prices, so these legs can be checked for calibration but not for profit.

| market    |    n |   mean_model_prob |   hit_rate |
|:----------|-----:|------------------:|-----------:|
| btts_no   |   14 |            0.669  |     0.6429 |
| btts_yes  |  125 |            0.676  |     0.656  |
| dc_12     | 3578 |            0.7586 |     0.7468 |
| dc_1x     | 2256 |            0.7889 |     0.8143 |
| dc_x2     | 1164 |            0.7547 |     0.7818 |
| over_1.5  | 3401 |            0.7749 |     0.783  |
| under_3.5 | 2484 |            0.7366 |     0.7472 |
| under_4.5 | 3526 |            0.844  |     0.8471 |

All unpriced qualifying legs, 5% buckets:

| bucket   |    n |   mean_model_prob |   hit_rate |     se |     gap |
|:---------|-----:|------------------:|-----------:|-------:|--------:|
| 65%-70%  | 2298 |            0.6765 |     0.6928 | 0.0096 |  0.0163 |
| 70%-75%  | 4206 |            0.7265 |     0.7266 | 0.0069 |  0.0001 |
| 75%-80%  | 3820 |            0.774  |     0.7812 | 0.0067 |  0.0071 |
| 80%-85%  | 3002 |            0.8233 |     0.8288 | 0.0069 |  0.0055 |
| 85%-90%  | 2154 |            0.874  |     0.8844 | 0.0069 |  0.0104 |
| 90%-95%  |  966 |            0.9192 |     0.9265 | 0.0084 |  0.0073 |
| 95%-100% |  102 |            0.9619 |     0.9412 | 0.0233 | -0.0207 |

### Accumulators (weekly, top legs by probability, one per match)

|          |   bets |   wins |   voids |   win_rate |   units |     roi |   max_drawdown |   longest_losing_run |   avg_model_prob |   avg_price |   avg_joint_model_prob |
|:---------|-------:|-------:|--------:|-----------:|--------:|--------:|---------------:|---------------------:|-----------------:|------------:|-----------------------:|
| 2-3 legs |     74 |     36 |       0 |     0.4865 |   -4.85 | -0.0656 |           8.25 |                    8 |           0.5159 |        1.88 |                 0.5159 |
| 4-6 legs |     73 |     21 |       0 |     0.2877 |   -2.28 | -0.0313 |          11.24 |                   10 |           0.2835 |        3.31 |                 0.2835 |
| 7+ legs  |     64 |      8 |       0 |     0.125  |  -14.87 | -0.2324 |          16    |                   16 |           0.1499 |        6.12 |                 0.1499 |

ROI 95% bootstrap intervals: 2-3 legs -0.29 to +0.15 (74 slips); 4-6 legs -0.38 to +0.34 (73 slips); 7+ legs -0.71 to +0.35 (64 slips). Intervals that span zero mean the accumulator results are not evidence of an edge in either direction.

## Test seasons (out of sample): 2425, 2526, 2627

### Does the model beat the market-only baseline?

| model                  |   matches |   1X2 log loss |   1X2 Brier |   O/U 2.5 log loss |   O/U 2.5 Brier |
|:-----------------------|----------:|---------------:|------------:|-------------------:|----------------:|
| market only (baseline) |      3832 |        0.96598 |     0.57412 |            0.6719  |         0.23967 |
| standing blend 80/15/5 |      3832 |        0.96784 |     0.57511 |            0.67256 |         0.24001 |
| team model alone       |      3832 |        0.98575 |     0.58701 |            0.68314 |         0.24499 |

Paired 1X2 log-loss difference, blend minus market only: +0.00196 per match (95% bootstrap CI +0.00048 to +0.00347, n=4004): **market only is better**.

Sharp-price source used as the anchor, matches per season:

|   season |   betfair_exchange |   market_average |   pinnacle |
|---------:|-------------------:|-----------------:|-----------:|
|     2425 |                  0 |                0 |       1752 |
|     2526 |                743 |              107 |        902 |
|     2627 |                500 |                0 |          0 |

Matches where a model component was missing (promoted side or short shot history) and the blend fell back toward the market: 263.

### Every qualifying leg (model probability at least 65%) at bet365 prices

|                                       |   bets |   wins |   voids |   win_rate |   units |     roi |   max_drawdown |   longest_losing_run |   avg_model_prob |   avg_clv |   beat_close_rate |
|:--------------------------------------|-------:|-------:|--------:|-----------:|--------:|--------:|---------------:|---------------------:|-----------------:|----------:|------------------:|
| standing blend                        |   1407 |   1030 |       0 |     0.7321 |  -23.75 | -0.0169 |          43.7  |                    4 |           0.7192 |    0.0008 |            0.4016 |
| market-only baseline (same floor)     |   1477 |   1077 |       0 |     0.7292 |  -25.77 | -0.0174 |          46.28 |                    5 |           0.7233 |   -0.0001 |            0.3961 |
| flat favourite baseline (every match) |   4001 |   2150 |       0 |     0.5374 | -126.56 | -0.0316 |         154.21 |                   11 |           0.5327 |   -0.0022 |            0.4221 |

Blend ROI 95% bootstrap interval: -0.048 to +0.013 per unit.

By market:

|           |   bets |   wins |   voids |   win_rate |   units |     roi |   max_drawdown |   longest_losing_run |   avg_model_prob |   avg_clv |   beat_close_rate |
|:----------|-------:|-------:|--------:|-----------:|--------:|--------:|---------------:|---------------------:|-----------------:|----------:|------------------:|
| away      |    144 |    113 |       0 |     0.7847 |    7.06 |  0.049  |           5.44 |                    2 |           0.7232 |    0.0023 |            0.4653 |
| home      |    600 |    468 |       0 |     0.78   |   11.91 |  0.0198 |          12.57 |                    4 |           0.7382 |   -0.0025 |            0.39   |
| over_2.5  |    528 |    362 |       0 |     0.6856 |  -32.4  | -0.0614 |          36.33 |                    5 |           0.7068 |    0.0001 |            0.3712 |
| under_2.5 |    135 |     87 |       0 |     0.6444 |  -10.32 | -0.0764 |          13.37 |                    4 |           0.6792 |    0.0166 |            0.5037 |

By league:

|     |   bets |   wins |   voids |   win_rate |   units |     roi |   max_drawdown |   longest_losing_run |   avg_model_prob |   avg_clv |   beat_close_rate |
|:----|-------:|-------:|--------:|-----------:|--------:|--------:|---------------:|---------------------:|-----------------:|----------:|------------------:|
| D1  |    357 |    266 |       0 |     0.7451 |   -1.67 | -0.0047 |          10.28 |                    4 |           0.7305 |    0.0001 |            0.3922 |
| E0  |    276 |    187 |       0 |     0.6775 |  -24.82 | -0.0899 |          26.72 |                    5 |           0.7137 |   -0.0049 |            0.3442 |
| F1  |    212 |    158 |       0 |     0.7453 |    1.1  |  0.0052 |           6.89 |                    4 |           0.7171 |    0.0001 |            0.3726 |
| I1  |    198 |    145 |       0 |     0.7323 |   -1.23 | -0.0062 |          11.5  |                    3 |           0.7097 |   -0.0026 |            0.399  |
| SP1 |    364 |    274 |       0 |     0.7527 |    2.87 |  0.0079 |          11.14 |                    5 |           0.7187 |    0.0082 |            0.4725 |

By season:

|      |   bets |   wins |   voids |   win_rate |   units |     roi |   max_drawdown |   longest_losing_run |   avg_model_prob |   avg_clv |   beat_close_rate |
|-----:|-------:|-------:|--------:|-----------:|--------:|--------:|---------------:|---------------------:|-----------------:|----------:|------------------:|
| 2425 |    670 |    488 |       0 |     0.7284 |  -13.52 | -0.0202 |          25.55 |                    4 |           0.7204 |    0.0025 |            0.4239 |
| 2526 |    536 |    384 |       0 |     0.7164 |  -20    | -0.0373 |          25.36 |                    4 |           0.7165 |   -0.0019 |            0.3619 |
| 2627 |    201 |    158 |       0 |     0.7861 |    9.77 |  0.0486 |           6.06 |                    4 |           0.7224 |    0.0024 |            0.4328 |

Calibration of priced qualifying legs (5% buckets):

| bucket   |   n |   mean_model_prob |   hit_rate |     se |     gap |
|:---------|----:|------------------:|-----------:|-------:|--------:|
| 65%-70%  | 679 |            0.672  |     0.6672 | 0.0181 | -0.0048 |
| 70%-75%  | 394 |            0.7222 |     0.7462 | 0.0219 |  0.024  |
| 75%-80%  | 180 |            0.7756 |     0.8111 | 0.0292 |  0.0355 |
| 80%-85%  |  83 |            0.8249 |     0.8916 | 0.0341 |  0.0667 |
| 85%-90%  |  50 |            0.8745 |     0.9    | 0.0424 |  0.0255 |
| 90%-95%  |  21 |            0.9176 |     0.8571 | 0.0764 | -0.0604 |

### Markets with no historical bet365 price (calibration only, no ROI)

football-data.co.uk does not record BTTS, double chance or alternative totals prices, so these legs can be checked for calibration but not for profit.

| market    |    n |   mean_model_prob |   hit_rate |
|:----------|-----:|------------------:|-----------:|
| btts_no   |   23 |            0.6675 |     0.4783 |
| btts_yes  |  204 |            0.6745 |     0.6471 |
| dc_12     | 4004 |            0.7593 |     0.751  |
| dc_1x     | 2524 |            0.7865 |     0.7956 |
| dc_x2     | 1289 |            0.7578 |     0.7843 |
| over_1.5  | 3753 |            0.7807 |     0.7831 |
| under_3.5 | 2649 |            0.7388 |     0.7433 |
| under_4.5 | 3926 |            0.8402 |     0.8492 |

All unpriced qualifying legs, 5% buckets:

| bucket   |    n |   mean_model_prob |   hit_rate |     se |    gap |
|:---------|-----:|------------------:|-----------:|-------:|-------:|
| 65%-70%  | 2682 |            0.6767 |     0.682  | 0.009  | 0.0052 |
| 70%-75%  | 4387 |            0.7268 |     0.7271 | 0.0067 | 0.0004 |
| 75%-80%  | 4377 |            0.7738 |     0.7793 | 0.0063 | 0.0055 |
| 80%-85%  | 3311 |            0.8242 |     0.8251 | 0.0066 | 0.0009 |
| 85%-90%  | 2344 |            0.8732 |     0.8823 | 0.0067 | 0.009  |
| 90%-95%  | 1140 |            0.9196 |     0.9237 | 0.0079 | 0.004  |
| 95%-100% |  131 |            0.9616 |     0.9771 | 0.0131 | 0.0155 |

### Accumulators (weekly, top legs by probability, one per match)

|          |   bets |   wins |   voids |   win_rate |   units |     roi |   max_drawdown |   longest_losing_run |   avg_model_prob |   avg_price |   avg_joint_model_prob |
|:---------|-------:|-------:|--------:|-----------:|--------:|--------:|---------------:|---------------------:|-----------------:|------------:|-----------------------:|
| 2-3 legs |     84 |     52 |       0 |     0.619  |    8.08 |  0.0962 |           7.5  |                    4 |           0.5234 |        1.83 |                 0.5234 |
| 4-6 legs |     84 |     27 |       0 |     0.3214 |   -3.75 | -0.0446 |          15.94 |                    7 |           0.2877 |        3.17 |                 0.2877 |
| 7+ legs  |     81 |     18 |       0 |     0.2222 |   16.75 |  0.2068 |          22.02 |                   21 |           0.1477 |        5.92 |                 0.1477 |

ROI 95% bootstrap intervals: 2-3 legs -0.09 to +0.27 (84 slips); 4-6 legs -0.35 to +0.26 (84 slips); 7+ legs -0.27 to +0.75 (81 slips). Intervals that span zero mean the accumulator results are not evidence of an edge in either direction.

