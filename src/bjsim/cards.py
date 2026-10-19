"""Cards and the shoe."""

import random

SUITS = ["♠", "♥", "♦", "♣"]
VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]


class Card:
    __slots__ = ("suit", "value", "blackjack_value", "count_value")

    def __init__(self, suit, value):
        if value not in VALUES:
            raise ValueError(f"unknown card value {value!r}")
        self.suit = suit
        self.value = value
        # blackjack value (ace = 11), computed once
        if value == "A":
            self.blackjack_value = 11
        elif value in ("J", "Q", "K"):
            self.blackjack_value = 10
        else:
            self.blackjack_value = int(value)
        # Hi-Lo tag: +1 for 2-6, 0 for 7-9, -1 for tens and aces
        self.count_value = 1 if self.blackjack_value <= 6 else -1 if self.blackjack_value >= 10 else 0

    def __repr__(self):
        return f"{self.value}{self.suit}"


class Shoe:
    """A multi-deck shoe with a cut card placed at ``penetration``."""

    def __init__(self, num_decks=6, penetration=0.83, rng=None):
        self.rng = rng or random.Random()
        self.penetration = penetration
        # ordered decks, reused at every shuffle
        self.all_cards = [Card(suit, value) for _ in range(num_decks) for suit in SUITS for value in VALUES]
        self.reset()

    def reset(self):
        """New shuffled shoe."""
        self.cards = self.all_cards.copy()
        self.rng.shuffle(self.cards)
        # the shoe is reshuffled once this many cards or fewer remain
        self.reshuffle_point = int(len(self.cards) * (1 - self.penetration))

    def draw(self):
        """Draw a card. The shoe is never reshuffled in the middle of a round: the
        round in progress ends past the cut card and the reshuffle happens before
        the next one."""
        if not self.cards:
            raise RuntimeError("shoe empty during a round")
        return self.cards.pop()

    def cards_remaining(self):
        return len(self.cards)

    def decks_remaining(self):
        return max(0.5, self.cards_remaining() / 52.0)

    def needs_shuffle(self):
        """True once the cut card is out (checked between rounds)."""
        return len(self.cards) <= self.reshuffle_point
