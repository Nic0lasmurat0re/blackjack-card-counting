import pytest

from bjsim import BASIC_FLAT, COUNTER_SPREAD, COUNTER_WONGING, BlackjackGame
from bjsim.cards import Card
from bjsim.game import BASE_EDGE, EDGE_PER_TRUE_COUNT, ROUND_VARIANCE
from bjsim.montecarlo import wilson_interval
from conftest import FILLER_COUNT, card, hilo_sum, stack_shoe


@pytest.fixture
def game():
    game = BlackjackGame(initial_bankroll=10000, seed=0)
    game.calculate_bet_size = lambda true_count, unit_bet=25: 10
    return game


# --- rounds -------------------------------------------------------------------

def test_draw_never_fails_after_cut_card(game):
    shoe = game.shoe
    shoe.cards = shoe.cards[:shoe.reshuffle_point - 5]
    remaining = shoe.cards_remaining()
    assert isinstance(shoe.draw(), Card)
    assert shoe.cards_remaining() == remaining - 1


def test_reshuffle_between_rounds_resets_count(game):
    shoe = game.shoe
    shoe.cards = shoe.cards[:shoe.reshuffle_point]
    game.running_count = 12
    game.play_round(unit_bet=10)
    assert game.running_count == -hilo_sum(shoe.cards)


def test_hole_card_counted(game):
    stack_shoe(game, ["10", "8", "9", "K"])
    assert game.play_round(unit_bet=10) == (-10, 10)
    assert game.running_count == -2


def test_dealer_does_not_draw_when_player_busts(game):
    stack_shoe(game, ["10", "6", "10", "4", "K"])
    game.get_optimal_action = lambda *args, **kwargs: "H"
    assert game.play_round(unit_bet=10) == (-10, 10)
    assert game.shoe.cards_remaining() == FILLER_COUNT


def test_eights_split_against_ten(game):
    stack_shoe(game, ["8", "8", "10", "7", "10", "10"])
    game.current_true_count = lambda: 1
    assert game.play_round(unit_bet=10) == (20, 20)


def test_split_aces_get_one_card(game):
    stack_shoe(game, ["A", "A", "6", "10", "5", "9"])
    assert game.play_round(unit_bet=10) == (20, 20)


def test_double_after_split(game):
    stack_shoe(game, ["8", "8", "6", "10", "3", "7", "2", "7"])
    assert game.play_round(unit_bet=10) == (40, 40)


def test_insurance_against_dealer_blackjack(game):
    stack_shoe(game, ["10", "9", "A", "K"])
    game.current_true_count = lambda: 4
    assert game.play_round(unit_bet=10) == (0, 15)


def test_insurance_lost_without_dealer_blackjack(game):
    stack_shoe(game, ["10", "9", "A", "7"])
    game.current_true_count = lambda: 4
    assert game.play_round(unit_bet=10) == (5, 15)


def test_basic_strategy_player_never_insures():
    game = BlackjackGame(BASIC_FLAT, seed=0)
    stack_shoe(game, ["10", "9", "A", "K"])
    game.current_true_count = lambda: 10
    assert game.play_round(unit_bet=10) == (-10, 10)


@pytest.mark.parametrize("player", [BASIC_FLAT, COUNTER_SPREAD, COUNTER_WONGING])
def test_count_matches_cards_seen_after_every_round(player):
    game = BlackjackGame(player, initial_bankroll=10**9, seed=3)
    for _ in range(3000):
        game.play_round(unit_bet=5)
        assert game.running_count == -hilo_sum(game.shoe.cards)


# --- betting ------------------------------------------------------------------

def test_ramp_applies_with_large_bankroll():
    game = BlackjackGame(initial_bankroll=10**9, seed=0)
    assert game.calculate_bet_size(5, unit_bet=5) == 80
    assert game.calculate_bet_size(9, unit_bet=5) == 80
    assert game.calculate_bet_size(2, unit_bet=5) == 20


def test_kelly_caps_small_bankroll():
    game = BlackjackGame(initial_bankroll=1500, seed=0)
    for true_count in (2, 3, 5, 8):
        bet = game.calculate_bet_size(true_count, unit_bet=5)
        kelly = 0.5 * game.bankroll * (BASE_EDGE + EDGE_PER_TRUE_COUNT * true_count) / ROUND_VARIANCE
        assert bet % 5 == 0
        assert bet <= max(5, kelly)


def test_minimum_bet_when_no_advantage():
    game = BlackjackGame(initial_bankroll=1500, seed=0)
    assert game.calculate_bet_size(-3, unit_bet=5) == 5


def test_flat_and_spread_players():
    flat = BlackjackGame(BASIC_FLAT, initial_bankroll=10**6, seed=0)
    spread = BlackjackGame(COUNTER_SPREAD, initial_bankroll=10**6, seed=0)
    assert [flat.calculate_bet_size(tc, 5) for tc in (-2, 0, 3, 6)] == [5, 5, 5, 5]
    assert [spread.calculate_bet_size(tc, 5) for tc in (-2, 0, 3, 6)] == [5, 5, 40, 80]
    assert flat.should_play_hand(-5) and spread.should_play_hand(-5)


def test_wong_thresholds_follow_bankroll():
    game = BlackjackGame(initial_bankroll=1000, seed=0)
    for bankroll, thresholds in ((1000, (1.5, 1)), (3500, (1, 0.5)), (7000, (0.5, -1))):
        game.bankroll = bankroll
        assert game.wong_thresholds() == thresholds


# --- simulation ---------------------------------------------------------------

def test_expected_value_uses_real_wagers():
    result = BlackjackGame(initial_bankroll=10**6, seed=1).simulate(20000, unit_bet=5)
    assert result.total_wagered >= 5 * result.rounds_played > 0
    assert result.expected_value == pytest.approx(result.net_gain / result.total_wagered)
    assert len(result.history) == 21


def test_ruin_stops_the_simulation():
    result = BlackjackGame(initial_bankroll=3, seed=0).simulate(10, unit_bet=5, record_every=1)
    assert result.ruined and result.rounds_played == 0
    assert result.history.tolist() == [3] * 11


def test_seed_is_reproducible():
    runs = [BlackjackGame(initial_bankroll=1500, seed=42).simulate(5000, unit_bet=5, record_every=10).history
            for _ in range(2)]
    assert runs[0].tolist() == runs[1].tolist()


def test_wilson_interval():
    low, high = wilson_interval(0, 100)
    assert low == 0 and high == pytest.approx(0.037, abs=1e-3)
    low, high = wilson_interval(50, 100)
    assert low == pytest.approx(0.404, abs=1e-3) and high == pytest.approx(0.596, abs=1e-3)
