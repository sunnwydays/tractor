import random
from collections import Counter
from itertools import combinations

import pytest

from engine.cards import BIG_JOKER, SMALL_JOKER, TRUMP, Suit, TrumpContext, parse_card
from engine.deal import build_deck
from engine.rules import (
    decompose,
    follow_options,
    is_legal_follow,
    is_legal_lead,
    lead_options,
    make_lead,
    match_profile,
    play_key,
    play_suit,
    throw_result,
    trick_winner,
)

CTX7 = TrumpContext(trump_rank=7, trump_suit=Suit.HEARTS)  # spades: 3 4 5 6 8 9 10 J Q K A
CTX3 = TrumpContext(trump_rank=3, trump_suit=Suit.HEARTS)  # spades: 4 5 6 7 8 9 10 J Q K A
CTX_NT = TrumpContext(trump_rank=7, trump_suit=None)


def cs(text: str) -> tuple[int, ...]:
    return tuple(sorted(parse_card(t) for t in text.split()))


def shape(groups):
    return [(g.width, g.length, g.cards) for g in groups]


# --- decompose -------------------------------------------------------------


def test_decompose_pair_tractor():
    g = decompose(cs("3♠ 3♠ 4♠ 4♠ 5♠ 5♠"), CTX7)
    assert shape(g) == [(2, 3, cs("3♠ 3♠ 4♠ 4♠ 5♠ 5♠"))]
    assert g[0].top == CTX7.order(parse_card("5♠"))


def test_decompose_triple_plus_pair_tractor_leaves_single():
    g = decompose(cs("3♠ 3♠ 3♠ 4♠ 4♠"), CTX7)
    assert shape(g) == [(2, 2, cs("3♠ 3♠ 4♠ 4♠")), (1, 1, cs("3♠"))]


def test_decompose_triple_tractor_and_pair():
    g = decompose(cs("3♠ 3♠ 3♠ 4♠ 4♠ 4♠ 5♠ 5♠"), CTX7)
    assert shape(g) == [(3, 2, cs("3♠ 3♠ 3♠ 4♠ 4♠ 4♠")), (2, 1, cs("5♠ 5♠"))]


def test_decompose_pair_and_singles():
    g = decompose(cs("A♠ K♠ K♠ 9♠"), CTX7)
    assert shape(g) == [(2, 1, cs("K♠ K♠")), (1, 1, cs("A♠")), (1, 1, cs("9♠"))]


def test_decompose_single_and_pair_fast_paths():
    assert shape(decompose(cs("9♠"), CTX7)) == [(1, 1, cs("9♠"))]
    assert shape(decompose(cs("9♠ 9♠"), CTX7)) == [(2, 1, cs("9♠ 9♠"))]
    assert len(decompose(cs("9♠ 8♠"), CTX7)) == 2


def test_tractor_skips_trump_rank_and_twos():
    # 7 is the trump rank, so 6-6-8-8 is a tractor; 2s are trump, so 3-3-A-A is not.
    assert shape(decompose(cs("6♠ 6♠ 8♠ 8♠"), CTX7)) == [(2, 2, cs("6♠ 6♠ 8♠ 8♠"))]
    assert len(decompose(cs("3♠ 3♠ A♠ A♠"), CTX7)) == 2
    assert len(decompose(cs("3♠ 3♠ 4♠ 4♠"), CTX7)) == 1


def test_trump_chain_tractors():
    # Hearts trump, rank 7: A♥ -> off-suit 2 -> 2♥ -> off-suit 7 -> 7♥ -> SJ -> BJ.
    assert len(decompose(cs("A♥ A♥ 2♠ 2♠"), CTX7)) == 1
    assert len(decompose(cs("A♥ A♥ 2♥ 2♥"), CTX7)) == 2
    assert len(decompose(cs("2♠ 2♠ 2♥ 2♥"), CTX7)) == 1
    assert len(decompose(cs("2♥ 2♥ 7♠ 7♠"), CTX7)) == 1
    assert len(decompose(cs("7♠ 7♠ 7♥ 7♥ SJ SJ BJ BJ"), CTX7)) == 1
    assert len(decompose(cs("2♠ 2♠ 2♣ 2♣"), CTX7)) == 2  # equal rank, not consecutive
    assert len(decompose(cs("7♠ 7♠ 7♣ 7♣"), CTX7)) == 2


