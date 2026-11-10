"""Stage 3 - football player props, simulated on the match simulation's draws.

A player's goals are allocated from the simulated team goals, and his shots are
built on top of his goals, so "player to score", "player shots" and the match
result are consistent draw by draw and can be combined in a Bet Builder.

Inputs (projected minutes, per-90 rates, goal share, referee rate) must be
supplied by the caller from a real source. No football player data source is
wired into the pipeline yet, so these functions are not run automatically, and
they have not been backtested. A missing input skips the prop with a reason; it
is never filled in.
"""
from __future__ import annotations

import numpy as np

from ..prop import Prop, _missing

PENALTY_GOAL_FRACTION = 0.09  # assumed share of team goals scored from penalties; verify per league
SHOT_DISPERSION = 10.0        # gamma-Poisson shape for non-scoring shots (untuned)


def goal_share(npxg_share: float, penalty_share: float = 0.0,
               penalty_fraction: float = PENALTY_GOAL_FRACTION) -> float:
    """Share of team goals: non-penalty xG share plus penalty duty."""
    return npxg_share * (1 - penalty_fraction) + penalty_share * penalty_fraction


def sim_player(player, team_goals, team_lambda, team_baseline_goals, p_start, minutes_if_start,
               minutes_if_sub, shots_per90, sot_per90, goal_share, rng) -> dict:
    """Shots, shots on target and goals for one player.

    team_goals: this team's simulated goals (one per draw) from the match sim.
    team_lambda / team_baseline_goals: the team-xG multiplier - how much better
    or worse than its usual output the team is expected to be in this match.
    goal_share: the player's share of team goals when he plays 90 minutes.
    """
    stats = ("shots", "shots_on_target", "goals")
    miss = _missing(team_lambda=team_lambda, team_baseline_goals=team_baseline_goals, p_start=p_start,
                    minutes_if_start=minutes_if_start, minutes_if_sub=minutes_if_sub,
                    shots_per90=shots_per90, sot_per90=sot_per90, goal_share=goal_share)
    if team_goals is None:
        miss.append("team_goals")
    if miss:
        return {s: Prop(player, s, skipped=True, reason=f"missing input: {', '.join(miss)}") for s in stats}
    team_goals = np.asarray(team_goals)
    n = len(team_goals)
    starts = rng.random(n) < p_start
    frac = np.where(starts, minutes_if_start, minutes_if_sub) / 90.0
    mult = team_lambda / team_baseline_goals
    goals = rng.binomial(team_goals, np.clip(goal_share * frac, 0, 1))
    exp_goals = team_lambda * goal_share * frac
    other_mean = np.maximum(shots_per90 * frac * mult - exp_goals, 0.0)
    other = rng.poisson(other_mean * rng.gamma(SHOT_DISPERSION, 1 / SHOT_DISPERSION, n))
    denom = np.maximum(shots_per90 * frac * mult - exp_goals, 1e-9)
    q = np.clip((sot_per90 * frac * mult - exp_goals) / denom, 0, 1)
    sot = goals + rng.binomial(other, q)
    return {"shots": Prop(player, "shots", goals + other), "shots_on_target": Prop(player, "shots_on_target", sot),
            "goals": Prop(player, "goals", goals)}


def sim_card(player, cards_per90, referee_factor, intensity, exp_minutes, n, rng) -> Prop:
    """Cards: player card rate x referee factor (referee cards per match relative
    to the league) x match intensity (1.0 normal; above 1 for derbies and
    relegation fights) x minutes."""
    miss = _missing(cards_per90=cards_per90, referee_factor=referee_factor, intensity=intensity,
                    exp_minutes=exp_minutes)
    if miss:
        return Prop(player, "cards", skipped=True, reason=f"missing input: {', '.join(miss)}")
    rate = cards_per90 * referee_factor * intensity * exp_minutes / 90.0
    return Prop(player, "cards", np.minimum(rng.poisson(rate, n), 2))
