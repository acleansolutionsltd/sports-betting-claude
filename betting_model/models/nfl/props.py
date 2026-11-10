"""Stage 3 - NFL player props, simulated inside the game simulation.

Structure is opportunity x efficiency with uncertainty on both. Team volumes
(pass attempts, carries, touchdowns) come from the same game draws as the
score, so a prop and the game result are always consistent and can be combined
in a Bet Builder.

If an input is missing the prop is skipped and flagged; nothing is filled in by
guesswork. These projections have NOT been backtested against prices (no free
historical prop-price source); treat their probabilities as unvalidated until
Stage 5 has been run on them.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..prop import Prop, _missing

# Dispersion settings (untuned defaults; tune on the Stage 5 harness before trusting tails)
SHARE_CONCENTRATION = 40.0   # beta-binomial concentration for target and carry shares
TD_CONCENTRATION = 12.0      # Dirichlet-multinomial concentration for touchdown allocation
YPR_SHAPE = 1.6              # gamma shape per reception (yards per catch are right-skewed)
YPC_SD = 5.5                 # standard deviation of a single carry, yards


def _volume(draws, name):
    if draws is None or not np.isfinite(draws).all():
        return None
    return np.asarray(draws)


def _beta_binomial(n, share, conc, rng):
    share = min(max(share, 1e-4), 1 - 1e-4)
    p = rng.beta(share * conc, (1 - share) * conc, size=len(n))
    return rng.binomial(n.astype(int), p)


def sim_receiving(player, team_pass_att, target_share, catch_rate, yards_per_rec, rng,
                  playing_time_factor=1.0):
    """Targets ~ beta-binomial(team pass attempts, target share); receptions ~
    binomial(targets, catch rate); yards ~ gamma per reception. Returns
    (receptions Prop, receiving-yards Prop)."""
    miss = _missing(target_share=target_share, catch_rate=catch_rate, yards_per_rec=yards_per_rec,
                    playing_time_factor=playing_time_factor)
    att = _volume(team_pass_att, "pass attempts")
    if att is None:
        miss.append("team_pass_att (pool games without play volumes)")
    if miss:
        r = f"missing input: {', '.join(miss)}"
        return Prop(player, "receptions", skipped=True, reason=r), Prop(player, "receiving_yards", skipped=True, reason=r)
    targets = _beta_binomial(att, target_share * playing_time_factor, SHARE_CONCENTRATION, rng)
    rec = rng.binomial(targets, min(max(catch_rate, 0.0), 1.0))
    yards = np.where(rec > 0, rng.gamma(YPR_SHAPE * np.maximum(rec, 1), yards_per_rec / YPR_SHAPE), 0.0)
    return Prop(player, "receptions", rec), Prop(player, "receiving_yards", np.round(yards))


def sim_rushing(player, team_carries, carry_share, yards_per_carry, rng, opp_rush_factor=1.0,
                playing_time_factor=1.0):
    """Carries ~ beta-binomial(team carries, carry share); yards ~ normal sum of
    carries (rushing yards can be negative). ``opp_rush_factor`` scales yards per
    carry for the opponent's run defence (1.0 = league average)."""
    miss = _missing(carry_share=carry_share, yards_per_carry=yards_per_carry, opp_rush_factor=opp_rush_factor,
                    playing_time_factor=playing_time_factor)
    car = _volume(team_carries, "carries")
    if car is None:
        miss.append("team_carries (pool games without play volumes)")
    if miss:
        r = f"missing input: {', '.join(miss)}"
        return Prop(player, "rush_attempts", skipped=True, reason=r), Prop(player, "rushing_yards", skipped=True, reason=r)
    carries = _beta_binomial(car, carry_share * playing_time_factor, SHARE_CONCENTRATION, rng)
    yards = rng.normal(carries * yards_per_carry * opp_rush_factor, YPC_SD * np.sqrt(np.maximum(carries, 0)))
    return Prop(player, "rush_attempts", carries), Prop(player, "rushing_yards", np.round(yards))


def sim_touchdowns(team_rush_td, team_pass_td, rush_td_share: dict, rec_td_share: dict, rng) -> dict:
    """Allocate the simulated team rushing and passing touchdowns to players
    with a Dirichlet-multinomial. A quarterback appears only in ``rush_td_share``:
    throwing a touchdown pass does not count as scoring one. Shares below 1 leave
    the remainder to 'other'. Returns {player: Prop of touchdown counts}."""
    rtd, ptd = _volume(team_rush_td, "rush td"), _volume(team_pass_td, "pass td")
    players = sorted(set(rush_td_share) | set(rec_td_share))
    if rtd is None or ptd is None:
        return {p: Prop(p, "touchdowns", skipped=True, reason="missing input: team touchdown draws") for p in players}
    total = {p: np.zeros(len(rtd), dtype=int) for p in players}
    for team_td, shares in ((rtd, rush_td_share), (ptd, rec_td_share)):
        names = [p for p, s in shares.items() if s is not None and np.isfinite(s) and s > 0]
        if not names:
            continue
        s = np.array([shares[p] for p in names], float)
        alpha = np.append(s, max(1 - s.sum(), 1e-3)) * TD_CONCENTRATION
        probs = rng.dirichlet(alpha, size=len(team_td))
        counts = rng.multinomial(team_td.astype(int), probs)
        for k, p in enumerate(names):
            total[p] += counts[:, k]
    out = {}
    for p in players:
        bad = [k for k, sh in (("rush_td_share", rush_td_share.get(p, 0.0)), ("rec_td_share", rec_td_share.get(p, 0.0)))
               if sh is None or not np.isfinite(sh)]
        out[p] = Prop(p, "touchdowns", skipped=True, reason=f"missing input: {', '.join(bad)}") if bad \
            else Prop(p, "touchdowns", total[p])
    return out