def test_decompose_every_card_used_once():
    rng = random.Random(1)
    for _ in range(200):
        hand = [c for c in rng.sample(build_deck(3), 30) if CTX7.effective_suit(c) == 0]
        groups = decompose(hand, CTX7)
        assert sorted(c for g in groups for c in g.cards) == sorted(hand)
        sizes = [(g.size, g.width, g.top) for g in groups]
        assert sizes == sorted(sizes, reverse=True)


def test_play_suit():
    assert play_suit(cs("3♠ 4♠"), CTX7) == 0
    assert play_suit(cs("3♠ 4♥"), CTX7) is None
    assert play_suit(cs("4♥ SJ"), CTX7) == TRUMP
    assert play_suit((), CTX7) is None


# --- leads -----------------------------------------------------------------


def test_lead_options_basic():
    hand = cs("3♠ 3♠ 4♠ 4♠ 5♠ 9♠ K♠ K♠ K♠ 4♦")
    opts = lead_options(hand, CTX7, throws=False)
    assert len(opts) == len(set(opts))
    assert all(o == tuple(sorted(o)) for o in opts)
    assert set(opts) == {
        cs("3♠"), cs("4♠"), cs("5♠"), cs("9♠"), cs("K♠"), cs("4♦"),  # singles
        cs("3♠ 3♠"), cs("4♠ 4♠"), cs("K♠ K♠"),  # pairs
        cs("K♠ K♠ K♠"),  # triple
        cs("3♠ 3♠ 4♠ 4♠"),  # tractor
    }


def test_lead_options_tractor_sub_runs():
    hand = cs("3♠ 3♠ 4♠ 4♠ 5♠ 5♠ 3♦ 3♦ 3♦ 4♦ 4♦ 4♦ 5♦ 5♦ 5♦")
    opts = set(lead_options(hand, CTX7, throws=False))
    assert cs("3♠ 3♠ 4♠ 4♠") in opts
    assert cs("4♠ 4♠ 5♠ 5♠") in opts
    assert cs("3♠ 3♠ 4♠ 4♠ 5♠ 5♠") in opts
    assert cs("3♦ 3♦ 3♦ 4♦ 4♦ 4♦") in opts  # triple tractor
    assert cs("3♦ 3♦ 3♦ 4♦ 4♦ 4♦ 5♦ 5♦ 5♦") in opts
    assert cs("3♦ 3♦ 4♦ 4♦") in opts  # pair tractor out of triples


def test_lead_options_tractor_in_trump_chain():
    hand = cs("A♥ A♥ 2♠ 2♠ 2♥")
    opts = set(lead_options(hand, CTX7, throws=False))
    assert cs("A♥ A♥ 2♠ 2♠") in opts


def test_lead_options_throws():
    hand = cs("A♠ K♠ Q♠ 9♠ 9♠ 4♦")
    plain = set(lead_options(hand, CTX7, throws=False))
    with_throws = lead_options(hand, CTX7)
    assert set(with_throws) > plain
    assert len(with_throws) == len(set(with_throws))
    extra = set(with_throws) - plain
    assert cs("A♠ K♠") in extra
    assert cs("A♠ K♠ Q♠") in extra
    assert cs("A♠ K♠ Q♠ 9♠ 9♠") in extra
    assert cs("9♠ 9♠") not in extra  # already a pair
    assert all(is_legal_lead(o, hand, CTX7) for o in with_throws)


def test_lead_options_throw_skips_structures():
    hand = cs("K♠ K♠ K♠ A♠ A♠")  # top 2 = AA, top 5 = whole hand
    extra = set(lead_options(hand, CTX7)) - set(lead_options(hand, CTX7, throws=False))
    # KK AA is a tractor (K, A adjacent) and AA a pair, so only these two remain
    assert extra == {cs("K♠ K♠ K♠ A♠ A♠"), cs("K♠ A♠ A♠")}


