import pytest

from bjsim import COUNTER_WONGING, BlackjackGame
from bjsim.strategy import BasicStrategy
from conftest import card

DEALER_VALUES = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

# Blackjack Apprenticeship charts, 4-8 decks, S17, DAS, no surrender. Columns: dealer 2 3 4 5 6 7 8 9 10 A
HARD = {
    5: "HHHHHHHHHH", 6: "HHHHHHHHHH", 7: "HHHHHHHHHH", 8: "HHHHHHHHHH",
    9: "HDDDDHHHHH", 10: "DDDDDDDDHH", 11: "DDDDDDDDDH", 12: "HHSSSHHHHH",
    13: "SSSSSHHHHH", 14: "SSSSSHHHHH", 15: "SSSSSHHHHH", 16: "SSSSSHHHHH",
    17: "SSSSSSSSSS", 18: "SSSSSSSSSS", 19: "SSSSSSSSSS",
}
SOFT_TWO_CARDS = {
    13: "HHHDDHHHHH", 14: "HHHDDHHHHH", 15: "HHDDDHHHHH", 16: "HHDDDHHHHH",
    17: "HDDDDHHHHH", 18: "SDDDDSSHHH", 19: "SSSSSSSSSS", 20: "SSSSSSSSSS",
}
SOFT_MULTI_CARDS = {
    13: "HHHHHHHHHH", 14: "HHHHHHHHHH", 15: "HHHHHHHHHH", 16: "HHHHHHHHHH",
    17: "HHHHHHHHHH", 18: "SSSSSSSHHH", 19: "SSSSSSSSSS", 20: "SSSSSSSSSS",
}
PAIRS = {
    11: "PPPPPPPPPP", 10: "SSSSSSSSSS", 9: "PPPPPSPPSS", 8: "PPPPPPPPPP",
    7: "PPPPPPHHHH", 6: "PPPPPHHHHH", 5: "DDDDDDDDHH", 4: "HHHPPHHHHH",
    3: "PPPPPPHHHH", 2: "PPPPPPHHHH",
}


def hard_hand(total):
    a = next(a for a in range(2, 10) if a < total - a <= 10)
    return [card(a), card(total - a)]


def soft_multi_hand(total):
    if total == 13:
        return [card(11), card(11), card(11)]
    if total == 14:
        return [card(11), card(11), card(2)]
    return [card(11), card(2), card(total - 13)]


def pair_decision(hand, dealer_value):
    if BasicStrategy.should_split(hand[0].blackjack_value, dealer_value):
        return "P"
    return BasicStrategy.get_action(hand, dealer_value)


CASES = [
    (chart, make_hand, decide, total, dealer, expected)
    for chart, make_hand, decide in [
        (HARD, hard_hand, BasicStrategy.get_action),
        (SOFT_TWO_CARDS, lambda t: [card(11), card(t - 11)], BasicStrategy.get_action),
        (SOFT_MULTI_CARDS, soft_multi_hand, BasicStrategy.get_action),
        (PAIRS, lambda v: [card(v), card(v)], pair_decision),
    ]
    for total, row in chart.items()
    for dealer, expected in zip(DEALER_VALUES, row)
]


@pytest.mark.parametrize("chart, make_hand, decide, total, dealer, expected", CASES,
                         ids=[f"{['hard', 'soft2', 'softN', 'pair'][[HARD, SOFT_TWO_CARDS, SOFT_MULTI_CARDS, PAIRS].index(c[0])]}"
                              f"-{c[3]}-vs{c[4]}" for c in CASES])
def test_basic_strategy_charts(chart, make_hand, decide, total, dealer, expected):
    assert decide(make_hand(total), dealer) == expected


def test_no_double_when_not_allowed():
    assert BasicStrategy.get_action([card(5), card(6)], 6, can_double=False) == "H"
    assert BasicStrategy.get_action([card(11), card(7)], 4, can_double=False) == "S"
    assert BasicStrategy.get_action([card(5), card(5)], 6, can_double=False) == "H"


def game_at(true_count, player=COUNTER_WONGING):
    game = BlackjackGame(player, seed=0)
    game.current_true_count = lambda: true_count
    return game


@pytest.mark.parametrize("hand, dealer, tc, expected", [
    ([10, 6], 10, 0, "S"), ([10, 6], 10, -0.5, "H"), ([10, 5], 10, 4, "S"), ([10, 2], 2, 3, "S"),
    ([6, 5], 11, 1, "D"), ([6, 4], 10, 4, "D"),
    ([10, 3], 2, 2, "S"), ([10, 3], 2, -1.5, "H"), ([10, 2], 4, -0.5, "H"), ([10, 2], 4, 0, "S"),
    ([10, 3], 3, -2.5, "H"),
])
def test_index_plays(hand, dealer, tc, expected):
    assert game_at(tc).get_optimal_action([card(v) for v in hand], card(dealer)) == expected


def test_index_double_needs_double_allowed():
    assert game_at(1).get_optimal_action([card(6), card(5)], card(11), can_double=False) == "H"


@pytest.mark.parametrize("pair, dealer, tc, expected", [
    (8, 10, 1, True), (6, 5, 1, True), (10, 6, 4, True), (10, 6, 3.9, False), (10, 5, 5, True), (10, 4, 10, False),
])
def test_split_decisions(pair, dealer, tc, expected):
    assert game_at(tc).should_split([card(pair), card(pair)], card(dealer)) == expected


def test_insurance_index():
    game = BlackjackGame(seed=0)
    assert game.deviations.take_insurance(3)
    assert not game.deviations.take_insurance(2.9)
