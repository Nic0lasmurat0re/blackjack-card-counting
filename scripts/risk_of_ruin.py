"""Risk of ruin against starting bankroll, and against the fraction of Kelly bet."""

from dataclasses import replace

import numpy as np

from bjsim import COUNTER_SPREAD, COUNTER_WONGING
from bjsim.montecarlo import run_players, wilson_interval
from style import COLORS, INK_2, plt, save

N_PLAYERS, N_ROUNDS, UNIT = 300, 100_000, 5
BANKROLL_UNITS = [50, 100, 200, 400, 800, 1600]
KELLY_FRACTIONS = [0.25, 0.5, 1, 1.5, 2, 3, 4]
KELLY_BANKROLL = 300  # 60 table minimums: small enough that ruin is possible


def ruin_curve(player, bankroll):
    results = run_players(player, N_PLAYERS, N_ROUNDS, bankroll, UNIT, seed=10_000, record_every=N_ROUNDS)
    ruined = sum(r.ruined for r in results)
    return ruined / N_PLAYERS, *wilson_interval(ruined, N_PLAYERS), np.median([r.final_bankroll for r in results])


def main():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6))

    print("Risk of ruin by starting bankroll (in table minimums)")
    for player, color in [(COUNTER_SPREAD, COLORS[1]), (COUNTER_WONGING, COLORS[2])]:
        rows = [ruin_curve(player, units * UNIT) for units in BANKROLL_UNITS]
        for units, (p, low, high, _) in zip(BANKROLL_UNITS, rows):
            print(f"  {player.name:<28} {units:>5} units: {p:6.1%} [{low:.1%}, {high:.1%}]")
        p, low, high, _ = np.array(rows).T
        ax1.fill_between(BANKROLL_UNITS, 100 * low, 100 * high, color=color, alpha=0.2, linewidth=0)
        ax1.plot(BANKROLL_UNITS, 100 * p, "o-", color=color, label=player.name)
    ax1.set_xscale("log")
    ax1.set_xticks(BANKROLL_UNITS, [str(u) for u in BANKROLL_UNITS])
    ax1.set_xlabel("starting bankroll (table minimums)")
    ax1.set_ylabel("risk of ruin within 100,000 rounds (%)")
    ax1.set_title("Risk of ruin falls with bankroll")
    ax1.legend(loc="upper right")

    print(f"\nWonging player, bankroll {KELLY_BANKROLL}: Kelly fraction")
    rows = [ruin_curve(replace(COUNTER_WONGING, kelly_fraction=k), KELLY_BANKROLL) for k in KELLY_FRACTIONS]
    for k, (p, low, high, median) in zip(KELLY_FRACTIONS, rows):
        print(f"  {k:>4} x Kelly: ruin {p:6.1%} [{low:.1%}, {high:.1%}], median final bankroll {median:8,.0f}")
    p, low, high, median = np.array(rows).T
    ax2.fill_between(KELLY_FRACTIONS, 100 * low, 100 * high, color=COLORS[2], alpha=0.2, linewidth=0)
    ax2.plot(KELLY_FRACTIONS, 100 * p, "o-", color=COLORS[2])
    ax2.set_xlabel("bet cap (fraction of the Kelly bet)")
    ax2.set_ylabel("risk of ruin (%)")
    ax2.set_title(f"Hi-Lo, wonging: over-betting Kelly ({KELLY_BANKROLL // UNIT} minimums)")
    ax2.axvline(2, color=INK_2, linewidth=1, linestyle=":")
    ax2.text(2.05, 3, "2 × Kelly: expected\ngrowth turns negative", color=INK_2, fontsize=9)
    ax2.set_ylim(0, 100)
    save(fig, "risk_of_ruin.png")


if __name__ == "__main__":
    main()
