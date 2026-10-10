#!/usr/bin/env python3
"""Price a player prop and compare it with the book.

Count stats (shots, shots on target, tackles, receptions, goals/TDs):
  python3 tools/props/prop_calc.py --line 2.5 --over -120 --under -105 \\
      --per90 3.23 --minutes 84 --samples 2,4,4,2,3 --opp-adj 1.10

Yardage stats (passing / rushing / receiving yards) use a normal model:
  python3 tools/props/prop_calc.py --line 74.5 --over -115 --under -115 \\
      --mean 88.2 --sd 51 --dist normal --opp-adj 0.95

Anytime scorer (one-sided market, no under price):
  python3 tools/props/prop_calc.py --line 0.5 --over +150 --mean 0.62

--prior / --games shrink a small recent sample toward a longer-run mean
(last season, career, or position average): with 4 games and the default
--prior-games 6, the projection is 40% recent and 60% prior.

--opp-adj multiplies the projected mean (e.g. 1.10 = opponent concedes 10%
more of this stat than league average). --samples fits over-dispersion
(negative binomial) when the game log is more volatile than Poisson.
"""
import argparse
import sys

from _common import (count_p_over, decimal_to_american, mean_var,
                     normal_p_over, parse_odds)

EDGE_THRESHOLD = 0.02
KELLY_FRACTION = 0.25


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--line", type=float, required=True)
    ap.add_argument("--over", required=True, help="over odds: +120, -150, 2.2 or 6/5")
    ap.add_argument("--under", help="under odds (omit for one-sided markets)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--mean", type=float, help="projected stat for this game")
    src.add_argument("--per90", type=float, help="rate per 90 minutes (football)")
    ap.add_argument("--minutes", type=float, default=90, help="expected minutes (with --per90)")
    ap.add_argument("--prior", type=float, help="longer-run mean to shrink toward (same units as --mean/--per90)")
    ap.add_argument("--games", type=int, help="games in the recent sample (needed with --prior)")
    ap.add_argument("--prior-games", type=float, default=6, help="weight of the prior, in games")
    ap.add_argument("--opp-adj", type=float, default=1.0)
    ap.add_argument("--dist", choices=["count", "normal"], default="count")
    ap.add_argument("--sd", type=float, help="standard deviation (normal model)")
    ap.add_argument("--samples", help="comma-separated recent game values, used to fit dispersion")
    args = ap.parse_args()

    rate = args.mean if args.mean is not None else args.per90
    if args.prior is not None:
        if not args.games:
            sys.exit("--prior needs --games (size of the recent sample)")
        rate = (args.games * rate + args.prior_games * args.prior) / (args.games + args.prior_games)
    base = rate if args.mean is not None else rate * args.minutes / 90
    mean = base * args.opp_adj

    if args.dist == "normal":
        if not args.sd:
            sys.exit("--dist normal needs --sd")
        p_over = normal_p_over(args.line, mean, args.sd * args.opp_adj)
        model = f"normal(mean={mean:.1f}, sd={args.sd * args.opp_adj:.1f})"
    else:
        if args.line != int(args.line) + 0.5:
            sys.exit("count props need a half-point line (0.5, 1.5, 2.5 ...)")
        var = None
        if args.samples:
            values = [float(x) for x in args.samples.split(",")]
            m, v = mean_var(values)
            if m > 0 and v > m * 1.05:
                var = mean * (v / m)  # keep the observed variance-to-mean ratio
        p_over = count_p_over(args.line, mean, var)
        model = (f"negative binomial(mean={mean:.2f}, var={var:.2f})" if var
                 else f"Poisson(mean={mean:.2f})")
    p_under = 1 - p_over

    over_dec = parse_odds(args.over)
    imp_over = 1 / over_dec
    if args.under:
        under_dec = parse_odds(args.under)
        imp_under = 1 / under_dec
        book = imp_over + imp_under
        fair_over, fair_under = imp_over / book, imp_under / book
        margin = f"{(book - 1) * 100:.1f}%"
    else:
        under_dec, fair_under = None, None
        fair_over = imp_over / 1.07  # one-sided markets: assume ~7% margin
        margin = "~7% (assumed, one-sided market)"

    if args.prior is not None:
        print(f"Shrunk toward prior {args.prior} ({args.games} recent games vs {args.prior_games:g} prior games)")
    print(f"Model: {model}")
    print(f"Book margin: {margin}\n")
    print(f"{'side':6}{'model P':>9}{'fair odds':>11}{'book odds':>11}{'market P':>10}{'edge':>8}{'EV':>8}{'¼ Kelly':>9}")
    best = None
    for side, p, dec, fair in (("over", p_over, over_dec, fair_over),
                               ("under", p_under, under_dec, fair_under)):
        if dec is None:
            continue
        edge = p - fair
        ev = p * dec - 1
        kelly = max(0.0, (p * dec - 1) / (dec - 1)) * KELLY_FRACTION
        print(f"{side:6}{p:>9.1%}{decimal_to_american(1 / p) if 0 < p < 1 else '-':>11}"
              f"{decimal_to_american(dec):>11}{fair:>10.1%}{edge:>+8.1%}{ev:>+8.1%}{kelly:>9.2%}")
        if edge >= EDGE_THRESHOLD and ev > 0 and (best is None or ev > best[2]):
            best = (side, edge, ev, kelly)

    print()
    if best:
        side, edge, ev, kelly = best
        print(f"CANDIDATE: {side.upper()} {args.line} — edge {edge:+.1%}, EV {ev:+.1%}, "
              f"stake {kelly:.2%} of bankroll (≈ {kelly / 0.02:.1f} units at 2%/unit) before tier caps")
    else:
        print(f"PASS — no side clears the {EDGE_THRESHOLD:.0%} edge threshold")


if __name__ == "__main__":
    main()
