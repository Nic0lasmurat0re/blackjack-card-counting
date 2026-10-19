"""Shared figure style: one color per player profile, the same in every figure."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIGURES = Path(__file__).resolve().parent.parent / "figures"
FIGURES.mkdir(exist_ok=True)

COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]  # basic flat, Hi-Lo spread, Hi-Lo wonging
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": INK_2,
    "axes.labelcolor": INK,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "legend.frameon": False,
    "lines.linewidth": 2,
    "lines.markersize": 6,
    "font.size": 10,
})


def save(fig, name):
    path = FIGURES / name
    fig.savefig(path, dpi=160, bbox_inches="tight")
    print(f"saved {path.relative_to(FIGURES.parent)}")