def test_is_legal_lead():
    hand = cs("3♠ 3♠ 4♠ 9♥ 9♥")
    assert is_legal_lead(cs("3♠ 3♠"), hand, CTX7)
    assert is_legal_lead(cs("3♠ 4♠"), hand, CTX7)  # a throw
    assert not is_legal_lead(cs("3♠ 3♠ 3♠"), hand, CTX7)  # not held
    assert not is_legal_lead(cs("3♠ 9♥"), hand, CTX7)  # two suits
    assert not is_legal_lead((), hand, CTX7)


def test_make_lead():
    lead = make_lead(cs("K♠ K♠ A♠"), CTX7)
    assert lead.suit == 0 and lead.n == 3 and lead.is_throw
    assert make_lead(cs("K♠ K♠"), CTX7).is_throw is False
    assert make_lead(cs("4♥"), CTX7).suit == TRUMP
    with pytest.raises(ValueError):
        make_lead(cs("4♥ 4♠"), CTX7)


# --- throws ----------------------------------------------------------------


def test_throw_single_group_always_stands():
    assert throw_result(cs("K♠ K♠"), CTX7, [cs("A♠ A♠")]) == cs("K♠ K♠")
    assert throw_result(cs("4♠"), CTX7, [cs("A♠")]) == cs("4♠")


def test_throw_succeeds_when_nothing_beats_it():
    hand = cs("A♠ A♠ K♠")
    others = [cs("Q♠ Q♠ 4♠"), cs("K♠ J♠ 9♣")]
    assert throw_result(hand, CTX7, others) == hand


def test_throw_forced_to_smallest_beatable_group():
    # K and Q singles are both beatable by A; the lowest (Q) is played.
    assert throw_result(cs("K♠ Q♠"), CTX7, [cs("A♠ 4♦")]) == cs("Q♠")


def test_throw_single_beats_pair_when_both_beatable():
    # Pair KK and single 9 are both beatable: fewest cards -> the single.
    assert throw_result(cs("K♠ K♠ 9♠"), CTX7, [cs("A♠ A♠")]) == cs("9♠")


def test_throw_only_pair_beatable():
    # Nothing beats the single A; the pair KK is beaten by an AA pair.
    assert throw_result(cs("K♠ K♠ A♠"), CTX7, [cs("A♠ A♠ 4♦")]) == cs("K♠ K♠")
    # A lone A does not beat a pair.
    assert throw_result(cs("K♠ K♠ 9♠"), CTX7, [cs("A♠ 4♦")]) == cs("9♠")


def test_throw_triple_in_opponent_hand_beats_pair():
    assert throw_result(cs("K♠ K♠ A♠"), CTX7, [cs("A♠ A♠ A♠")]) == cs("K♠ K♠")


def test_throw_pair_not_beaten_by_lower_or_equal():
    assert throw_result(cs("K♠ K♠ A♠"), CTX7, [cs("Q♠ Q♠ Q♠"), cs("K♠ K♠")]) == cs("K♠ K♠ A♠")


def test_throw_trumps_do_not_count_against_off_suit():
    others = [cs("4♥ 4♥ 7♠ 7♠ SJ BJ")]
    assert throw_result(cs("A♠ K♠"), CTX7, others) == cs("A♠ K♠")


def test_throw_tractor_beaten_by_higher_tractor_only():
    throw = cs("8♠ 8♠ 9♠ 9♠ A♠")  # tractor 88-99 and single A
    # The single A cannot be beaten; the lower tractor 88-99 can (QQ-KK).
    assert throw_result(throw, CTX7, [cs("K♠ K♠ Q♠ Q♠")]) == cs("8♠ 8♠ 9♠ 9♠")
    # Two separate high pairs are not a tractor.
    assert throw_result(throw, CTX7, [cs("K♠ K♠ J♠ J♠")]) == throw


