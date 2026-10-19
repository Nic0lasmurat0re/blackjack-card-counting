import random
from collections import Counter

import pytest

from bjsim.cards import VALUES, Card, Shoe


def test_card_values():
    assert [Card("♠", v).blackjack_value for v in VALUES] == [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]
    assert [Card("♠", v).count_value for v in VALUES] == [1, 1, 1, 1, 1, 0, 0, 0, -1, -1, -1, -1, -1]


def test_invalid_value():
    with pytest.raises(ValueError):
        Card("♠", "X")


def test_shoe_composition_is_balanced():
    shoe = Shoe(num_decks=6)
    assert shoe.cards_remaining() == 312
    counts = Counter((c.suit, c.value) for c in shoe.cards)
    assert len(counts) == 52 and all(n == 6 for n in counts.values())
    assert sum(c.count_value for c in shoe.cards) == 0  # a full shoe is balanced in Hi-Lo


def test_draw_until_empty():
    shoe = Shoe(num_decks=1)
    drawn = [shoe.draw() for _ in range(52)]
    assert len({(c.suit, c.value) for c in drawn}) == 52
    with pytest.raises(RuntimeError):
        shoe.draw()


def test_shuffle_is_reproducible():
    first = [repr(c) for c in Shoe(rng=random.Random(42)).cards]
    second = [repr(c) for c in Shoe(rng=random.Random(42)).cards]
    assert first == second


def test_cut_card():
    shoe = Shoe(num_decks=6)
    assert shoe.reshuffle_point == 53
    while shoe.cards_remaining() > 54:
        shoe.draw()
    assert not shoe.needs_shuffle()
    shoe.draw()
    assert shoe.needs_shuffle()


def test_decks_remaining_has_a_floor():
    shoe = Shoe(num_decks=6)
    for _ in range(26):
        shoe.draw()
    assert shoe.decks_remaining() == 5.5
    shoe.cards = shoe.cards[:10]
    assert shoe.decks_remaining() == 0.5