def player_inputs(player_weeks: pd.DataFrame, team: str, season: int, week: int,
                  halflife_games: float = 5.0, min_games: int = 4) -> pd.DataFrame:
    """Recency-weighted opportunity shares and efficiency for a team's players,
    using only games before (season, week) in this and the previous season.

    Players with fewer than ``min_games`` games for this team come back with
    NaN inputs (so their props are skipped, not guessed). Efficiency is shrunk
    toward the positional average; touchdown shares are each player's share of
    the team's rushing or receiving touchdowns shrunk toward his carry or target
    share (a proxy for red-zone share, which needs play-by-play data).
    """
    pw = player_weeks[(player_weeks.season_type == "REG") & player_weeks.player_id.notna()]
    past = pw[((pw.season == season) & (pw.week < week)) | (pw.season == season - 1)]
    tm = past[past.team == team].copy()
    if tm.empty:
        return pd.DataFrame()
    order = tm[["season", "week"]].drop_duplicates().sort_values(["season", "week"], ascending=False)
    order["ago"] = np.arange(len(order))
    tm = tm.merge(order, on=["season", "week"])
    tm["w"] = 0.5 ** (tm.ago / halflife_games)
    tw = tm.groupby(["season", "week"]).agg(att=("attempts", "sum"), car=("carries", "sum"),
                                            rtd=("rushing_tds", "sum"), ptd=("receiving_tds", "sum"))
    tm = tm.join(tw, on=["season", "week"])
    pos = past.groupby("position").agg(rec=("receptions", "sum"), tgt=("targets", "sum"),
                                       ryd=("receiving_yards", "sum"), car=("carries", "sum"),
                                       ruyd=("rushing_yards", "sum"))
    rows = []
    for (pid, name, position), g in tm.groupby(["player_id", "player_display_name", "position"]):
        w = g.w
        row = {"player_id": pid, "player": name, "position": position, "games": len(g),
               "last_played_games_ago": int(g.ago.min())}
        if len(g) >= min_games and position in pos.index:
            pp = pos.loc[position]
            tgt, rec, car = (w * g.targets).sum(), (w * g.receptions).sum(), (w * g.carries).sum()
            row["target_share"] = tgt / max((w * g.att).sum(), 1e-9)
            row["carry_share"] = car / max((w * g.car).sum(), 1e-9)
            row["catch_rate"] = (rec + 20 * pp.rec / max(pp.tgt, 1)) / (tgt + 20) if pp.tgt else np.nan
            row["yards_per_rec"] = ((w * g.receiving_yards).sum() + 15 * pp.ryd / max(pp.rec, 1)) / (rec + 15) \
                if pp.rec else np.nan
            row["yards_per_carry"] = ((w * g.rushing_yards).sum() + 40 * pp.ruyd / max(pp.car, 1)) / (car + 40) \
                if pp.car else np.nan
            row["rush_td_share"] = ((w * g.rushing_tds).sum() + 4 * row["carry_share"]) / ((w * g.rtd).sum() + 4)
            row["rec_td_share"] = ((w * g.receiving_tds).sum() + 4 * row["target_share"]) / ((w * g.ptd).sum() + 4)
        rows.append(row)
    out = pd.DataFrame(rows)
    for c in ("target_share", "carry_share", "catch_rate", "yards_per_rec", "yards_per_carry",
              "rush_td_share", "rec_td_share"):
        if c not in out:
            out[c] = np.nan
    return out.sort_values(["target_share", "carry_share"], ascending=False, na_position="last").reset_index(drop=True)


def opponent_rush_factor(player_weeks: pd.DataFrame, opponent: str, season: int, week: int,
                         prior_carries: float = 150.0):
    """Opponent yards per carry allowed relative to the league, this season
    before ``week``, shrunk toward 1.0. None if the opponent has no games yet."""
    d = player_weeks[(player_weeks.season == season) & (player_weeks.week < week)
                     & (player_weeks.season_type == "REG")]
    lg_car, lg_yd = d.carries.sum(), d.rushing_yards.sum()
    o = d[d.opponent_team == opponent]
    if lg_car <= 0 or o.carries.sum() <= 0:
        return None
    lg = lg_yd / lg_car
    return float(((o.rushing_yards.sum() + prior_carries * lg) / (o.carries.sum() + prior_carries)) / lg)