def test_throw_trump_throw():
    throw = cs("SJ BJ")
    assert throw_result(throw, CTX7, [cs("BJ 7♥")]) == cs("SJ")
    assert throw_result(cs("BJ 7♥"), CTX7, [cs("SJ 2♥")]) == cs("7♥")
    assert throw_result(cs("BJ 7♥"), CTX7, [cs("4♥ 2♥")]) == cs("BJ 7♥")


# --- following -------------------------------------------------------------


def legal(play, hand, lead, ctx=CTX3, split=False):
    return is_legal_follow(cs(play), cs(hand), make_lead(cs(lead), ctx), ctx, split_triples=split)


def options(hand, lead, ctx=CTX3, split=False, cap=400):
    return set(follow_options(cs(hand), make_lead(cs(lead), ctx), ctx, split_triples=split, cap=cap))


def test_match_profile_examples():
    lead = make_lead(cs("A♠ A♠"), CTX3)
    assert match_profile(cs("7♠ 7♠ 7♠ 9♠ 5♠"), lead, CTX3, split_triples=False) == (0, 0, 0)
    assert match_profile(cs("7♠ 7♠ 7♠ 9♠ 5♠"), lead, CTX3, split_triples=True) == (0, 0, 1)
    assert match_profile(cs("7♠ 7♠ 7♠ 9♠ 9♠ 5♠"), lead, CTX3, split_triples=False) == (0, 0, 1)
    assert match_profile(cs("7♠ 7♠ 9♦ 9♦"), lead, CTX3) == (0, 0, 1)  # off-suit pair ignored
    assert match_profile(cs("9♦ 9♦"), lead, CTX3) == (0, 0, 0)


def test_match_profile_tractor_and_triples():
    tractor = make_lead(cs("4♠ 4♠ 5♠ 5♠"), CTX3)
    assert match_profile(cs("6♠ 6♠ 7♠ 7♠ 9♠"), tractor, CTX3) == (1, 0, 2)
    assert match_profile(cs("6♠ 6♠ 8♠ 8♠ 10♠ 10♠ K♠"), tractor, CTX3) == (0, 0, 2)
    assert match_profile(cs("6♠ 6♠ 9♠ 10♠"), tractor, CTX3) == (0, 0, 1)
    triple = make_lead(cs("4♠ 4♠ 4♠"), CTX3)
    assert match_profile(cs("6♠ 6♠ 6♠ 8♠ 8♠"), triple, CTX3) == (0, 1, 1)
    assert match_profile(cs("6♠ 6♠ 8♠ 8♠"), triple, CTX3) == (0, 0, 1)  # triple falls to a pair
    assert match_profile(cs("6♠ 8♠"), triple, CTX3) == (0, 0, 0)
    tt = make_lead(cs("4♠ 4♠ 4♠ 5♠ 5♠ 5♠"), CTX3)
    assert match_profile(cs("6♠ 6♠ 6♠ 7♠ 7♠ 7♠"), tt, CTX3) == (1, 2, 2)
    assert match_profile(cs("6♠ 6♠ 6♠ 8♠ 8♠ 8♠"), tt, CTX3) == (0, 2, 2)  # no run, two triples


def test_follow_pair_with_triple_in_hand():
    hand = "7♠ 7♠ 7♠ 9♠ 5♠ 4♦ 4♦ 4♦ J♦"
    lead = "A♠ A♠"
    for play in ("7♠ 7♠", "7♠ 9♠", "7♠ 5♠", "9♠ 5♠"):
        assert legal(play, hand, lead)
    assert not legal("7♠ 4♦", hand, lead)
    assert not legal("4♦ 4♦", hand, lead)
    assert options(hand, lead) == {cs(p) for p in ("7♠ 7♠", "7♠ 9♠", "7♠ 5♠", "9♠ 5♠")}


