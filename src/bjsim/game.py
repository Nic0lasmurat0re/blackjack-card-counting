"""The game engine: one player against the dealer, with Hi-Lo counting."""

import random
from dataclasses import dataclass, field

import numpy as np

from .cards import Shoe
from .strategy import BasicStrategy, Illustrious18, hand_value, is_blackjack

# Player edge as a function of the true count, and variance of one round, measured
# with this engine on 10 million flat-bet rounds (scripts/edge_by_count.py).
BASE_EDGE = -0.0034
EDGE_PER_TRUE_COUNT = 0.0053
ROUND_VARIANCE = 1.32

# bet in units by true count rounded and clipped to the keys
DEFAULT_RAMP = {0: 1, 1: 2, 2: 4, 3: 8, 4: 12, 5: 16}


@dataclass(frozen=True)
class Player:
    """How the player plays and bets."""

    name: str
    deviations: bool = True  # Illustrious 18 index plays and insurance
    ramp: dict | None = field(default_factory=lambda: DEFAULT_RAMP)  # None: flat bet of one unit
    wonging: bool = True  # sit out rounds when the count is low
    kelly_fraction: float | None = 0.5  # cap each bet at this fraction of the Kelly bet; None: no cap


BASIC_FLAT = Player("Basic strategy, flat bet", deviations=False, ramp=None, wonging=False, kelly_fraction=None)
COUNTER_SPREAD = Player("Hi-Lo, 1-16 spread", wonging=False, kelly_fraction=None)
COUNTER_WONGING = Player("Hi-Lo, wonging, half Kelly")


@dataclass
class Result:
    initial_bankroll: float
    final_bankroll: float
    min_bankroll: float
    rounds_observed: int
    rounds_played: int
    total_wagered: float
    ruined: bool  # the bankroll fell below the table minimum
    history: np.ndarray  # bankroll every `record_every` rounds, starting with the initial one

    @property
    def net_gain(self):
        return self.final_bankroll - self.initial_bankroll

    @property
    def expected_value(self):
        """Net gain per unit of money wagered."""
        return self.net_gain / self.total_wagered if self.total_wagered else 0.0


