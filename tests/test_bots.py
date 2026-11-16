"""GreedyBot: always legal over full rounds, and the main rules on hand-built states."""

from dataclasses import replace

import pytest

from bots.greedy_bot import GreedyBot
from engine.cards import Suit, parse_card
from engine.config import GameConfig
from engine.runner import play_round
from engine.state import (
    BuryCard,
    CallFriends,
    Declare,
    FriendCall,
    Pass,
    Phase,
    Play,
    apply,
    legal_actions,
    state_for_play,
)
from engine.view import make_view


class CheckedGreedy(GreedyBot):
    def choose(self, view, legal):
        action = super().choose(view, legal)
        assert action in legal
        return action


@pytest.mark.parametrize("players", [7, 8, 9])
def test_always_returns_a_legal_action(players):
    cfg = GameConfig.for_players(players)
    for seed in range(30):
        bots = [CheckedGreedy(seed=i) for i in range(players)]
        st = play_round(cfg, bots, f"greedy-{players}-{seed}", check=True)
        assert st.phase is Phase.DONE


# --- hand-built states -------------------------------------------------------

CFG = GameConfig.for_players(7)
C = parse_card


def cards(text):
    return [C(t) for t in text.split()]


def mid_trick(hands, plays, *, me, calls=(), friends=(), landlord=0):
    """Trump 9 of hearts. Seats play `plays` in order from `landlord`; returns (view, legal) for `me`."""
    st = state_for_play(
        CFG, hands, landlord, 9, Suit.HEARTS, calls=calls, friends=friends
    )
    for cs in plays:
        st = apply(st, Play(tuple(sorted(cs))))
    assert st.to_act == me
    return make_view(st, me), legal_actions(st)


def pad(hands):
    return hands + [cards("3D")] * (7 - len(hands))


def test_feeds_points_to_a_teammate_holding_the_trick():
    hands = pad([cards("AS 4D"), cards("3S 5D"), cards("4S 6D"), cards("KS 4S 5S"), cards("8D"), cards("8D"), cards("8D")])
    view, legal = mid_trick(hands, [cards("AS"), cards("3S"), cards("4S")], me=3, friends=(3,))
    assert GreedyBot().choose(view, legal) == Play((C("KS"),))


def test_wins_a_point_trick_cheaply():
    hands = pad([cards("10S 4D"), cards("QS AS 4S"), cards("3D")])
    view, legal = mid_trick(hands, [cards("10S")], me=1)
    assert GreedyBot().choose(view, legal) == Play((C("QS"),))


def test_dumps_a_low_pointless_card_when_it_cannot_win():
    hands = pad([cards("AS 4D"), cards("KS 4S 3S 5S"), cards("3D")])
    view, legal = mid_trick(hands, [cards("AS")], me=1)
    assert GreedyBot().choose(view, legal) == Play((C("3S"),))


def test_plays_its_called_card_to_reveal():
    call = FriendCall(C("AC"), 1)
    hands = pad([cards("4C 4D"), cards("3C 5D"), cards("AC 5C 6D")])
    view, legal = mid_trick(hands, [cards("4C"), cards("3C")], me=2, calls=(call,))
    # 5C would feed more points; the called card reveals instead
    assert GreedyBot().choose(view, legal) == Play((C("AC"),))


def test_buries_a_point_free_short_suit_card():
    hands = pad([cards("3S 4C 4C 6C KC 5D 8D AD 3H 4H"), cards("3D")])
    st = state_for_play(CFG, hands, 0, 9, Suit.HEARTS)
    view = replace(make_view(st, 0), phase=Phase.BURY)
    legal = [BuryCard(c) for c in sorted(set(view.hand))]
    assert GreedyBot().choose(view, legal) == BuryCard(C("3S"))


def _deal_view(hand, *, complete=False, declaration=None):
    hands = pad([cards("3D"), hand])
    st = state_for_play(CFG, hands, 0, 9, Suit.HEARTS)
    view = replace(make_view(st, 1), phase=Phase.DEAL, deal_complete=complete, declaration=declaration)
    legal = [Pass(), *(Declare(c, 1) for c in sorted(set(hand)) if c % 13 + 2 == 3)]
    return view, legal


def test_declares_only_with_length():
    short, legal = _deal_view(cards("3H 4H"))
    assert GreedyBot().choose(short, legal) == Pass()
    long, legal = _deal_view(cards("2S 3S 3H 5H 6H 8H 2C 4C 7C 4D"))
    assert GreedyBot().choose(long, legal) == Declare(C("3H"), 1)


def test_closing_round_someone_must_declare():
    view, legal = _deal_view(cards("3H 4S 6C 8D 10D 5S 7C"), complete=True)
    assert isinstance(GreedyBot().choose(view, legal), Declare)


def test_calls_top_cards_of_a_suit():
    hands = pad([cards("AS AS 3C 4C"), cards("3D")])
    st = state_for_play(CFG, hands, 0, 9, Suit.HEARTS)
    view = replace(make_view(st, 0), phase=Phase.CALL, buried=(C("KC"),))
    legal = [CallFriends((FriendCall(C("AC"), 1), FriendCall(C("AC"), 2))), CallFriends((FriendCall(C("AD"), 1), FriendCall(C("AD"), 2)))]
    choice = GreedyBot().choose(view, legal)
    assert choice in legal
    assert choice.calls == (FriendCall(C("AC"), 1), FriendCall(C("AC"), 2))  # holds no AC: two alive calls


def test_boss_lead_beats_a_longer_suit():
    hands = pad([cards("AS 4C 5C 6C 8C"), cards("3D")])
    st = state_for_play(CFG, hands, 0, 9, Suit.HEARTS)
    view, legal = make_view(st, 0), legal_actions(st)
    assert GreedyBot().choose(view, legal) == Play((C("AS"),))
