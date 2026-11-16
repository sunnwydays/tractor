from collections import Counter

import pytest

from engine.cards import (
    BIG_JOKER,
    SMALL_JOKER,
    TRUMP,
    Suit,
    TrumpContext,
    card_name,
    parse_card,
    points,
)
from engine.config import GameConfig
from engine.deal import build_deck, deal
from engine.hand import (
    analyze_hand,
    find_pairs,
    find_tractors,
    find_triples,
    group_by_suit,
)


def cards(text: str) -> list[int]:
    return [parse_card(t) for t in text.split()]


HEARTS_3 = TrumpContext(trump_rank=3, trump_suit=Suit.HEARTS)


# --- cards and deck -------------------------------------------------------


def test_deck_counts():
    deck = build_deck(3)
    assert len(deck) == 162
    counts = Counter(deck)
    assert len(counts) == 54
    assert set(counts.values()) == {3}


def test_points_total():
    assert sum(points(c) for c in build_deck(1)) == 100
    assert sum(points(c) for c in build_deck(3)) == 300
    assert points(parse_card("5♠")) == 5
    assert points(parse_card("10♦")) == 10
    assert points(parse_card("K♥")) == 10
    assert points(parse_card("A♥")) == 0
    assert points(BIG_JOKER) == 0


def test_card_names_round_trip():
    for c in range(54):
        assert parse_card(card_name(c)) == c
    assert parse_card("10h") == parse_card("10♥")


# --- trump context --------------------------------------------------------


def test_effective_suits():
    ctx = HEARTS_3
    assert ctx.effective_suit(parse_card("K♠")) == Suit.SPADES
    for name in ["4♥", "A♥", "2♠", "2♥", "3♣", "3♥", "SJ", "BJ"]:
        assert ctx.is_trump(parse_card(name)), name
    sizes = {g: sum(len(level) for level in ctx.levels(g)) for g in ctx.groups}
    assert sizes == {Suit.SPADES: 11, Suit.CLUBS: 11, Suit.DIAMONDS: 11, TRUMP: 21}


def test_trump_order():
    ctx = HEARTS_3
    chain = ["4♥", "5♥", "K♥", "A♥", "2♠", "2♥", "3♠", "3♥", "SJ", "BJ"]
    orders = [ctx.order(parse_card(n)) for n in chain]
    assert orders == sorted(orders) and len(set(orders)) == len(orders)
    # From trump-suit A upward every step is exactly one level.
    top = orders[3:]
    assert top == list(range(top[0], top[0] + len(top)))
    # Off-suit 2s are equal, as are off-suit trump-rank cards.
    assert ctx.order(parse_card("2♠")) == ctx.order(parse_card("2♦"))
    assert ctx.order(parse_card("3♣")) == ctx.order(parse_card("3♦"))


def test_off_suit_order_skips_trump_rank():
    ctx = TrumpContext(trump_rank=7, trump_suit=Suit.HEARTS)
    assert ctx.order(parse_card("8♠")) - ctx.order(parse_card("6♠")) == 1
    assert ctx.order(parse_card("3♠")) == 0  # 2s are trump, so 3 is lowest


def test_no_trump_suit():
    ctx = TrumpContext(trump_rank=3, trump_suit=None)
    assert ctx.groups == (0, 1, 2, 3, TRUMP)
    assert not ctx.is_trump(parse_card("A♥"))
    trump = [c for level in ctx.levels(TRUMP) for c in level]
    assert len(trump) == 10  # four 2s, four 3s, two jokers
    assert [len(level) for level in ctx.levels(TRUMP)] == [4, 4, 1, 1]


# --- config and dealing ---------------------------------------------------


@pytest.mark.parametrize(
    "players, hand, kitty, friends", [(7, 22, 8, 2), (8, 19, 10, 3), (9, 17, 9, 3)]
)
def test_deal_sizes(players, hand, kitty, friends):
    config = GameConfig.for_players(players)
    assert (config.hand_size, config.kitty_size, config.num_friends) == (
        hand,
        kitty,
        friends,
    )
    d = deal(config, 1)
    assert [len(h) for h in d.hands] == [hand] * players
    assert len(d.kitty) == kitty
    everything = [c for h in d.hands for c in h] + d.kitty
    assert sorted(everything) == sorted(build_deck(3))


