from dataclasses import replace

import pytest

from engine.cards import BIG_JOKER, SMALL_JOKER, Suit, parse_card, points
from engine.config import LANDLORD, PEASANTS, GameConfig
from engine.deal import build_deck
from engine.state import (
    BuryCard,
    CallFriends,
    Declare,
    FriendCall,
    GoSolo,
    Pass,
    Phase,
    Play,
    _closing_on,
    apply,
    is_legal,
    legal_actions,
    new_round,
    state_for_play,
)
from engine.view import make_view

CFG = GameConfig.for_players(7)
N = 7


def c1(text: str) -> int:
    return parse_card(text)


def cs(text: str) -> tuple[int, ...]:
    return tuple(sorted(parse_card(t) for t in text.split()))


def rigged(prefix: str, *, cfg=CFG, **kw):
    """A new round whose deck starts with the given cards (then the rest in sorted order)."""
    cards = [c1(t) for t in prefix.split()]
    rest = build_deck(cfg.num_decks)
    for c in cards:
        rest.remove(c)
    st = new_round(cfg, 0, **kw)
    n = cfg.num_players
    st = replace(
        st, deck=tuple(cards + rest), dealt=0, hands=((),) * n, declaration=None,
        declare_history=(), to_act=kw.get("first_seat", 0), closing_left=-1,
    )  # fmt: skip
    from engine.state import _deal_on

    return _deal_on(st)


def pass_until_bury(st, *, declare=False):
    """Pass at every window (or take the first declaration offered) until the deal is over."""
    while st.phase is Phase.DEAL:
        legal = legal_actions(st)
        st = apply(st, legal[1] if declare and len(legal) > 1 else Pass())
    return st


def closing_state(hands, declaration=None, *, levels=None, eligible=None, cfg=CFG, first=0):
    """A deal that is complete, with chosen hands, ready for the closing round."""
    st = new_round(cfg, 1, levels=levels, eligible=eligible, first_seat=first)
    n = cfg.num_players
    full = tuple(tuple(sorted(cs(hands[s]))) if s in hands else () for s in range(n))
    return replace(
        st, hands=full, dealt=n * cfg.hand_size, declaration=declaration, closing_left=n, to_act=0
    )


def at_play(hands, *, cfg=CFG, trump_rank=7, suit=Suit.HEARTS, **kw):
    return state_for_play(cfg, [cs(h) for h in hands], 0, trump_rank, suit, **kw)


def play(st, *plays):
    for p in plays:
        st = apply(st, Play(cs(p)))
    return st


# --- declaring -------------------------------------------------------------


def test_deal_is_card_by_card_and_window_opens_on_a_three():
    st = rigged("3♥")
    assert (st.phase, st.to_act, st.dealt) == (Phase.DEAL, 0, 1)
    assert st.hands[0] == cs("3♥") and all(h == () for h in st.hands[1:])
    assert legal_actions(st) == [Pass(), Declare(c1("3♥"), 1)]


def test_window_only_for_own_level_card_of_eligible_player():
    levels = (3, 5, 6, 3, 3, 3, 3)
    st = rigged("3♥ 3♥ 6♣", levels=levels, eligible=(1, 2))
    # seat 0 is not eligible, seat 1's level is 5: the first window is seat 2's 6
    assert (st.to_act, st.dealt) == (2, 3)
    assert legal_actions(st) == [Pass(), Declare(c1("6♣"), 1)]
    assert not is_legal(st, Declare(c1("3♥"), 1))
    st = pass_until_bury(apply(st, Declare(c1("6♣"), 1)))
    assert st.landlord == 2 and st.ctx.trump_rank == 6 and st.ctx.trump_suit == Suit.CLUBS


def test_each_declare_is_followed_by_more_dealing():
    st = rigged("3♥")
    st2 = apply(st, Declare(c1("3♥"), 1))
    assert st2.declaration.player == 0 and st2.declare_history == (st2.declaration,)
    assert st2.dealt > 1 or st2.phase is not Phase.DEAL


