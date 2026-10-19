"""Playing decisions: basic strategy and the Illustrious 18 count-based deviations.

Rules assumed throughout: 4 to 8 decks, dealer stands on soft 17, double after
split allowed, no surrender.
"""


def hand_value(hand):
    """(best total, soft) for a list of cards: an ace counts 11 unless that busts."""
    total = 0
    aces = 0
    for card in hand:
        if card.blackjack_value == 11:
            aces += 1
        total += card.blackjack_value
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total, aces > 0


def is_blackjack(hand):
    return len(hand) == 2 and hand_value(hand)[0] == 21


class BasicStrategy:
    """Basic strategy charts of Blackjack Apprenticeship (4-8 decks, S17, DAS)."""

    @staticmethod
    def get_action(player_hand, dealer_value, can_double=True):
        """'H', 'S' or 'D' for a hand that is not split (splits are decided first)."""
        total, soft = hand_value(player_hand)
        if can_double and len(player_hand) == 2 and BasicStrategy._should_double(total, soft, dealer_value):
            return "D"
        return BasicStrategy._hit_or_stand(total, soft, dealer_value)

    @staticmethod
    def should_split(pair_value, dealer_value):
        """5,5 and 10,10 are never split: they play as hard 10 and hard 20."""
        if pair_value in (11, 8):
            return True
        if pair_value == 9:
            return dealer_value not in (7, 10, 11)
        if pair_value == 7:
            return dealer_value <= 7
        if pair_value == 6:
            return dealer_value <= 6
        if pair_value == 4:
            return dealer_value in (5, 6)
        if pair_value in (2, 3):
            return dealer_value <= 7
        return False

    @staticmethod
    def _should_double(total, soft, dealer_value):
        if not soft:
            if total == 11:
                return dealer_value <= 10
            if total == 10:
                return dealer_value <= 9
            if total == 9:
                return dealer_value in (3, 4, 5, 6)
        else:
            if total in (13, 14):
                return dealer_value in (5, 6)
            if total in (15, 16):
                return dealer_value in (4, 5, 6)
            if total in (17, 18):
                return dealer_value in (3, 4, 5, 6)
        return False

    @staticmethod
    def _hit_or_stand(total, soft, dealer_value):
        if soft:
            if total >= 19:
                return "S"
            if total == 18:
                return "S" if dealer_value <= 8 else "H"
            return "H"
        if total >= 17:
            return "S"
        if total >= 13:
            return "S" if dealer_value <= 6 else "H"
        if total == 12:
            return "S" if dealer_value in (4, 5, 6) else "H"
        return "H"


class Illustrious18:
    """The Illustrious 18 index plays for Hi-Lo (shoe game, S17)."""

    # (hard total, dealer card): (index, action) -> play the action when TC >= index
    PLAY_ABOVE = {
        (16, 10): (0, "S"),
        (15, 10): (4, "S"),
        (10, 10): (4, "D"),
        (12, 3): (2, "S"),
        (12, 2): (3, "S"),
        (11, 11): (1, "D"),
        (9, 2): (1, "D"),
        (10, 11): (4, "D"),
        (9, 7): (3, "D"),
        (16, 9): (5, "S"),
    }
    # (hard total, dealer card): index -> hit when TC < index (otherwise stand, as basic strategy does)
    HIT_BELOW = {
        (13, 2): -1,
        (13, 3): -2,
        (12, 4): 0,
        (12, 5): -2,
        (12, 6): -1,
    }
    # dealer card: index -> split 10,10 when TC >= index
    SPLIT_TENS_ABOVE = {5: 5, 6: 4}
    INSURANCE_INDEX = 3

    def get_deviation(self, total, dealer_value, soft, true_count, can_double=True):
        """Deviating action on a hard total, or None to follow basic strategy."""
        if soft:
            return None
        key = (total, dealer_value)
        if key in self.PLAY_ABOVE:
            index, action = self.PLAY_ABOVE[key]
            if true_count >= index and (action != "D" or can_double):
                return action
        if key in self.HIT_BELOW and true_count < self.HIT_BELOW[key]:
            return "H"
        return None

    def should_split_tens(self, dealer_value, true_count):
        index = self.SPLIT_TENS_ABOVE.get(dealer_value)
        return index is not None and true_count >= index

    def take_insurance(self, true_count):
        return true_count >= self.INSURANCE_INDEX
