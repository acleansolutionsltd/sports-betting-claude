import numpy as np
import pandas as pd
import pytest

from betting_model.analysis.errors import calibration_slope
from betting_model.backtest import metrics as mx
from betting_model.tracker import tracker as t


def _leg(bet_id, slip, leg_no, price=1.5, p=0.7, **kw):
    return {"bet_id": bet_id, "placed_at_utc": "2026-11-08T13:55:00Z", "sport": "Football", "league": "Serie A",
            "event": "Inter v Como", "event_id": "I1|2026-11-08|Inter|Como",
            "event_start_utc": "2026-11-08T17:00:00+00:00", "market": "BTTS", "selection": "Yes",
            "market_key": "btts:yes", "bookmaker": "bet365", "price_decimal": price,
            "price_source_and_time": "bet365 app 13:50 GMT", "model_prob": p, "slip_id": slip,
            "leg_no": leg_no, "stake_units": 1, **kw}


def test_tracker_append_only_and_tamper_evident(tmp_path):
    bets, results = tmp_path / "bets.csv", tmp_path / "results.csv"
    t.append_bets([_leg("a1", "s1", 1), _leg("a2", "s1", 2, price=1.4)], bets)
    t.append_bets([_leg("b1", "s2", 1, price=2.0, price_source_and_time="matchesnow 13:00 GMT (third-party)")], bets)
    with pytest.raises(ValueError):
        t.append_bets([_leg("a1", "s9", 1)], bets)            # no replacing a recorded bet
    with pytest.raises(ValueError):
        t.append_bets([{**_leg("c1", "s3", 1), "model_prob": ""}], bets)  # incomplete rows refused
    assert t.verify(bets) == []
    df = pd.read_csv(bets)
    assert df.implied_prob.iloc[0] == pytest.approx(0.6667)
    assert "third_party_price" in df["flags"].iloc[2]
    late = _leg("d1", "s4", 1, placed_at_utc="2026-11-08T18:00:00Z")
    t.append_bets([late], bets)
    assert "recorded_after_start" in pd.read_csv(bets)["flags"].iloc[3]

    t.record_result("a1", "win", "test", bets_path=bets, results_path=results)
    t.record_result("a2", "win", "test", bets_path=bets, results_path=results)
    t.record_result("b1", "loss", "test", bets_path=bets, results_path=results)
    with pytest.raises(ValueError):
        t.record_result("b1", "win", "test", bets_path=bets, results_path=results)  # silent regrade refused
    slips, _ = t.slips(t.load(bets, results))
    s = slips.set_index("slip_id")
    assert s.loc["s1", "net_units"] == pytest.approx(1.5 * 1.4 - 1)
    assert s.loc["s2", "net_units"] == -1                     # the loss stays in the record
    assert s.loc["s4", "result"] == "open"
    assert "hash chain intact" in t.report(bets, results)

    text = bets.read_text().replace("0.7,", "0.9,", 1)        # edit a stored probability
    bets.write_text(text)
    assert t.verify(bets)


def test_void_leg_drops_out_of_acca(tmp_path):
    bets, results = tmp_path / "bets.csv", tmp_path / "results.csv"
    t.append_bets([_leg("a1", "s1", 1, price=1.5), _leg("a2", "s1", 2, price=2.0)], bets)
    t.record_result("a1", "void", "test", bets_path=bets, results_path=results)
    t.record_result("a2", "win", "test", bets_path=bets, results_path=results)
    slips, _ = t.slips(t.load(bets, results))
    assert slips.net_units.iloc[0] == pytest.approx(1.0)


def test_metrics():
    assert mx.max_drawdown([1, -1, -1, 2, -3]) == 3
    assert mx.longest_losing_run(["win", "loss", "loss", "void", "loss", "win"]) == 3
    assert mx.log_loss([0.5, 0.5], [1, 0]) == pytest.approx(np.log(2))
    tab = mx.calibration_table([0.66, 0.68, 0.72, 0.99], [1, 0, 1, 1], lo=0.65)
    assert list(tab.index) == ["65%-70%", "70%-75%", "95%-100%"]
    assert tab.loc["65%-70%", "hit_rate"] == 0.5
    s = mx.bet_summary(pd.DataFrame({"result": ["win", "loss", "void"], "net_units": [0.5, -1, 0],
                                     "stake_units": [1, 1, 1]}))
    assert s["bets"] == 3 and s["win_rate"] == 0.5 and s["roi"] == pytest.approx(-0.1667, abs=1e-4)


def test_calibration_slope_detects_overconfidence():
    rng = np.random.default_rng(0)
    true = rng.uniform(0.5, 0.9, 40_000)
    y = rng.random(40_000) < true
    a, b = calibration_slope(true, y)
    assert abs(a) < 0.06 and b == pytest.approx(1.0, abs=0.06)
    logit = np.log(true / (1 - true)) * 1.5                   # stated probabilities too extreme
    _, b2 = calibration_slope(1 / (1 + np.exp(-logit)), y)
    assert b2 < 0.8