def test_pair_contests_single_triple_contests_pair_not_same_suit():
    single = closing_state({1: "3♠ 3♠ 3♥", 2: "3♥ 3♥", 3: "3♣ 3♣ 3♣"})
    single = replace(single, declaration=_decl(0, "3♥", 1), to_act=1)
    assert is_legal(single, Declare(c1("3♠"), 2))
    assert not is_legal(single, Declare(c1("3♠"), 1))  # a single does not beat a single
    assert not is_legal(replace(single, to_act=2), Declare(c1("3♥"), 2))  # same suit
    pair = replace(single, declaration=_decl(0, "3♥", 2), to_act=3)
    assert is_legal(pair, Declare(c1("3♣"), 3))
    assert not is_legal(pair, Declare(c1("3♣"), 2))  # a pair does not beat a pair
    assert not is_legal(replace(pair, to_act=1), Declare(c1("3♠"), 2))


def _decl(player, card, count):
    from engine.state import Declaration

    return Declaration(player, c1(card), count)


def test_reinforce_own_declaration_only_with_more_of_the_same_card():
    st = closing_state({0: "3♥ 3♥ 3♥ 3♠ 3♠"}, _decl(0, "3♥", 1))
    assert is_legal(st, Declare(c1("3♥"), 2))
    assert is_legal(st, Declare(c1("3♥"), 3))
    assert not is_legal(st, Declare(c1("3♠"), 2))  # a different card: not a reinforcement
    assert not is_legal(replace(st, declaration=_decl(0, "3♥", 2)), Declare(c1("3♥"), 2))


def test_only_eligible_players_with_enough_copies_of_their_own_level():
    levels = (3, 5, 3, 3, 3, 3, 3)
    st = closing_state({0: "3♠ 3♠", 1: "3♥ 5♥"}, levels=levels, eligible=(1, 2))
    assert not is_legal(st, Declare(c1("3♠"), 1))  # seat 0 not eligible
    st = replace(st, to_act=1)
    assert not is_legal(st, Declare(c1("3♥"), 1))  # not seat 1's level
    assert not is_legal(st, Declare(c1("5♥"), 2))  # holds one copy only
    assert is_legal(st, Declare(c1("5♥"), 1))


def test_joker_pair_beats_everything_and_means_no_trump():
    st = closing_state({1: "SJ SJ", 2: "BJ BJ", 3: "BJ 3♠"}, _decl(0, "3♥", 3))
    assert not is_legal(replace(st, to_act=3), Declare(BIG_JOKER, 1))
    assert is_legal(replace(st, to_act=1), Declare(SMALL_JOKER, 2))
    big = replace(st, to_act=2, declaration=_decl(1, "SJ", 2))
    assert is_legal(big, Declare(BIG_JOKER, 2))
    assert not is_legal(replace(big, to_act=1, declaration=_decl(2, "BJ", 2)), Declare(SMALL_JOKER, 2))
    # play it through: seat 0's second big joker opens a window
    st = rigged("BJ 2♠ 2♠ 2♠ 4♠ 4♠ 4♠ BJ")
    assert st.to_act == 0 and st.dealt == 8
    st = pass_until_bury(apply(st, Declare(BIG_JOKER, 2)))
    assert st.landlord == 0 and st.ctx.trump_suit is None and st.ctx.trump_rank == 3


def test_closing_round_asks_everyone_with_an_option_until_all_pass():
    st = closing_state({3: "3♥", 5: "3♠ 3♠"})
    st = _closing_on(st, 0)
    assert (st.to_act, st.closing_left) == (3, 4)  # seats 0, 1, 2 had no option
    st = apply(st, Declare(c1("3♥"), 1))  # seat 3 declares; 4 has no option
    assert (st.to_act, st.closing_left) == (5, 5)  # all but the declarer still to be passed over
    st = apply(st, Pass())  # 5 passes (6, 0, 1, 2 have no option)
    assert st.phase is Phase.BURY and st.landlord == 3


def test_closing_round_restarts_after_a_contest():
    st = closing_state({1: "3♥ 3♥ 3♥", 2: "3♠ 3♠"})
    st = _closing_on(st, 0)
    assert st.to_act == 1
    st = apply(st, Declare(c1("3♥"), 1))
    assert st.to_act == 2
    st = apply(st, Declare(c1("3♠"), 2))  # a pair contests the single
    assert (st.to_act, st.closing_left) == (1, 1)  # seat 1 is asked again: a triple beats a pair
    assert is_legal(st, Declare(c1("3♥"), 3))
    st = apply(st, Declare(c1("3♥"), 3))
    assert st.phase is Phase.BURY and st.landlord == 1 and len(st.declare_history) == 3