def test_follow_pair_must_play_a_pair_when_one_is_available():
    hand = "7♠ 7♠ 7♠ 9♠ 9♠ 5♠ 4♦"
    assert legal("9♠ 9♠", hand, "A♠ A♠")
    assert legal("7♠ 7♠", hand, "A♠ A♠")
    assert not legal("9♠ 5♠", hand, "A♠ A♠")
    assert not legal("7♠ 9♠", hand, "A♠ A♠")
    assert options(hand, "A♠ A♠") == {cs("9♠ 9♠"), cs("7♠ 7♠")}


def test_follow_pair_with_split_triples_allowed():
    hand = "7♠ 7♠ 7♠ 9♠ 5♠"
    assert not legal("9♠ 5♠", hand, "A♠ A♠", split=True)
    assert options(hand, "A♠ A♠", split=True) == {cs("7♠ 7♠")}


def test_follow_pair_only_triple_left():
    assert options("7♠ 7♠ 7♠ 4♦", "A♠ A♠") == {cs("7♠ 7♠")}


def test_follow_triple():
    lead = "A♠ A♠ A♠"
    # has a triple: must play it
    assert options("7♠ 7♠ 7♠ 9♠ 9♠ 5♠", lead) == {cs("7♠ 7♠ 7♠")}
    # no triple but a pair: pair + any single
    got = options("7♠ 7♠ 9♠ 5♠ 4♠", lead)
    assert got == {cs("7♠ 7♠ 9♠"), cs("7♠ 7♠ 5♠"), cs("7♠ 7♠ 4♠")}
    # nothing: anything in suit
    got = options("7♠ 9♠ 5♠ 4♠", lead)
    assert got == {cs(p) for p in ("7♠ 9♠ 5♠", "7♠ 9♠ 4♠", "7♠ 5♠ 4♠", "9♠ 5♠ 4♠")}


def test_follow_triple_two_triples_either():
    got = options("7♠ 7♠ 7♠ 9♠ 9♠ 9♠ 4♦", "A♠ A♠ A♠")
    assert got == {cs("7♠ 7♠ 7♠"), cs("9♠ 9♠ 9♠")}


def test_follow_tractor():
    lead = "4♠ 4♠ 5♠ 5♠"
    # adjacent pairs 66 77: must play the tractor
    assert options("6♠ 6♠ 7♠ 7♠ K♠ 4♦", lead) == {cs("6♠ 6♠ 7♠ 7♠")}
    # separated pairs: two pairs
    assert options("6♠ 6♠ 8♠ 8♠ 10♠ 10♠ K♠", lead) == {
        cs("6♠ 6♠ 8♠ 8♠"), cs("6♠ 6♠ 10♠ 10♠"), cs("8♠ 8♠ 10♠ 10♠")
    }
    # one pair + singles: the pair and two singles
    got = options("6♠ 6♠ 9♠ J♠ K♠", lead)
    assert got == {cs("6♠ 6♠ 9♠ J♠"), cs("6♠ 6♠ 9♠ K♠"), cs("6♠ 6♠ J♠ K♠")}
    # no pairs: any four
    assert len(options("6♠ 7♠ 9♠ J♠ K♠", lead)) == 5


def test_follow_tractor_prefers_tractor_not_just_pairs():
    hand = "6♠ 6♠ 7♠ 7♠ 10♠ 10♠"
    assert not legal("6♠ 6♠ 10♠ 10♠", hand, "4♠ 4♠ 5♠ 5♠")
    assert legal("6♠ 6♠ 7♠ 7♠", hand, "4♠ 4♠ 5♠ 5♠")


def test_follow_triple_tractor_lead():
    lead = "4♠ 4♠ 4♠ 5♠ 5♠ 5♠"
    got = options("6♠ 6♠ 6♠ 7♠ 7♠ 7♠ 9♠ 9♠ 9♠ K♠", lead)
    assert got == {cs("6♠ 6♠ 6♠ 7♠ 7♠ 7♠")}
    # two separate triples: both triples (a "triple unit" each)
    got = options("6♠ 6♠ 6♠ 8♠ 8♠ 8♠ 9♠ K♠", lead)
    assert got == {cs("6♠ 6♠ 6♠ 8♠ 8♠ 8♠")}


