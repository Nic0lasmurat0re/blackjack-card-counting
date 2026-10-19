"""Player edge as a function of the Hi-Lo true count, on flat one-unit bets.

Every round is played (no wonging), with basic strategy, the Illustrious 18 and
insurance. The linear fit gives the edge model used to size Kelly bets.
"""

import numpy as np

from bjsim.montecarlo import flat_bet_outcomes
from style import INK, INK_2, plt, save

N_ROUNDS = 10_000_000
COUNTS = np.arange(-4, 7)


def main():
    tc, result = flat_bet_outcomes(N_ROUNDS, seed=1000)
    n = len(result)
    print(f"{n:,} rounds: edge {result.mean():+.3%} ± {1.96 * result.std() / np.sqrt(n):.3%} (95 %), "
          f"variance {result.var():.3f}")

    keep = np.abs(tc) < 10  # the last cards of a shoe give extreme, rare counts
    slope, intercept = np.polyfit(tc[keep], result[keep], 1)
    print(f"linear fit: edge = {intercept:+.4f} {slope:+.4f} x TC  ->  break-even at TC = {-intercept / slope:+.2f}")

    rounded = np.round(tc)
    means, halfwidths, shares = [], [], []
    print(f"{'TC':>4} {'share':>7} {'edge':>8} {'95 % CI':>9}")
    for c in COUNTS:
        r = result[rounded == c]
        means.append(r.mean())
        halfwidths.append(1.96 * r.std() / np.sqrt(len(r)))
        shares.append(len(r) / n)
        print(f"{c:>+4d} {shares[-1]:>7.1%} {means[-1]:>+8.2%} {halfwidths[-1]:>8.2%}")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.5, 6.5), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
    ax1.axhline(0, color=INK_2, linewidth=1)
    x = np.linspace(COUNTS[0], COUNTS[-1], 100)
    ax1.plot(x, 100 * (intercept + slope * x), color="#2a78d6", linewidth=1.5, linestyle="--",
             label=f"fit: {100 * intercept:+.2f} % {100 * slope:+.2f} % × TC")
    ax1.errorbar(COUNTS, 100 * np.array(means), yerr=100 * np.array(halfwidths), fmt="o", color=INK,
                 capsize=4, markersize=7, label="measured, with 95 % interval")
    ax1.set_ylabel("player edge (% of the bet)")
    ax1.set_title(f"Edge by true count, {n / 1e6:.0f} million rounds, 6 decks, S17")
    ax1.legend(loc="upper left")

    ax2.bar(COUNTS, 100 * np.array(shares), color="#c3c2b7", width=0.7)
    ax2.set_ylabel("% of rounds")
    ax2.set_xlabel("true count (rounded)")
    ax2.set_xticks(COUNTS)
    ax2.grid(axis="x", visible=False)
    save(fig, "edge_by_count.png")


if __name__ == "__main__":
    main()
