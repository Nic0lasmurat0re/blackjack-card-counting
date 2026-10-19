"""Run many independent players in parallel, and the statistics used on the results."""

import math
from multiprocessing import Pool

import numpy as np

from .game import BlackjackGame, Player


def _play(args):
    player, seed, n_rounds, bankroll, unit_bet, record_every = args
    game = BlackjackGame(player, initial_bankroll=bankroll, seed=seed)
    return game.simulate(n_rounds, unit_bet, record_every)


def run_players(player, n_players, n_rounds, bankroll, unit_bet, seed=0, record_every=1000, processes=None):
    """Simulate n_players independent players (seeds seed, seed+1, ...). Returns a list of Results."""
    jobs = [(player, seed + i, n_rounds, bankroll, unit_bet, record_every) for i in range(n_players)]
    with Pool(processes) as pool:
        return pool.map(_play, jobs, chunksize=max(1, n_players // 64))


def _flat_bet(args):
    seed, n_rounds = args
    flat = Player("flat bet, every round, index plays", ramp=None, wonging=False, kelly_fraction=None)
    game = BlackjackGame(flat, initial_bankroll=float("inf"), seed=seed)
    counts, results = np.empty(n_rounds), np.empty(n_rounds)
    for i in range(n_rounds):
        results[i] = game.play_round(unit_bet=1)[0]
        counts[i] = game.last_true_count
    return counts, results


def flat_bet_outcomes(n_rounds, seed=0, chunks=64, processes=None):
    """True count before each round and net result of a one-unit bet, over n_rounds rounds."""
    per_chunk = n_rounds // chunks
    with Pool(processes) as pool:
        parts = pool.map(_flat_bet, [(seed + i, per_chunk) for i in range(chunks)])
    return np.concatenate([p[0] for p in parts]), np.concatenate([p[1] for p in parts])


def wilson_interval(successes, n, z=1.96):
    """95 % Wilson score interval for a proportion."""
    if n == 0:
        return 0.0, 1.0
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)
