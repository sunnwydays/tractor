"""Run rounds and matches with bots."""

from __future__ import annotations

from collections import Counter

from engine.cards import points
from engine.config import GameConfig
from engine.state import Phase, RoundState, apply, is_legal, legal_actions, new_round

CHECK_EVERY = 4  # check=True also tests every legal_actions entry on every 4th step
from engine.view import make_view


def all_cards(st: RoundState) -> Counter:
    """Every card still accounted for: hands, undealt deck, current and past tricks, buried."""
    out: Counter = Counter()
    for h in st.hands:
        out.update(h)
    if st.phase is Phase.DEAL:
        out.update(st.deck[st.dealt :])
    for _, cards in st.trick:
        out.update(cards)
    for rec in st.tricks:
        for _, cards in rec.plays:
            out.update(cards)
    out.update(st.buried)
    return out


def play_round(
    config: GameConfig, bots, seed, *, levels=None, eligible=None, first_seat=0, check=False
) -> RoundState:
    """Play one round to the end. `bots` is indexed by seat.

    With check=True every chosen action must pass is_legal, the cards are counted
    after every step, and on a sample of steps every legal_actions entry must pass is_legal.
    """
    st = new_round(config, seed, levels=levels, eligible=eligible, first_seat=first_seat)
    expected = Counter(c for c in range(54) for _ in range(config.num_decks)) if check else None
    step = 0
    while st.phase is not Phase.DONE:
        p = st.to_act
        legal = legal_actions(st)
        action = bots[p].choose(make_view(st, p), legal)
        if check:
            assert legal, (st.phase, "no legal actions")
            assert is_legal(st, action), (st.phase, action)
            if step % CHECK_EVERY == 0:
                bad = [a for a in legal if not is_legal(st, a)]
                assert not bad, (st.phase, bad[:3])
            step += 1
        st = apply(st, action)
        if check:
            assert all_cards(st) == expected, "cards not conserved"
    if check:
        assert sum(st.points_won) + sum(points(c) for c in st.buried) == config.total_points
    return st


def play_match(config: GameConfig, bots, seed, *, max_rounds=50, check=False) -> list[RoundState]:
    """Rounds in a row; levels and declaring rights carry over until someone wins the game."""
    n = config.num_players
    rounds: list[RoundState] = []
    levels = eligible = None
    for k in range(max_rounds):
        st = play_round(
            config, bots, f"{seed}-{k}", levels=levels, eligible=eligible,
            first_seat=k % n, check=check,
        )  # fmt: skip
        rounds.append(st)
        if st.result.game_winner is not None:
            break
        levels, eligible = st.result.new_levels, st.result.next_eligible
    return rounds
