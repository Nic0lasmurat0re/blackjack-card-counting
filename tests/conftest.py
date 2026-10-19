from bjsim.cards import Card

FILLER_COUNT = 100


def card(value):
    return Card("♠", {11: "A", 10: "10"}.get(value, str(value)))


def stack_shoe(game, deal_order):
    """Cards dealt in deal_order, then neutral 7s."""
    game.shoe.cards = [Card("♣", "7") for _ in range(FILLER_COUNT)] + [Card("♠", v) for v in reversed(deal_order)]
    game.running_count = 0
    game.should_play_hand = lambda true_count: True


def hilo_sum(cards):
    return sum(c.count_value for c in cards)