def test_deal_is_seeded():
    config = GameConfig.for_players(7)
    assert deal(config, 42) == deal(config, 42)
    assert deal(config, 42) != deal(config, 43)


def test_bad_config_rejected():
    with pytest.raises(ValueError):
        GameConfig(num_players=7, num_decks=3, kitty_size=7, num_friends=2)


# --- hand analysis --------------------------------------------------------


def test_group_by_suit_sorted():
    hand = cards("A♠ 4♠ BJ 2♣ 5♥ 3♦ K♦")
    groups = group_by_suit(hand, HEARTS_3)
    assert [card_name(c) for c in groups[Suit.SPADES]] == ["4♠", "A♠"]
    assert [card_name(c) for c in groups[Suit.DIAMONDS]] == ["K♦"]
    assert groups[Suit.CLUBS] == []
    assert [card_name(c) for c in groups[TRUMP]] == ["5♥", "2♣", "3♦", "BJ"]


def test_pairs_and_triples():
    hand = cards("9♠ 9♠ 9♠ K♦ K♦ A♣ SJ SJ")
    assert find_pairs(hand) == sorted(cards("9♠ K♦ SJ"))
    assert find_triples(hand) == cards("9♠")
    # Same rank in different suits is not a pair.
    assert find_pairs(cards("9♠ 9♦")) == []


def names(tractor):
    return [[card_name(c) for c in level] for level in tractor.levels]


def test_simple_tractor():
    (t,) = find_tractors(cards("5♠ 5♠ 6♠ 6♠ 9♠"), HEARTS_3)
    assert (t.group, t.width, t.length) == (Suit.SPADES, 2, 2)
    assert names(t) == [["5♠"], ["6♠"]]


def test_not_a_tractor():
    assert find_tractors(cards("5♠ 5♠ 7♠ 7♠"), HEARTS_3) == []  # gap
    assert find_tractors(cards("5♠ 5♠ 6♦ 6♦"), HEARTS_3) == []  # two suits
    assert find_tractors(cards("5♠ 5♠ 6♠"), HEARTS_3) == []


def test_tractor_skips_trump_rank():
    ctx = TrumpContext(trump_rank=7, trump_suit=Suit.HEARTS)
    (t,) = find_tractors(cards("6♠ 6♠ 8♠ 8♠"), ctx)
    assert names(t) == [["6♠"], ["8♠"]]
    # With another trump rank the same cards are not consecutive.
    assert find_tractors(cards("6♠ 6♠ 8♠ 8♠"), HEARTS_3) == []
    # The trump-rank pair itself is trump, not part of the spade run.
    assert find_tractors(cards("6♠ 6♠ 7♠ 7♠"), ctx) == []


def test_tractor_skips_twos():
    # 2s are trump: 2♠2♠ + 4♠4♠ don't chain (3 is the trump rank here)...
    assert find_tractors(cards("2♠ 2♠ 4♠ 4♠"), HEARTS_3) == []
    # ...and A doesn't wrap around to the low end.
    assert find_tractors(cards("A♠ A♠ 4♠ 4♠"), HEARTS_3) == []
    # In the trump suit, 2 is skipped in the low run too: with 4 as trump
    # rank, 3♥3♥ + 5♥5♥ are consecutive.
    ctx = TrumpContext(trump_rank=4, trump_suit=Suit.HEARTS)
    (t,) = find_tractors(cards("3♥ 3♥ 5♥ 5♥"), ctx)
    assert t.group == TRUMP and names(t) == [["3♥"], ["5♥"]]


def test_full_trump_chain():
    hand = cards("K♥ K♥ A♥ A♥ 2♠ 2♠ 2♥ 2♥ 3♠ 3♠ 3♥ 3♥ SJ SJ BJ BJ")
    (t,) = find_tractors(hand, HEARTS_3)
    assert t.group == TRUMP and t.length == 8
    assert names(t) == [
        ["K♥"], ["A♥"], ["2♠"], ["2♥"], ["3♠"], ["3♥"], ["SJ"], ["BJ"],
    ]  # fmt: skip


