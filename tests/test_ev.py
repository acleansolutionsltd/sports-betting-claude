import math

import numpy as np
import pytest

from betting_model.ev import odds
from betting_model.ev.acca import Leg, build_acca, joint_prob_from_draws


def test_conversions():
    assert odds.to_decimal("10/1") == 11.0
    assert odds.to_decimal("4/6") == pytest.approx(1.6667, abs=1e-4)
    assert odds.to_decimal("evens") == 2.0
    assert odds.to_decimal("+150") == 2.5
    assert odds.to_decimal("-200") == 1.5
    assert odds.to_decimal(-110, "american") == pytest.approx(1.9091, abs=1e-4)
    assert odds.to_decimal(1.5) == 1.5
    with pytest.raises(ValueError):
        odds.to_decimal(0.9)


@pytest.mark.parametrize("method", ["power", "shin", "multiplicative"])
def test_devig_sums_to_one_and_keeps_order(method):
    p = odds.devig([1.5, 4.2, 7.0], method)
    assert p.sum() == pytest.approx(1.0, abs=1e-9)
    assert p[0] > p[1] > p[2]
    assert (p < 1 / np.array([1.5, 4.2, 7.0])).all()  # every outcome loses some margin


def test_devig_fair_book_unchanged_and_missing_price_is_nan():
    assert odds.devig_power([2.0, 2.0]) == pytest.approx([0.5, 0.5])
    out = odds.devig_power([[1.9, 1.9], [np.nan, 1.9], [0.0, 1.9]])
    assert out[0] == pytest.approx([0.5, 0.5])
    assert np.isnan(out[1]).all() and np.isnan(out[2]).all()


def test_ev_and_push():
    assert odds.ev_per_unit(0.651, 1.50) == pytest.approx(0.651 * 0.5 - 0.349)
    assert odds.ev_per_unit(0.5, 2.0) == pytest.approx(0.0)
    assert odds.ev_per_unit(0.45, 2.0, p_push=0.10) == pytest.approx(0.0)  # push returns the stake


def test_prop_probability_comes_from_distribution():
    draws = np.array([3, 4, 5, 5, 6, 9])
    p = odds.outcome_probs(draws, 5)
    assert p == {"over": pytest.approx(2 / 6), "under": pytest.approx(2 / 6), "push": pytest.approx(2 / 6)}


def test_same_game_joint_is_not_the_product():
    rng = np.random.default_rng(1)
    goals = rng.poisson(2.7, 50_000)
    over15, over25 = goals > 1.5, goals > 2.5
    joint = joint_prob_from_draws(over15, over25)
    assert joint == pytest.approx(over25.mean())           # over 2.5 implies over 1.5
    assert joint > over15.mean() * over25.mean() + 0.05    # multiplying singles would be badly wrong
    with pytest.raises(ValueError):
        joint_prob_from_draws(over15, over25[:10])


def test_acca_respects_floor_band_and_one_leg_per_event():
    legs = [Leg(f"m{i}", f"leg{i}", p, d) for i, (p, d) in enumerate(
        [(0.80, 1.22), (0.75, 1.30), (0.72, 1.36), (0.70, 1.40), (0.68, 1.44), (0.66, 1.50),
         (0.74, 1.33), (0.78, 1.25), (0.69, 1.42), (0.67, 1.47), (0.71, 1.38), (0.73, 1.35)])]
    legs.append(Leg("m0", "second leg same match", 0.9, 1.10))
    legs.append(Leg("low", "below floor", 0.60, 1.9))
    slip = build_acca(legs, band=(11.0, 11.2), floor=0.65)
    assert slip is not None
    assert 11.0 <= slip["price_decimal"] <= 11.2
    assert all(l.model_prob >= 0.65 for l in slip["legs"])
    ids = [l.event_id for l in slip["legs"]]
    assert len(ids) == len(set(ids))
    assert slip["model_joint_prob"] == pytest.approx(math.prod(l.model_prob for l in slip["legs"]))
    assert slip["legs_below_floor_rejected"] == 1


def test_acca_is_optimal_against_brute_force():
    import itertools
    rng = np.random.default_rng(3)
    legs = [Leg(f"m{i}", "", float(p), float(round(0.93 / p, 2)))
            for i, p in enumerate(rng.uniform(0.65, 0.9, 11))]
    slip = build_acca(legs, band=(5.0, 5.3), floor=0.65)
    best = 0.0
    for r in range(2, len(legs) + 1):
        for combo in itertools.combinations(legs, r):
            price = math.prod(l.price_decimal for l in combo)
            if 5.0 <= price <= 5.3:
                best = max(best, math.prod(l.model_prob for l in combo))
    assert slip["model_joint_prob"] == pytest.approx(best, rel=1e-9)


def test_acca_returns_none_rather_than_lowering_floor():
    legs = [Leg("a", "", 0.9, 1.1), Leg("b", "", 0.6, 10.0)]
    assert build_acca(legs, band=(11.0, 11.2), floor=0.65) is None