def test_nobody_declares_redeals_with_a_new_shuffle():
    st = closing_state({})
    st2 = _closing_on(st, 0)
    assert st2.redeals == 1 and st2.phase is Phase.DEAL and st2.deck != st.deck
    assert st2.dealt >= 1


def test_no_face_redeal_only_deals_hands_with_a_jqk():
    from engine.state import _has_clothesless_hand

    cfg = GameConfig.for_players(7)
    for seed in range(20):
        st = new_round(cfg, seed)
        assert not _has_clothesless_hand(st.deck, cfg, st.first_seat)


def test_clothesless_hand_detection_ignores_jokers_and_aces():
    from engine.state import _has_clothesless_hand

    cfg = GameConfig.for_players(7)
    n, hs = cfg.num_players, cfg.hand_size
    # Seat 0 gets only aces (rank 14 -> index 12) and jokers; everyone else gets a king (index 11).
    deck = [11] * (n * hs)
    for i in range(0, n * hs, n):
        deck[i] = 12 if i % 2 else SMALL_JOKER
    assert _has_clothesless_hand(deck, cfg, 0)
    deck[0] = 11
    assert not _has_clothesless_hand(deck, cfg, 0)


def test_table_that_never_declares_gives_up():
    st = new_round(CFG, 5)
    with pytest.raises(RuntimeError):
        pass_until_bury(st)


# --- kitty and bury ----------------------------------------------------------


@pytest.mark.parametrize("n", [7, 8, 9])
def test_kitty_pickup_and_bury_sizes(n):
    cfg = GameConfig.for_players(n)
    st = pass_until_bury(new_round(cfg, 3, first_seat=2), declare=True)
    ll = st.landlord
    assert st.phase is Phase.BURY and to_act_is(st, ll)
    assert len(st.kitty) == cfg.kitty_size == len(st.deck) - n * cfg.hand_size
    assert len(st.hands[ll]) == cfg.hand_size + cfg.kitty_size
    for s in range(n):  # card i goes to seat (first_seat + i) % n
        if s != ll:
            assert st.hands[s] == tuple(sorted(st.deck[(s - 2) % n : n * cfg.hand_size : n]))
    for i in range(cfg.kitty_size):
        assert st.phase is Phase.BURY
        legal = legal_actions(st)
        assert {a.card for a in legal} == set(st.hands[ll])
        assert not is_legal(st, BuryCard(54))
        st = apply(st, legal[0])
    assert st.phase is Phase.CALL and len(st.buried) == cfg.kitty_size
    assert len(st.hands[ll]) == cfg.hand_size


def to_act_is(st, p):
    return st.to_act == p


# --- calling friends -----------------------------------------------------------


def call_state(landlord_hand="A♠ 3♦", buried="", cfg=CFG, trump_rank=7, suit=Suit.HEARTS):
    hands = [cs(landlord_hand)] + [()] * (cfg.num_players - 1)
    st = state_for_play(cfg, hands, 0, trump_rank, suit, buried=cs(buried))
    return replace(st, phase=Phase.CALL)


def call(*specs):
    """call('A♠', 1, 'A♠', 2) or with a trailing alive flag in a tuple."""
    return CallFriends(tuple(FriendCall(c1(c), o, *(a,)) for c, o, a in specs))


A = lambda card, o, alive=True: (card, o, alive)  # noqa: E731


def test_friend_call_legal_and_illegal_cases():
    st = call_state()
    assert is_legal(st, call(A("A♠", 1), A("A♠", 2)))
    assert is_legal(st, call(A("A♠", 1), A("K♠", 1)))
    assert not is_legal(st, call(A("A♠", 1)))  # wrong number of calls
    assert not is_legal(st, call(A("A♠", 1), A("K♣", 1)))  # two suits
    assert not is_legal(st, call(A("A♥", 1), A("K♥", 1)))  # trump suit
    assert not is_legal(st, call(A("7♠", 1), A("K♠", 1)))  # trump rank
    assert not is_legal(st, call(A("2♠", 1), A("K♠", 1)))  # permanent trump rank
    assert not is_legal(st, CallFriends((FriendCall(SMALL_JOKER, 1), FriendCall(c1("K♠"), 1))))
    assert not is_legal(st, call(A("A♠", 4), A("K♠", 1)))  # only 3 decks
    assert not is_legal(st, call(A("A♠", 0), A("K♠", 1)))
    assert not is_legal(st, call(A("A♠", 1), A("A♠", 1)))  # same call twice
    assert not is_legal(st, call(A("A♠", 1, True), A("A♠", 2, False)))  # mixed alive flags
    assert not is_legal(st, Pass())