def test_follow_throw_must_include_pair():
    got = options("9♠ 9♠ 8♠ 7♠ 6♠ 4♦", "A♠ A♠ K♠")
    assert got == {cs("9♠ 9♠ 8♠"), cs("9♠ 9♠ 7♠"), cs("9♠ 9♠ 6♠")}


def test_follow_void_is_free():
    hand = "9♥ 9♥ 5♦ 4♣ K♣"
    lead = "A♠ A♠"
    for play in ("9♥ 9♥", "5♦ 4♣", "9♥ K♣"):
        assert legal(play, hand, lead)
    assert len(options(hand, lead)) == 6 + 1  # 2-card multisets: C(4,2) of types + the 9♥ pair


def test_follow_short_suit_must_play_all_of_it():
    hand = "9♠ 5♦ 4♣ K♣ 9♥"
    assert not legal("5♦ 4♣", hand, "A♠ A♠")
    assert legal("9♠ 5♦", hand, "A♠ A♠")
    assert options(hand, "A♠ A♠") == {cs("9♠ 5♦"), cs("9♠ 4♣"), cs("9♠ K♣"), cs("9♠ 9♥")}
    assert options("9♠ 8♠ 5♦", "A♠ A♠ K♠") == {cs("9♠ 8♠ 5♦")}


def test_follow_single():
    hand = "9♠ 9♠ 5♠ 5♦ 4♥"
    assert options(hand, "A♠") == {cs("9♠"), cs("5♠")}
    assert options("5♦ 5♦ 4♥", "A♠") == {cs("5♦"), cs("4♥")}
    assert options(hand, "4♥") == {cs("4♥")}  # trump lead, one trump held


def test_follow_trump_lead():
    hand = "4♥ 4♥ 9♥ 5♠ 5♠"
    assert options(hand, "A♥ A♥") == {cs("4♥ 4♥")}
    assert not legal("5♠ 5♠", hand, "A♥ A♥")


def test_follow_wrong_size_or_cards_not_held():
    assert not legal("9♠", "9♠ 5♠", "A♠ A♠")
    assert not legal("9♠ 9♠", "9♠ 5♠", "A♠ A♠")


def test_follow_options_big_pool_is_structured_but_legal():
    hand = cs("4♠ 5♠ 6♠ 7♠ 8♠ 9♠ 10♠ J♠ Q♠ K♠ A♠ 4♠ 5♠ 6♠ 7♠ 8♠ 9♠ 10♠ J♠ Q♠ K♠ A♠")
    lead = make_lead(cs("4♠ 4♠ 5♠ 5♠ 6♠ 6♠ 8♠ 8♠"), CTX3)  # throw: tractor + pair
    opts = follow_options(hand, lead, CTX3)
    assert opts and all(is_legal_follow(o, hand, lead, CTX3) for o in opts)
    assert len(opts) < 400


def test_follow_options_big_void_pool_includes_trump_match():
    hand = cs("4♥ 4♥ 5♥ 5♥ 6♥ 6♥ 7♥ 7♥ 8♥ 9♥ 10♥ 4♦ 5♦ 6♦ 7♦ 8♦ 9♦ K♦")
    lead = make_lead(cs("A♠ A♠ K♠ K♠ Q♠ Q♠"), CTX3)  # pair tractor, n = 6
    opts = follow_options(hand, lead, CTX3)
    assert all(is_legal_follow(o, hand, lead, CTX3) for o in opts)
    # at least one full trump tractor
    assert any(play_key(o, lead, CTX3) is not None for o in opts)


# --- winning ---------------------------------------------------------------


def winner(*plays, ctx=CTX3):
    return trick_winner([cs(p) for p in plays], ctx)


def test_winner_higher_same_suit():
    assert winner("9♠", "K♠", "5♠", "A♠", "4♠") == 3
    assert winner("9♠ 9♠", "K♠ K♠", "5♠ 5♠") == 1


