# Building the Football + NFL Betting Model

Built from the 8-prompt thread by [@Rusty_Bill](https://x.com/Rusty_Bill/status/2119965657307750511) (posted 10 Nov 2026), adapted to Rich's setup: bet365 (UK, GBP), Bet Builder, accumulators and ladder steps, every leg ≥ 65% model probability.

The thread's core idea: **use AI to build, backtest and audit a model, not to guess winners.** Judge the model on data it has never seen, with a transparent record of every pick, not on its best week.

---

## Part A — The thread, unrolled

**Opening post.** Most people use ChatGPT to make picks. That's the wrong approach. AI is far more useful for building a betting model than pretending it knows who wins tonight. Here are 8 prompts to build, backtest and improve your own model.

1. **The Model Architect.** "Act as a quantitative sports analyst. Help me build a prediction model for [SPORT] and [BET TYPE]. Identify the 10 most predictive variables, where to obtain historical data, how to create a simple baseline, and how to test whether each variable improves predictions. Prioritize measurable data over narratives. Explain which variables could cause data leakage."
2. **The Data Quality Inspector.** "Audit my historical [SPORT] dataset before I build a model. Identify missing values, duplicate games, inconsistent player IDs, incorrect dates, outliers, and statistics that weren't available before kickoff. Create Python code to clean the dataset without silently deleting records. Produce a report of every correction and unresolved issue."
3. **The Player Prop Projection Builder.** "Help me build a statistical projection model for [PLAYER PROP]. Use historical game logs, projected playing time, opportunity volume, efficiency, opponent adjustments, and uncertainty. Start with a simple baseline. Write reproducible Python code and produce a projected mean, median, and probability distribution. Never invent missing inputs."
4. **The Expected Value Calculator.** "Build a Python calculator that compares my model's probabilities against sportsbook odds. Convert American odds into implied probabilities, estimate bookmaker margin, and calculate expected value per $1 wager. For player props, derive over/under probabilities from my projected distribution, not just the difference between my projection and the betting line. Include pushes, odds formats, and worked examples."
5. **The Backtesting Specialist.** "Design a walk-forward backtest for my [SPORT] betting model. Train only on information available before each game and test on future games. Prevent look-ahead bias, data leakage, and repeated tuning on the test set. Track every qualifying selection, including losses. Report ROI, units, sample size, drawdowns, calibration, and performance by market. Compare results against a simple baseline."
6. **The Model Improvement Analyst.** "Analyze my model's historical predictions against actual results. Break down errors by player, team, opponent, market, projection range, and betting line. Determine whether the model is systematically overestimating or underestimating outcomes. Separate random variance from repeatable weaknesses. Suggest improvements, but require out-of-sample validation before accepting any changes."
7. **The Betting Performance Tracker.** "Build a transparent performance tracker for my model using [CSV OR DATABASE]. Record every qualifying play, its timestamp, sportsbook, line, odds, model probability, result, and net units. Calculate win rate, ROI, cumulative profit, and maximum drawdown. Use flat 1-unit risk as the baseline. Never remove losing picks or retroactively change qualification criteria. Flag missing or unverifiable records."
8. **The Model Automation Engineer.** "Help me automate my [SPORT] prediction model. Design a workflow that imports updated statistics, validates data freshness, runs projections, compares market lines, and saves timestamped selections before games begin. Keep expensive API calls controlled. Separate administrative refresh actions from public dashboards. Include error handling, caching, usage limits, and alerts for stale data. Do not modify the underlying prediction formulas without approval."

**Closing post.** Don't judge a model by its biggest winning week; judge it by whether its predictions stay accurate on unseen data. A transparent record, consistent selection rules and hundreds of properly tracked predictions beat a screenshot of a few winners. (The author links his own NFL and NHL models at rustybillsports.com.)

---

## Part B — The build plan

Each stage below maps to one thread prompt, filled in for football and NFL.

### Repo layout

```
betting_model/
  config.yaml              # leagues, seeds, thresholds (65% floor), bankroll unit
  data/raw/                # untouched downloads, one folder per source + date
  data/clean/              # outputs of the data audit (Stage 2)
  data/audit_reports/      # every correction and unresolved issue
  models/football/         # Dixon-Coles / bivariate Poisson + player props
  models/nfl/              # score-pair model + player props
  ev/                      # odds conversion, de-vig, EV, acca builder (Stage 4)
  backtest/                # walk-forward harness (Stage 5)
  analysis/                # error breakdowns (Stage 6)
  tracker/bets.csv         # every qualifying play, never edited (Stage 7)
  pipeline/                # scheduled refresh + snapshot jobs (Stage 8)
```

Everything is Python (pandas, numpy, scipy, statsmodels; optional PyMC). Every simulation uses a fixed, logged seed.

---

### Stage 1 — Model architecture (Prompt 1)

**Football (match result, totals, BTTS, handicaps).**
Core model: Dixon-Coles adjusted Poisson on team attack and defence strengths with time decay, then a bivariate Poisson or negative-binomial version for fatter tails (Over 4.5 and Under 1.5 are poorly calibrated under plain Poisson).

Ten most predictive variables, measurable before kickoff:
1. De-vigged closing-style sharp price (Pinnacle) for 1X2 and totals; this is the market anchor.
2. Non-penalty xG for and against, recency-weighted over the last 6–8 matches (FBref, Understat).
3. Shots and shots on target for and against, as a stabiliser for small xG samples.
4. Home advantage, estimated per league.
5. Confirmed XI and key absences, measured as minutes-weighted xG contribution lost.
6. Rest days and fixture congestion (European midweek, cup replays).
7. Travel distance (relevant for Europe and the MLS).
8. Goalkeeper shot-stopping (post-shot xG minus goals conceded), shrunk heavily.
9. Game-state tendencies: how often each team protects a lead or chases.
10. Referee card and penalty rates (for card props and penalty-linked markets).

Blend: market 80%, team xG model 15%, recent shot form 5% (current standing weights; retune only via Stage 5).

**NFL (moneyline, spread, totals).**
Core model: an empirical score-pair bootstrap from completed regular-season games, re-weighted (maximum-entropy) so its win, cover and total probabilities match de-vigged sharp moneyline, spread and total prices. This keeps realistic NFL margins (3s, 7s, 10s) that a normal distribution misses.

Ten most predictive variables:
1. De-vigged sharp moneyline, spread and total.
2. EPA per play, offence and defence, opponent-adjusted.
3. Success rate, offence and defence.
4. Starting QB identity and QB-level EPA (the biggest single news adjustment).
5. Offensive line pressure rate allowed versus defensive pressure rate.
6. Injuries weighted by snap share and position value.
7. Rest (short week, bye, Thursday) and travel (time zones, international games).
8. Weather: wind speed above about 15 mph and heavy precipitation for totals and passing props.
9. Pace (seconds per play) and neutral pass rate.
10. Red-zone trip rate and red-zone TD rate, shrunk toward league average.

**Data leakage to watch (both sports).** Never use full-season averages that include the game being predicted; never use closing prices for a bet placed earlier; never use the final confirmed XI or inactive list for a bet placed before it was published; never use post-match ratings (player match ratings, PFF grades) published after the game.

**Baselines every model must beat.** Football: de-vigged Pinnacle price alone. NFL: de-vigged sharp price alone. If the full model can't beat the market on log loss out of sample, it doesn't get used to add anything beyond the market.

**Variable test.** Add one variable at a time on the walk-forward harness (Stage 5). Keep it only if log loss and Brier score improve out of sample across at least two seasons.

---

### Stage 2 — Data quality audit (Prompt 2)

Sources: football-data.co.uk (results and closing prices), FBref and Understat (xG, shots, lineups), nflverse / nflfastR (play-by-play, EPA, rosters, injuries), Pro Football Reference, official injury reports.

Checks the audit script runs, writing a report rather than deleting anything:
- Missing values per column, per season and per team.
- Duplicate fixtures (same teams and date), including postponed games that appear twice.
- Team and player name mismatches across sources (one ID map file, e.g. `Man Utd` vs `Manchester United`; nflverse `gsis_id` as the NFL key).
- Dates and kickoff times stored in UTC, then converted; spot-check matches abroad (e.g. NFL in Madrid or London).
- Outliers: xG above 6, totals above 9 goals, NFL scores above 60 flagged for manual review.
- "Available at kickoff" flag on every feature column, with a timestamp of when the value existed.
- Corrections are logged to `data/audit_reports/YYYY-MM-DD.md` with row, old value, new value and reason; unresolved issues are listed separately.

---

### Stage 3 — Player prop projections (Prompt 3)

Every prop is built as a full distribution, not a single number, and is simulated inside the same match simulation so props and team results stay consistent.

Structure: projected opportunity × efficiency, with uncertainty on both.
- **Football shots and shots on target.** Projected minutes (from XI news and recent minutes) × shots per 90 (shrunk toward positional average) × team-xG multiplier from the match sim, giving a Poisson or negative-binomial count.
- **Football anytime scorer.** The player's share of team non-penalty xG plus penalty duty, applied to the simulated team goal count.
- **Football cards.** Player foul rate × referee card rate × match intensity (derby, relegation fight).
- **NFL receptions and receiving yards.** Snap share × route participation × target share → targets (beta-binomial on team pass attempts from the game sim) → catch rate → yards per reception (gamma or log-normal).
- **NFL rushing yards and attempts.** Rush share of team carries from the game sim × yards per carry, adjusted for opponent run defence.
- **NFL anytime TD.** Team offensive TDs from the score sim, split rush vs pass, then allocated to players by red-zone share (Dirichlet-multinomial). QBs count rushing TDs only.

Each projection outputs a mean, median and full distribution. If an input such as snap share is missing, the prop is skipped and flagged, never filled in by guesswork.

---

### Stage 4 — EV calculator and slip builder (Prompt 4)

`ev/` functions:
- Convert fractional, decimal and American odds to implied probability.
- Remove bookmaker margin (overround) with the power or Shin method on two-way and three-way markets.
- EV per £1: `p × (decimal − 1) − (1 − p)`.
- Prop over/under probabilities come from the Stage 3 distribution, never from "projection minus line".
- Pushes on whole-number lines and NFL moneyline ties are modelled as voids (stake returned), and reported separately from wins.
- Worked examples live in `ev/examples.md`.

Accumulator rules (Rich's standing rules):
- Every leg must be at least 65% model probability.
- Choose the combination with the highest joint model probability inside the target price band (for example decimal 11.0–11.2 for a 10/1).
- Different matches: joint probability = product of legs.
- Same match (Bet Builder): joint probability comes from the shared simulation draws. Never multiply same-game singles to estimate a Bet Builder price.
- Report both the model joint probability and the price-implied probability; a high joint probability is not the same as positive EV.
- Every price records its source and timestamp; anything not from the bet365 app is labelled third-party and checked in the app before placing.

---

### Stage 5 — Walk-forward backtest (Prompt 5)

- Rolling origin: fit on everything before matchweek *t*, predict matchweek *t*, roll forward. Never fit on the test week.
- Use only prices that existed at the assumed bet time (opening or a fixed pre-kickoff snapshot), not closing prices, unless the strategy is explicitly to bet at the close.
- Hyperparameters (time-decay, blend weights, negative-binomial dispersion) are tuned on a validation season, then frozen for the test season.
- Track every selection that met the rules, including losses.
- Report: number of bets, ROI, units won, maximum drawdown, longest losing run, calibration (reliability curve in 5% buckets), Brier score, log loss, and closing-line value (did our price beat the close?).
- Break results down by market: 1X2, totals, BTTS, handicaps, each prop type, and accumulators of 2–3, 4–6 and 7+ legs.
- Always compare with the market-only baseline and with a flat "favourite" baseline.

---

### Stage 6 — Model improvement analysis (Prompt 6)

- Bucket predictions by stated probability (65–70%, 70–75%, …) and compare with the actual hit rate. If 65–70% legs land 60% of the time, the 65% floor is not really 65%.
- Break errors down by league, team, opponent strength, market, line, and home/away.
- Test for systematic bias with mean residual and a calibration slope; separate noise from repeatable weakness with bootstrap confidence intervals.
- Any proposed change (new variable, new blend weight) must improve out-of-sample results on the Stage 5 harness before it goes live.

---

### Stage 7 — Performance tracker (Prompt 7)

`tracker/bets.csv`, append-only:

| column | example |
|---|---|
| bet_id | 2026-11-08-mixed-101 |
| placed_at_utc | 2026-11-08T13:55:00Z |
| sport / league | NFL / Football-SerieA |
| event | Inter v Como |
| market / selection | BTTS / Yes |
| bookmaker | bet365 |
| price_decimal | 1.50 |
| price_source_and_time | matchesnow 13:00 GMT (third-party) |
| model_prob | 0.651 |
| implied_prob | 0.667 |
| slip_id / leg_no | mixed-101 / 3 |
| stake_units | 1 |
| result | win / loss / void |
| net_units | +0.50 |

Reports: win rate per leg and per slip, ROI, cumulative profit, maximum drawdown and calibration of model probability versus outcome. Flat 1-unit stake is the baseline. Losing picks are never removed, and selection rules are never changed after the fact. Missing or unverifiable records are flagged, not filled in.

---

### Stage 8 — Automation (Prompt 8)

Daily schedule (UK time):
1. **Morning:** pull results from the previous day, grade the tracker, refresh team and player stats, run the data audit.
2. **Price snapshot:** fetch sharp prices and bet365 prices with timestamps; cache them; flag any source older than 60 minutes as stale.
3. **Run the models** with fixed seeds; save outputs to a dated folder.
4. **News window:** about 75 minutes before football kickoffs (team sheets) and 90 minutes before NFL kickoffs (inactives), re-run only the affected games.
5. **Save timestamped selections** before kickoff so the record is honest.
6. **Alerts** for stale data, failed fetches (for example SSL errors), or a leg that kicks off before a slip is delivered.

API calls are cached and rate-limited. Refresh jobs are kept separate from any dashboard or tracker page. Model formulas are never changed by the automation itself; changes go through Stage 5 and Stage 6 first.

---

## Part C — Rules that never change

- No invented odds, stats or simulation results. If something can't be fetched or run, say so.
- Every leg at least 65% model probability; don't lower the floor to hit a price.
- Choose by highest simulated probability; don't exclude leg types just because they lost before.
- "Run the simulation" means every match in the top leagues that weekend, not a hand-picked subset.
- Same-game legs are always simulated jointly.
- The market is the anchor; the model has to earn its deviations out of sample.