def test_friend_call_in_no_trump_may_use_any_suit():
    st = call_state(suit=None)
    assert is_legal(st, call(A("A♥", 1), A("K♥", 1)))


def test_dead_call_needs_the_landlord_to_hold_the_rest():
    st = call_state("A♠ 3♦")  # holds 1 A♠: two dead calls on it are right
    assert is_legal(st, call(A("A♠", 1, False), A("A♠", 2, False)))
    assert not is_legal(st, call(A("A♠", 1, False), A("A♠", 3, False)))  # ordinals must be 1..m
    assert not is_legal(st, call(A("A♠", 1, False), A("K♠", 1)))  # holds 0 K♠ (needs 2)
    assert not is_legal(call_state("3♦"), call(A("A♠", 1, False), A("A♠", 2, False)))
    # buried copies count as the landlord's
    assert is_legal(call_state("3♦", buried="A♠"), call(A("A♠", 1, False), A("A♠", 2, False)))
    two = call_state("A♠ A♠ K♠ K♠")
    assert is_legal(two, call(A("A♠", 1, False), A("K♠", 1, False)))


def test_solo_needs_allow_solo_and_starts_play():
    st = call_state()
    assert is_legal(st, GoSolo())
    st2 = apply(st, GoSolo())
    assert st2.phase is Phase.PLAY and st2.solo_called and st2.calls == ()
    assert st2.to_act == st2.leader == 0
    no_solo = call_state(cfg=GameConfig.for_players(7, allow_solo=False))
    assert not is_legal(no_solo, GoSolo())
    assert GoSolo() not in legal_actions(no_solo)