def test_winner_trump_single_beats_off_suit():
    assert winner("A♠", "K♠", "4♥", "Q♠") == 2
    assert winner("A♠", "2♦") == 1  # off-suit 2 is trump in rank
    assert winner("A♠", "3♣") == 1


def test_winner_trump_pair_beats_pair():
    assert winner("K♠ K♠", "4♥ 4♥", "A♠ A♠") == 1


def test_winner_random_trumps_lose_to_pair():
    assert winner("K♠ K♠", "4♥ 5♥", "Q♠ Q♠") == 0
    assert winner("K♠ K♠", "SJ BJ", "9♦ 9♦") == 0  # two trumps, not a pair


def test_winner_trump_tractor_beats_tractor():
    assert winner("A♠ A♠ K♠ K♠", "4♥ 4♥ 5♥ 5♥", "Q♠ Q♠ J♠ J♠") == 1
    assert winner("A♠ A♠ K♠ K♠", "4♥ 4♥ 6♥ 6♥") == 0  # two pairs, not a tractor
    assert winner("A♠ A♠ K♠ K♠", "4♥ 4♥ 5♥ 5♥", "6♥ 6♥ 7♥ 7♥") == 2


def test_winner_later_higher_trump_overtakes():
    assert winner("A♠", "4♥", "J♥", "10♥") == 2
    assert winner("A♠", "2♠", "3♥") == 2


def test_winner_identical_plays_first_wins():
    assert winner("A♠", "A♠", "K♠") == 0
    assert winner("A♠ A♠", "A♠ A♠") == 0
    assert winner("5♥", "4♥", "5♥") == 0


def test_winner_off_suit_discard_loses():
    assert winner("9♠", "A♦", "K♣", "10♠") == 3
    assert winner("9♠", "A♦", "K♣") == 0


def test_winner_trumped_throw():
    # Lead is a throw of two spade singles; any two trumps match it.
    assert winner("A♠ K♠", "4♥ 5♥", "Q♠ J♠") == 1
    assert winner("A♠ K♠", "4♥ 5♦", "Q♠ J♠") == 0  # mixed play cannot win
    assert winner("A♠ K♠", "4♥ 5♥", "6♥ 9♥") == 2  # higher top trump wins


def test_winner_throw_with_pair_needs_pair():
    # throw K♠K♠ + A♠: a trump play of three singles does not match, a pair + single does.
    assert winner("K♠ K♠ A♠", "4♥ 5♥ 6♥", "Q♠ Q♠ A♠") == 0
    assert winner("K♠ K♠ A♠", "4♥ 4♥ 6♥", "Q♠ Q♠ A♠") == 1


def test_winner_trump_lead():
    assert winner("4♥", "5♥", "3♠") == 2  # off-suit trump rank beats plain trump
    assert winner("4♥", "A♠", "5♥") == 2
    assert winner("SJ", "BJ", "3♥") == 1


def test_play_key_values():
    lead = make_lead(cs("K♠ K♠"), CTX3)
    o = CTX3.order
    assert play_key(cs("A♠ A♠"), lead, CTX3) == (0, o(parse_card("A♠")))
    assert play_key(cs("4♥ 4♥"), lead, CTX3) == (1, o(parse_card("4♥")))
    assert play_key(cs("A♠ Q♠"), lead, CTX3) is None
    assert play_key(cs("A♠ 4♥"), lead, CTX3) is None
    assert play_key(cs("A♦ A♦"), lead, CTX3) is None
    assert play_key(cs("A♠"), lead, CTX3) is None


def test_play_key_trump_lead_has_no_trump_bonus():
    lead = make_lead(cs("4♥"), CTX3)
    assert play_key(cs("BJ"), lead, CTX3)[0] == 0


def test_no_trump_context():
    # no-trump: 2s, 7s, jokers are trump; no suit is trump
    assert winner("A♠", "7♦", ctx=CTX_NT) == 1
    assert winner("A♠", "K♦", "2♣", ctx=CTX_NT) == 2
    assert winner("7♠ 7♠", "7♦ 7♦", ctx=CTX_NT) == 0  # equal pairs