@pytest.mark.parametrize(
    "hand",
    [
        "A♥ A♥ 2♠ 2♠",  # trump-suit A -> off-suit 2
        "2♣ 2♣ 2♥ 2♥",  # off-suit 2 -> trump-suit 2
        "2♥ 2♥ 3♦ 3♦",  # trump-suit 2 -> off-suit trump rank
        "3♦ 3♦ 3♥ 3♥",  # off-suit trump rank -> trump-suit trump rank
        "3♥ 3♥ SJ SJ",  # trump-suit trump rank -> small joker
        "SJ SJ BJ BJ",  # small joker -> big joker
    ],
)
def test_each_trump_chain_link(hand):
    (t,) = find_tractors(cards(hand), HEARTS_3)
    assert t.group == TRUMP and t.length == 2


@pytest.mark.parametrize(
    "hand",
    [
        "2♠ 2♠ 2♣ 2♣",  # equal off-suit 2s
        "3♠ 3♠ 3♦ 3♦",  # equal off-suit trump-rank cards
        "A♥ A♥ 2♥ 2♥",  # skips the off-suit 2 level
        "2♠ 2♠ 3♠ 3♠",  # skips the trump-suit 2 level
        "3♠ 3♠ SJ SJ",  # skips the trump-suit trump-rank level
    ],
)
def test_trump_non_tractors(hand):
    assert find_tractors(cards(hand), HEARTS_3) == []


def test_equal_cards_share_a_level():
    (t,) = find_tractors(cards("A♥ A♥ 2♠ 2♠ 2♣ 2♣ 2♥ 2♥"), HEARTS_3)
    assert t.length == 3
    assert names(t) == [["A♥"], ["2♠", "2♣"], ["2♥"]]


def test_no_trump_chain():
    ctx = TrumpContext(trump_rank=3, trump_suit=None)
    (t,) = find_tractors(cards("2♠ 2♠ 3♥ 3♥ SJ SJ BJ BJ"), ctx)
    assert t.group == TRUMP and t.length == 4
    assert find_tractors(cards("2♠ 2♠ 2♥ 2♥"), ctx) == []
    # Hearts is an ordinary suit in 无主.
    (t,) = find_tractors(cards("K♥ K♥ A♥ A♥"), ctx)
    assert t.group == Suit.HEARTS


def test_triple_tractors():
    hand = cards("5♠ 5♠ 5♠ 6♠ 6♠ 6♠ 7♠ 7♠")
    (pairs,) = find_tractors(hand, HEARTS_3, width=2)
    assert pairs.length == 3  # triples count as pairs too
    (triples,) = find_tractors(hand, HEARTS_3, width=3)
    assert triples.width == 3 and names(triples) == [["5♠"], ["6♠"]]


def test_two_separate_tractors():
    found = find_tractors(cards("5♠ 5♠ 6♠ 6♠ 9♠ 9♠ 10♠ 10♠ J♦ J♦ Q♦ Q♦"), HEARTS_3)
    assert [(t.group, t.length) for t in found] == [
        (Suit.SPADES, 2),
        (Suit.SPADES, 2),
        (Suit.DIAMONDS, 2),
    ]


def test_analyze_hand():
    hand = cards("5♠ 5♠ 5♠ 6♠ 6♠ 6♠ 9♠ K♦ SJ SJ BJ BJ 2♣")
    summary = analyze_hand(hand, HEARTS_3)
    spades = summary[Suit.SPADES]
    assert (spades.length, spades.pairs, spades.triples) == (7, 2, 2)
    assert (spades.pair_tractors, spades.triple_tractors) == (1, 1)
    assert summary[Suit.CLUBS].length == 0
    assert summary[Suit.DIAMONDS].length == 1
    trump = summary[TRUMP]
    assert (trump.length, trump.pairs, trump.triples) == (5, 2, 0)
    assert (trump.pair_tractors, trump.triple_tractors) == (1, 0)


def test_analyze_matches_find_functions():
    config = GameConfig.for_players(7)
    for seed in range(50):
        hand = deal(config, seed).hands[0]
        summary = analyze_hand(hand, HEARTS_3)
        groups = group_by_suit(hand, HEARTS_3)
        for g in HEARTS_3.groups:
            s = summary[g]
            assert s.length == len(groups[g])
            assert s.pairs == len(find_pairs(groups[g]))
            assert s.triples == len(find_triples(groups[g]))
            for width, n in ((2, s.pair_tractors), (3, s.triple_tractors)):
                assert n == sum(
                    t.group == g for t in find_tractors(hand, HEARTS_3, width)
                )
    assert SMALL_JOKER < BIG_JOKER