def test_call_actions_listed_are_legal_and_include_dead_variants():
    st = call_state("A♠ A♠ K♠ K♠ 3♦")
    acts = legal_actions(st)
    assert GoSolo() in acts and all(is_legal(st, a) for a in acts)
    dead = call(A("K♠", 1, False), A("A♠", 1, False))
    assert dead in acts
    assert not any(f.card // 13 == Suit.HEARTS for a in acts if isinstance(a, CallFriends) for f in a.calls)
    st = apply(st, call(A("A♠", 1), A("A♠", 2)))
    assert st.phase is Phase.PLAY and st.slots == (None, None) and st.leader == 0


# --- play: friends, slots, scoring ----------------------------------------------

SPADE_TRICK = [
    "K♠ 4♦", "A♠ 3♦", "3♠ 6♦", "4♠ 8♦", "5♠ 9♦", "6♠ J♦", "8♠ Q♦",
]  # fmt: skip
CALLS_A = (FriendCall(c1("A♠"), 1), FriendCall(c1("A♠"), 2))


def test_friend_joins_after_the_trick_and_their_points_move_sides():
    st = at_play(SPADE_TRICK, calls=CALLS_A)
    st = play(st, "K♠", "A♠")
    assert st.slots == (1, None) and st.slot_tricks == (1, None) and st.friends == ()
    st = play(st, "3♠", "4♠", "5♠", "6♠", "8♠")
    rec = st.tricks[0]
    assert (rec.winner, rec.points, rec.joined) == (1, 15, (1,))
    assert st.friends == (1,) and st.points_won[1] == 15 and st.leader == st.to_act == 1
    st = play(st, "3♦", "6♦", "8♦", "9♦", "J♦", "Q♦", "4♦")
    r = st.result
    assert st.phase is Phase.DONE and r.landlord_team == (0, 1)
    assert r.trick_points == 0  # the friend's 15 points are not the peasants'
    assert r.winner == LANDLORD and r.peasant_points == 0


def test_without_the_call_the_same_points_go_to_the_peasants():
    st = at_play(SPADE_TRICK, calls=(FriendCall(c1("K♠"), 3),))
    st = play(st, "K♠", "A♠", "3♠", "4♠", "5♠", "6♠", "8♠", "3♦", "6♦", "8♦", "9♦", "J♦", "Q♦", "4♦")
    assert st.friends == () and st.result.trick_points == 15


def test_wasted_slot_when_the_landlord_plays_a_called_alive_copy():
    hands = ["A♠ 3♦", "A♠ 4♦", "3♠ 6♦", "4♠ 8♦", "5♠ 9♦", "6♠ J♦", "8♠ Q♦"]
    st = play(at_play(hands, calls=CALLS_A), "A♠")
    assert st.slots == (0, None) and st.copies_seen == ((c1("A♠"), 1),)
    st = play(st, "A♠")  # the 2nd copy: seat 1 fills the second slot
    assert st.slots == (0, 1)
    st = play(st, "3♠", "4♠", "5♠", "6♠", "8♠")
    assert st.friends == (1,)


def test_ignore_option_does_not_count_the_landlord_copy():
    cfg = GameConfig.for_players(7, alive_landlord_copy="ignore")
    hands = ["A♠ 3♦", "A♠ 4♦", "3♠ 6♦", "4♠ 8♦", "5♠ 9♦", "6♠ J♦", "8♠ Q♦"]
    st = play(at_play(hands, cfg=cfg, calls=CALLS_A), "A♠")
    assert st.slots == (None, None) and st.copies_seen == ((c1("A♠"), 0),)
    st = play(st, "A♠")
    assert st.slots == (1, None)


def test_dead_call_ignores_the_landlord_copy():
    hands = ["A♠ 3♦", "4♠ 4♦", "A♠ 6♦", "5♠ 8♦", "6♠ 9♦", "7♠ J♦", "8♠ Q♦"]
    calls = (FriendCall(c1("A♠"), 1, False),)
    st = play(at_play(hands, calls=calls), "A♠", "4♠")
    assert st.slots == (None,)
    st = play(st, "A♠")
    assert st.slots == (2,) and st.slot_tricks == (1,)


def test_one_player_filling_two_slots_is_still_one_friend():
    hands = ["3♠ 4♠", "A♠ A♠", "4♠ 5♠", "5♠ 6♠", "6♠ 8♠", "8♠ 9♠", "9♠ 10♠"]
    st = at_play(hands, calls=CALLS_A, leader=1)
    st = play(st, "A♠ A♠", "4♠ 5♠", "5♠ 6♠", "6♠ 8♠", "8♠ 9♠", "9♠ 10♠", "3♠ 4♠")
    assert st.slots == (1, 1) and st.friends == (1,)
    assert st.result.landlord_team == (0, 1)


def test_solo_doubles_the_landlord_gain_but_an_accidental_solo_does_not():
    hands = ["A♠", "3♠", "4♠", "5♠", "6♠", "8♠", "9♠"]
    on_purpose = play(at_play(hands, solo=True), "A♠", "3♠", "4♠", "5♠", "6♠", "8♠", "9♠")
    accident = play(at_play(hands), "A♠", "3♠", "4♠", "5♠", "6♠", "8♠", "9♠")
    assert on_purpose.result.winner == LANDLORD
    assert (on_purpose.result.base_gain, on_purpose.result.gain) == (3, 6)
    assert (accident.result.base_gain, accident.result.gain) == (3, 3)


def test_failed_throw_plays_only_the_smallest_beatable_group_and_records_attempted():
    hands = ["3♠ 4♦", "4♠ 5♦", "A♠ Q♠", "K♠ 6♦", "5♠ 8♦", "6♠ 9♦", "8♠ J♦"]
    st = at_play(hands, leader=2, calls=CALLS_A)
    before = st
    st = apply(st, Play(cs("A♠ Q♠")))
    assert before.trick == () and before.attempted is None  # apply is pure
    assert st.attempted == cs("A♠ Q♠")
    assert st.trick == ((2, cs("Q♠")),) and st.lead.n == 1
    assert st.hands[2] == cs("A♠")  # only the played card left the hand
    assert st.slots == (None, None) and st.copies_seen == ((c1("A♠"), 0),)  # attempted A♠ not counted
    st = play(st, "K♠", "5♠", "6♠", "8♠", "3♠", "4♠")
    rec = st.tricks[0]
    assert rec.attempted == cs("A♠ Q♠") and rec.winner == 3 and st.attempted is None
    assert rec.plays[0] == (2, cs("Q♠"))


def test_a_successful_throw_is_played_whole():
    hands = ["3♠ 4♦", "4♠ 5♦", "A♠ K♠", "Q♠ 6♦", "5♠ 8♦", "6♠ 9♦", "8♠ J♦"]
    st = apply(at_play(hands, leader=2), Play(cs("A♠ K♠")))
    assert st.attempted is None and st.trick == ((2, cs("A♠ K♠")),) and st.lead.is_throw


def last_trick(hands, kitty="K♣ K♣", **kw):
    return at_play(hands, buried=cs(kitty), **kw)


def test_last_trick_won_by_peasants_with_a_single_doubles_the_kitty():
    hands = ["3♠", "A♠", "4♠", "5♠", "6♠", "8♠", "9♠"]
    st = play(last_trick(hands), *hands)
    r = st.result
    assert (r.kitty_points, r.kitty_multiplier) == (20, 2)
    assert r.trick_points == 5 and r.peasant_points == 5 + 40


def test_last_trick_won_by_peasants_with_a_pair_quadruples_the_kitty():
    hands = ["3♠ 3♠", "A♠ A♠", "4♠ 4♠", "5♠ 5♠", "6♠ 6♠", "8♠ 8♠", "9♠ 9♠"]
    st = play(last_trick(hands), *hands)
    r = st.result
    assert r.kitty_multiplier == 4 and r.trick_points == 10 and r.peasant_points == 10 + 80


def test_last_trick_won_by_the_landlord_team_gets_no_kitty():
    hands = ["A♠", "3♠", "4♠", "5♠", "6♠", "8♠", "9♠"]
    st = play(last_trick(hands), *hands)
    r = st.result
    assert r.kitty_multiplier == 0 and r.peasant_points == r.trick_points == 0 and r.winner == LANDLORD


def test_illegal_actions_raise_and_do_not_change_the_state():
    st = at_play(SPADE_TRICK)
    for bad in (Play(cs("A♠")), Play(()), Play(cs("K♠ K♠")), Pass(), GoSolo(), BuryCard(c1("K♠"))):
        assert not is_legal(st, bad)
        with pytest.raises(ValueError):
            apply(st, bad)
    st = play(st, "K♠")
    assert not is_legal(st, Play(cs("4♦")))  # seat 1 holds A♠: must follow suit
    done = play(at_play(["A♠", "3♠", "4♠", "5♠", "6♠", "8♠", "9♠"]), "A♠", "3♠", "4♠", "5♠", "6♠", "8♠", "9♠")
    assert legal_actions(done) == [] and not is_legal(done, Pass())


# --- views -----------------------------------------------------------------------


def test_views_hide_other_hands_the_deck_and_the_kitty():
    st = pass_until_bury(new_round(CFG, 11), declare=True)
    ll = st.landlord
    other = (ll + 1) % N
    v_l, v_o = make_view(st, ll), make_view(st, other)
    assert v_l.hand == st.hands[ll] and v_o.hand == st.hands[other]
    assert v_l.kitty == st.kitty and v_l.buried == st.buried
    assert v_o.kitty is None and v_o.buried is None
    assert v_o.hand_sizes == tuple(len(h) for h in st.hands)
    for name in ("deck", "hands", "seed"):
        assert not hasattr(v_o, name)
    for value in vars_of(v_o):
        assert value is not st.deck and value is not st.hands
    assert v_o.landlord == ll and v_o.ctx is st.ctx and v_o.player == other


def vars_of(view):
    return [getattr(view, f) for f in view.__slots__]


def test_view_shares_tuples_instead_of_copying():
    st = at_play(SPADE_TRICK, calls=CALLS_A)
    after = play(st, "K♠")
    v = make_view(after, 3)
    assert v.trick is after.trick
    assert v.calls is st.calls and v.points_won == st.points_won
    assert v.lead is not None and v.phase is Phase.PLAY