# --- randomized checks -----------------------------------------------------


def brute_force(hand, lead, ctx, split):
    out = set()
    for combo in set(combinations(sorted(hand), lead.n)):
        if is_legal_follow(combo, hand, lead, ctx, split_triples=split):
            out.add(combo)
    return out


def random_ctx(rng):
    suit = rng.choice([None, 0, 1, 2, 3])
    return TrumpContext(rng.randint(3, 14), None if suit is None else Suit(suit))


def test_follow_options_matches_brute_force():
    rng = random.Random(2024)
    deck = build_deck(3)
    checked = 0
    for trial in range(250):
        ctx = random_ctx(rng)
        split = rng.random() < 0.3
        hand = sorted(rng.sample(deck, 22 if trial % 2 else 12))
        other = rng.sample(deck, 22)
        leads = lead_options(other, ctx)
        # bias toward small leads so brute force stays cheap
        lead_cards = rng.choice(leads) if rng.random() < 0.4 else rng.choice([x for x in leads if len(x) <= 4])
        if len(lead_cards) > len(hand):
            continue
        lead = make_lead(lead_cards, ctx)
        opts = follow_options(hand, lead, ctx, split_triples=split)
        assert opts, (hand, lead_cards)
        assert len(set(opts)) == len(opts)
        for o in opts:
            assert o == tuple(sorted(o))
            assert is_legal_follow(o, hand, lead, ctx, split_triples=split)
        if lead.n <= 4:
            full = follow_options(hand, lead, ctx, split_triples=split, cap=10**9)
            assert set(full) == brute_force(hand, lead, ctx, split)
            assert len(full) == len(set(full))
            assert set(opts) <= set(full)
            if len(full) <= 400 and lead.n <= 2:
                assert set(opts) == set(full)
            checked += 1
    assert checked > 100


def test_follow_options_dense_hands_all_legal():
    """Hands with many pairs / triples and long leads (structured branch)."""
    rng = random.Random(7)
    deck = build_deck(3)
    for _ in range(150):
        ctx = random_ctx(rng)
        suit = rng.choice(ctx.groups)
        pool = [c for c in deck if ctx.effective_suit(c) == suit]
        hand = sorted(rng.sample(pool, min(len(pool), rng.randint(8, 18))) + rng.sample(deck, 4))
        other = sorted(rng.sample(pool, min(len(pool), 16)))
        leads = [x for x in lead_options(other, ctx) if len(x) >= 3]
        if not leads:
            continue
        lead = make_lead(rng.choice(leads), ctx)
        if lead.n > len(hand):
            continue
        split = rng.random() < 0.3
        opts = follow_options(hand, lead, ctx, split_triples=split)
        assert opts
        assert all(is_legal_follow(o, hand, lead, ctx, split_triples=split) for o in opts)


def test_lead_options_all_legal_and_unique():
    rng = random.Random(5)
    deck = build_deck(3)
    for _ in range(100):
        ctx = random_ctx(rng)
        hand = rng.sample(deck, 22)
        opts = lead_options(hand, ctx)
        assert len(opts) == len(set(opts))
        for o in opts:
            assert o == tuple(sorted(o))
            assert is_legal_lead(o, hand, ctx)
            assert make_lead(o, ctx).cards == o
        assert {(c,) for c in hand} <= set(opts)
        assert {(c, c) for c, k in Counter(hand).items() if k >= 2} <= set(opts)


def test_throw_result_is_part_of_the_throw():
    rng = random.Random(11)
    deck = build_deck(3)
    for _ in range(200):
        ctx = random_ctx(rng)
        hand = rng.sample(deck, 22)
        others = [rng.sample(deck, 22) for _ in range(3)]
        for cards in lead_options(hand, ctx)[-6:]:
            res = throw_result(cards, ctx, others)
            assert not (Counter(res) - Counter(cards))
            groups = decompose(cards, ctx)
            assert res == cards or res in {g.cards for g in groups}