class BlackjackGame:
    def __init__(self, player=COUNTER_WONGING, num_decks=6, initial_bankroll=10000, seed=None):
        # an integer seed makes the simulation reproducible
        self.player = player
        self.rng = random.Random(seed)
        self.shoe = Shoe(num_decks, rng=self.rng)
        self.running_count = 0
        self.deviations = Illustrious18()

        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll

        self.dealer_hits_soft_17 = False  # the basic strategy charts used are those for S17
        self.blackjack_pays = 1.5
        self.can_double_after_split = True

        self.currently_playing = False
        self.last_true_count = 0.0  # true count at the start of the last round
        self.round_exposure = 0  # money committed in the current round (bet, insurance, split, double)
        self.rounds_played = 0
        self.total_wagered = 0

    # --- counting -------------------------------------------------------------

    def current_true_count(self):
        return round(self.running_count / self.shoe.decks_remaining(), 2)

    def deal_card(self):
        """Draw a visible card and count it."""
        card = self.shoe.draw()
        self.running_count += card.count_value
        return card

    # --- betting --------------------------------------------------------------

    def wong_thresholds(self):
        """(entry, exit) true counts for wonging, looser as the bankroll grows."""
        if self.bankroll < 3 * self.initial_bankroll:
            return 1.5, 1
        if self.bankroll < 6 * self.initial_bankroll:
            return 1, 0.5
        return 0.5, -1

    def should_play_hand(self, true_count):
        if not self.player.wonging:
            return True
        wong_in, wong_out = self.wong_thresholds()
        self.currently_playing = true_count >= (wong_out if self.currently_playing else wong_in)
        return self.currently_playing

    def calculate_bet_size(self, true_count, unit_bet=25):
        ramp = self.player.ramp
        if ramp is None:
            return unit_bet
        bet_amount = ramp[min(max(round(true_count), min(ramp)), max(ramp))] * unit_bet

        if self.player.kelly_fraction is not None:
            # Kelly bet: fraction of the bankroll equal to edge / variance
            advantage = BASE_EDGE + EDGE_PER_TRUE_COUNT * true_count
            kelly_bet = self.player.kelly_fraction * self.bankroll * advantage / ROUND_VARIANCE
            bet_amount = min(bet_amount, kelly_bet)

        # whole multiples of the unit (the table minimum), within the bankroll
        bet_amount = max(unit_bet, (bet_amount // unit_bet) * unit_bet)
        return min(bet_amount, (self.bankroll // unit_bet) * unit_bet)

    # --- playing --------------------------------------------------------------

    def observe_round(self):
        """Watch a round without playing: 4 to 7 cards are seen and counted."""
        for _ in range(self.rng.randint(4, 7)):
            self.deal_card()

    def should_split(self, player_hand, dealer_upcard):
        pair_value = player_hand[0].blackjack_value
        if pair_value != player_hand[1].blackjack_value:
            return False
        if pair_value == 10:
            return self.player.deviations and self.deviations.should_split_tens(
                dealer_upcard.blackjack_value, self.current_true_count())
        return BasicStrategy.should_split(pair_value, dealer_upcard.blackjack_value)

    def get_optimal_action(self, player_hand, dealer_upcard, can_double=True):
        """Action on a hand that is not split: index play if one applies, else basic strategy."""
        dealer_value = dealer_upcard.blackjack_value
        if self.player.deviations:
            total, soft = hand_value(player_hand)
            deviation = self.deviations.get_deviation(total, dealer_value, soft, self.current_true_count(), can_double)
            if deviation:
                return deviation
        return BasicStrategy.get_action(player_hand, dealer_value, can_double)

    def play_hand(self, hand, dealer_upcard, bet, is_split=False):
        """Play one hand (splits are handled by play_round). Returns (final total, final bet)."""
        # a split ace receives one card only
        if is_split and hand[0].value == "A":
            return hand_value(hand)[0], bet

        while True:
            total, _ = hand_value(hand)
            if total >= 21:
                break
            can_double = (len(hand) == 2
                          and (not is_split or self.can_double_after_split)
                          and self.bankroll >= self.round_exposure + bet)
            action = self.get_optimal_action(hand, dealer_upcard, can_double)
            if action == "S":
                break
            hand.append(self.deal_card())
            if action == "D":
                self.round_exposure += bet
                bet *= 2
                break

        return hand_value(hand)[0], bet

    def play_dealer_hand(self, hand):
        """The dealer draws to 17 (and on soft 17 if dealer_hits_soft_17). Returns the total."""
        while True:
            total, soft = hand_value(hand)
            if total > 17 or (total == 17 and not (soft and self.dealer_hits_soft_17)):
                return total
            hand.append(self.deal_card())

    def play_round(self, unit_bet=25):
        """Play one round. Returns (net result, amount wagered), or (None, 0) when sitting it out."""
        # reshuffle only between rounds, once the cut card is out
        if self.shoe.needs_shuffle():
            self.shoe.reset()
            self.running_count = 0
            self.currently_playing = False

        true_count = self.last_true_count = self.current_true_count()
        if not self.should_play_hand(true_count):
            self.observe_round()
            return None, 0

        bet = self.calculate_bet_size(true_count, unit_bet)
        self.round_exposure = bet

        # the dealer's hole card is counted only at the end of the round, once revealed
        player_hand = [self.deal_card(), self.deal_card()]
        dealer_upcard = self.deal_card()
        hole_card = self.shoe.draw()
        dealer_hand = [dealer_upcard, hole_card]

        player_blackjack = is_blackjack(player_hand)
        dealer_blackjack = is_blackjack(dealer_hand)

        # insurance (Illustrious 18): against an ace at TC >= +3, pays 2 to 1
        insurance = 0
        if (self.player.deviations
                and dealer_upcard.value == "A"
                and self.bankroll >= self.round_exposure + bet / 2
                and self.deviations.take_insurance(self.current_true_count())):
            insurance = bet / 2
            self.round_exposure += insurance
        net_result = 2 * insurance if dealer_blackjack else -insurance

        if dealer_blackjack:
            hand_results = [(0 if player_blackjack else -bet, bet)]
        elif player_blackjack:
            hand_results = [(bet * self.blackjack_pays, bet)]
        else:
            # play the hand, or both hands after a split (no re-split)
            if self.bankroll >= self.round_exposure + bet and self.should_split(player_hand, dealer_upcard):
                self.round_exposure += bet
                player_hands = [self.play_hand([card, self.deal_card()], dealer_upcard, bet, is_split=True)
                                for card in player_hand]
            else:
                player_hands = [self.play_hand(player_hand, dealer_upcard, bet)]

            # the dealer does not draw when every player hand has busted
            if any(total <= 21 for total, _ in player_hands):
                dealer_total = self.play_dealer_hand(dealer_hand)
            else:
                dealer_total = 0

            hand_results = []
            for total, hand_bet in player_hands:
                if total > 21 or total < dealer_total <= 21:
                    hand_results.append((-hand_bet, hand_bet))
                elif total == dealer_total:
                    hand_results.append((0, hand_bet))
                else:
                    hand_results.append((hand_bet, hand_bet))

        self.running_count += hole_card.count_value

        net_result += sum(result for result, _ in hand_results)
        wagered = insurance + sum(hand_bet for _, hand_bet in hand_results)
        return net_result, wagered

    # --- simulation -----------------------------------------------------------

    def simulate(self, num_rounds, unit_bet=5, record_every=1000):
        """Play up to num_rounds rounds (observed or played), stopping at ruin.

        Ruin means the bankroll can no longer cover the table minimum, unit_bet.
        """
        self.bankroll = self.initial_bankroll
        self.rounds_played = 0
        self.total_wagered = 0
        history = [self.bankroll]
        min_bankroll = self.bankroll

        rounds = 0
        while rounds < num_rounds and self.bankroll >= unit_bet:
            result, wagered = self.play_round(unit_bet)
            rounds += 1
            if result is not None:
                self.bankroll += result
                self.rounds_played += 1
                self.total_wagered += wagered
                min_bankroll = min(min_bankroll, self.bankroll)
            if rounds % record_every == 0:
                history.append(self.bankroll)

        # a ruined player keeps a flat bankroll for the rest of the horizon
        history.extend([self.bankroll] * (num_rounds // record_every + 1 - len(history)))
        return Result(self.initial_bankroll, self.bankroll, min_bankroll, rounds, self.rounds_played,
                      self.total_wagered, self.bankroll < unit_bet, np.array(history, dtype=float))
