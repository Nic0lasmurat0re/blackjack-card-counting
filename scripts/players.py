"""Three players, the same table and bankroll: Monte Carlo distribution of outcomes.

Each player starts with 1,500 (300 table minimums of 5) and plays up to 100,000
rounds, about 1,000 hours at 100 rounds an hour, or until ruin.
"""

import numpy as np

from bjsim import BASIC_FLAT, COUNTER_SPREAD, COUNTER_WONGING
from bjsim.montecarlo import run_players, wilson_interval
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from style import COLORS, INK_2, plt, save

PLAYERS = [BASIC_FLAT, COUNTER_SPREAD, COUNTER_WONGING]
N_PLAYERS, N_ROUNDS, BANKROLL, UNIT = 500, 100_000, 1500, 5
RECORD_EVERY = 1000


def main():
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), sharey=True)
    rounds = np.arange(0, N_ROUNDS + 1, RECORD_EVERY) / 1000

    print(f"{N_PLAYERS} players each, bankroll {BANKROLL}, table minimum {UNIT}, up to {N_ROUNDS:,} rounds\n")
    print(f"{'player':<28} {'edge on wagers':>14} {'median final':>12} {'P(gain)':>8} {'risk of ruin (95 % CI)':>24}")
    for player, color, ax in zip(PLAYERS, COLORS, axes):
        results = run_players(player, N_PLAYERS, N_ROUNDS, BANKROLL, UNIT, seed=0, record_every=RECORD_EVERY)
        paths = np.array([r.history for r in results])
        finals = paths[:, -1]
        ruined = sum(r.ruined for r in results)
        low, high = wilson_interval(ruined, N_PLAYERS)
        edge = sum(r.net_gain for r in results) / sum(r.total_wagered for r in results)
        print(f"{player.name:<28} {edge:>+14.2%} {np.median(finals):>12,.0f} {np.mean(finals > BANKROLL):>8.0%} "
              f"{ruined / N_PLAYERS:>9.1%} [{low:.1%}, {high:.1%}]")

        q5, q25, q50, q75, q95 = np.percentile(paths, [5, 25, 50, 75, 95], axis=0)
        ax.fill_between(rounds, q5, q95, color=color, alpha=0.15, linewidth=0)
        ax.fill_between(rounds, q25, q75, color=color, alpha=0.35, linewidth=0)
        ax.plot(rounds, q50, color=color)
        ax.axhline(BANKROLL, color=INK_2, linewidth=1, linestyle=":")
        ax.set_title(player.name)
        ax.set_xlabel("rounds (thousands)")
        ax.text(0.03, 0.97, f"risk of ruin {ruined / N_PLAYERS:.1%}\nedge on wagers {edge:+.2%}",
                transform=ax.transAxes, va="top", color=INK_2, fontsize=9.5)
    axes[0].set_ylabel("bankroll")
    axes[0].set_yscale("symlog", linthresh=1000)
    axes[0].set_ylim(0, None)
    grey = "#8a8984"
    fig.legend(handles=[Line2D([], [], color=grey, label="median"),
                        Patch(color=grey, alpha=0.6, label="25th-75th percentile"),
                        Patch(color=grey, alpha=0.25, label="5th-95th percentile"),
                        Line2D([], [], color=INK_2, linewidth=1, linestyle=":", label="starting bankroll")],
               loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle(f"{N_PLAYERS} simulated players per strategy, starting bankroll {BANKROLL:,} at a {UNIT} table", fontsize=11, color=INK_2)
    save(fig, "players.png")


if __name__ == "__main__":
    main()
