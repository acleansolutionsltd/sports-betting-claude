# betting_model

A working build of the plan in [`docs/BUILD_BETTING_MODEL.md`](../docs/BUILD_BETTING_MODEL.md): a football and NFL model that is built, backtested and audited in code, with a tamper-evident record of every pick. bet365 (UK), decimal prices, every leg at least 65% model probability.

Nothing in here invents a number. Where data could not be fetched or a stage could not be validated, it says so (see [What is not done](#what-is-not-done)).

## Run it

```bash
pip install -r requirements.txt

python -m betting_model.pipeline.run_daily          # fetch, audit, grade tracker, run models, save selections
python -m betting_model.backtest.football           # walk-forward backtest (about 7 minutes)
python -m betting_model.backtest.nfl                # walk-forward backtest (under a minute)
python -m betting_model.analysis.errors             # error breakdown from the backtest output
python -m betting_model.tracker.tracker report      # read-only performance report
python -m betting_model.tracker.tracker verify      # check bets.csv has not been edited
python -m pytest tests                              # 24 tests
```

## What the first backtests found

Full reports: [`backtest/reports/football.md`](backtest/reports/football.md), [`backtest/reports/nfl.md`](backtest/reports/nfl.md), [`analysis/reports/error_analysis.md`](analysis/reports/error_analysis.md). Data fetched 10 Nov 2026.

**Football** (top five leagues; tuned on 2022/23-2023/24, tested out of sample on 2024/25, 2025/26 and 2026/27 to date, 4,004 matches; the table uses the 3,832 where all three models have a prediction):

| | 1X2 log loss (lower is better) |
|---|---|
| De-vigged sharp price alone | 0.96598 |
| Standing blend 80 / 15 / 5 | 0.96784 |
| Team model alone | 0.98575 |

- The blend is slightly but significantly **worse** than the market on its own (paired difference +0.0020 per match, 95% CI +0.0005 to +0.0035), on the validation seasons as well as the test seasons.
- Following the plan's own rule ("if the full model can't beat the market on log loss out of sample, it doesn't get used"), `config.yaml` has `blend_passed_stage5: false`. Live probabilities therefore use the de-vigged sharp price alone; the blend is still computed and logged beside it. Flip the flag only when a backtest report shows the blend ahead.
- Every leg at 65% or more, flat 1 unit at bet365's recorded pre-match prices: 1,407 bets, 73.2% winners, **-23.75 units, ROI -1.7%** (95% interval -4.8% to +1.3%). The market-only version of the same rule: -1.7%. Backing every favourite: -3.2%.
- The 65% floor is honest: 65-70% legs landed 67.9% of the time across 3,361 out-of-sample legs, and no league, season or team shows a bias beyond noise.
- One lead worth testing: 1X2 legs at 65%+ won 78.1% against a stated 73.5%. Legs backing the away side show the same thing. This looks like the favourite-longshot bias (the de-vig step leaving strong favourites under-rated). It is a candidate for a Stage 5 test, not a change that has been made.
- Weekly accumulators from the top legs: every size bucket has an ROI interval that spans zero on 81-84 slips. Not evidence of an edge.

**NFL** (2022 to week 9 of 2026, 1,223 games; the pool is every regular-season game since 2015 before the week being predicted):

- The score-pair bootstrap matches the de-vigged moneyline, spread and total to within 0.00002, with a median effective sample of about 1,050 games.
- On alternative spreads, alternative totals and team totals (72,670 legs) it is no better and no worse than a plain normal distribution (log loss 0.58822 v 0.58834, difference not significant). The plan's claim that the bootstrap beats a normal curve is **not confirmed** on this test; it does beat the bootstrap without the similar-line kernel.
- Derived legs at 65%+ landed slightly more often than stated (+1.1 points on 22,571 legs), so the floor is safe on these markets.
- Moneyline favourites at 65%+ at the consensus closing price: 594 bets, 74.0% winners, **-24.0 units, ROI -4.0%**.

**The plain reading:** legs at 65% or more win about as often as the model says, and at the available prices they lose roughly the bookmaker's margin. A high hit rate is not an edge. Nothing tested so far beats the market.

## How each stage is built

| Stage | Where | What it does |
|---|---|---|
| 1 Architecture | `models/football/dixon_coles.py`, `models/nfl/score_pair.py` | Dixon-Coles with time decay, per-league home advantage, low-score correction and optional negative-binomial tails; market-implied expected goals; shots-on-target form. NFL: maximum-entropy re-weighted score-pair bootstrap. |
| 2 Data audit | `ingest/fetch.py`, `ingest/audit.py` | Cached, capped downloads into `data/raw/<source>/<date>/` with a manifest (URL, fetch time, source update time, SHA-256). The audit writes `data/clean/` and `data/audit_reports/YYYY-MM-DD.md`: missing values, duplicates, names, UTC kickoffs, outliers, an "available at kickoff" table, every correction and every unresolved issue. |
| 3 Props | `models/football/props.py`, `models/nfl/props.py` | Full distributions simulated on the same draws as the match, so props and results can be combined. Missing input means the prop is skipped with a reason. |
| 4 EV and slips | `ev/odds.py`, `ev/acca.py`, [`ev/examples.md`](ev/examples.md) | Fractional, decimal and American odds; power and Shin de-vig; EV per £1 with pushes; exact search for the highest joint probability inside a price band; same-game joint probability from shared draws. |
| 5 Backtest | `backtest/` | Rolling-origin walk-forward, frozen hyperparameters, pre-match prices for betting and closing prices only for closing-line value, baselines, calibration, drawdown, by-market tables. |
| 6 Error analysis | `analysis/errors.py` | Calibration slope, residuals by market, league, season, team and side, with multiple-comparison-corrected bootstrap intervals that resample whole games. |
| 7 Tracker | `tracker/tracker.py`, `tracker/bets.csv`, `tracker/results.csv` | Append-only. Results live in a second file so `bets.csv` is never edited, and each row is hash-chained to the one before, so an edit or deletion is detected. |
| 8 Automation | `pipeline/run_daily.py` | The steps in order, per-event fixed seeds, stale-price and failed-fetch alerts, timestamped outputs in `outputs/<date>/<time>/` that are never overwritten, a non-zero exit code when anything needs attention. |

### Differences from the plan, and why

- **Sharp anchor.** football-data.co.uk stopped publishing Pinnacle prices part-way through 2025/26. The anchor is Pinnacle where it exists, then Betfair Exchange, then the market average; the source is recorded per match. Exchange prices are used as quoted, without adjusting for commission.
- **xG.** football-data.co.uk only added xG columns in 2026/27, FBref blocks automated downloads, and one part-season cannot pass the plan's two-season variable test. The team model therefore runs on goals, with shots on target as the form component. The xG columns are audited and waiting.
- **Tracker columns.** `result` and `net_units` are kept in `results.csv` and computed in the report, instead of being columns in `bets.csv`, so that `bets.csv` never needs a row rewritten.
- **NFL prices.** nflverse holds one consensus line per game, effectively the close. The NFL backtest is a bet-at-the-close test at non-bet365 prices.
- **Tuned settings.** Time decay 0.003/day and ridge 4.0 were best on the validation seasons and are frozen in `config.yaml`. Ridge 4.0 was the edge of the grid searched, so a wider search may find better.

## What is not done

- **No live football card this week.** The football price file covers 6-9 November and has no upcoming top-league fixtures (international break), so the 10 November run saved NFL week 10 legs only. The football live path was exercised with `--as-of 2026-11-06T12:00:00Z`, which writes to `outputs/replay/` and is marked as not a live record.
- **No bet365 feed.** Prices come from football-data.co.uk (bet365's pre-match price, updated twice a week) and nflverse (consensus). Every priced leg is labelled third-party and flagged stale after 60 minutes; check the app before placing.
- **Props are unvalidated.** There is no free historical prop-price source, so no prop has been backtested. NFL props run in the pipeline as projections only (`nfl_props.csv`). Football props have no player data source wired in and are not run automatically. Route participation and true red-zone share need play-by-play data; target share and touchdown share stand in for them.
- **NFL variables 2-10** (EPA, QB, pressure, injuries, weather, pace) are not in the model. Each should be added one at a time through the backtest.
- **Lineup and injury news** is not ingested. The `--kickoff-within` option re-runs only the games in the news window, but the news itself has to change the prices the run reads.
- **BTTS, double chance and alternative lines** have no historical prices, so they have calibration results but no ROI.
- **Scheduling.** The pipeline is a command; it is not yet on a timer.
- **The tracker is empty.** No bets have been recorded.

## Rules enforced in code

- 65% floor: `build_acca` drops legs under the floor and returns nothing when no combination fits the band.
- Same-game legs: joint probability only from shared draws (`joint_prob_from_draws`).
- Market as anchor: no sharp price means no projection; the blend needs the Stage 5 flag.
- No look-ahead: the team model only sees matches before the as-of date (tested by corrupting later results and checking the fit does not move).
- No silent data changes: the audit logs corrections and leaves unresolved rows in place, flagged.
- The pipeline reads formulas and thresholds from `config.yaml`, logs its hash, and never writes to it.
