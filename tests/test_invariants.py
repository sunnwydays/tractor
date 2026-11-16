"""Whole-game invariants over many RandomBot rounds (via play_match, so later-round declaring is used)."""

import pytest

from bots.random_bot import RandomBot
from engine.cards import points
from engine.config import LANDLORD, PEASANTS, GameConfig
from engine.runner import all_cards, play_match, play_round
from engine.state import Phase

ROUNDS = 300


def rounds_for(n: int, count: int = ROUNDS):
    cfg = GameConfig.for_players(n)
    bots = [RandomBot(100 + i) for i in range(n)]
    out, seed = [], 0
    while len(out) < count:
        out += play_match(cfg, bots, seed, max_rounds=50, check=True)
        seed += 1
    return cfg, out[:count]


@pytest.mark.parametrize("n", [7, 8, 9])
def test_random_rounds_keep_every_invariant(n):
    cfg, rounds = rounds_for(n)
    assert len(rounds) == ROUNDS
    for st in rounds:
        assert st.phase is Phase.DONE and all(h == () for h in st.hands)
        kitty_points = sum(points(c) for c in st.buried)
        assert sum(st.points_won) + kitty_points == cfg.total_points
        assert len(st.buried) == cfg.kitty_size
        assert sum(len(r.plays) for r in st.tricks) == cfg.num_players * len(st.tricks)

        r = st.result
        peasants = set(range(cfg.num_players)) - {st.landlord, *st.friends}
        assert r.landlord_team == (st.landlord, *st.friends) and set(r.peasants) == peasants
        assert r.trick_points == sum(st.points_won[p] for p in peasants)
        assert r.kitty_points == kitty_points
        assert r.peasant_points == r.trick_points + r.kitty_points * r.kitty_multiplier
        assert r.winner in (LANDLORD, PEASANTS)
        assert (r.winner == PEASANTS) == (r.next_eligible == tuple(sorted(r.peasants)))
        assert len(r.new_levels) == cfg.num_players
        assert st.friends == tuple(dict.fromkeys(st.friends)) and st.landlord not in st.friends
        assert len(st.friends) <= cfg.num_friends
        last = st.tricks[-1]
        assert (r.kitty_multiplier == 0) == (last.winner not in peasants)
        for rec in st.tricks:
            assert sum(points(c) for _, cards in rec.plays for c in cards) == rec.points
            assert len({len(cards) for _, cards in rec.plays}) == 1


@pytest.mark.parametrize("n", [7, 8, 9])
def test_matches_carry_levels_and_eligibility_between_rounds(n):
    cfg = GameConfig.for_players(n)
    bots = [RandomBot(i) for i in range(n)]
    rounds = play_match(cfg, bots, 77, max_rounds=12)
    for prev, nxt in zip(rounds, rounds[1:]):
        assert nxt.levels == prev.result.new_levels and nxt.eligible == prev.result.next_eligible
        assert nxt.first_seat == (prev.first_seat + 1) % n
        assert nxt.landlord in nxt.eligible
        assert nxt.ctx.trump_rank == nxt.levels[nxt.landlord]


def test_same_seed_same_round():
    cfg = GameConfig.for_players(7)
    a = play_round(cfg, [RandomBot(i) for i in range(7)], 5)
    b = play_round(cfg, [RandomBot(i) for i in range(7)], 5)
    assert a == b
