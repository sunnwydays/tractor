from itertools import combinations
from math import isclose

import pytest

from engine.cards import Suit, TrumpContext
from engine.config import GameConfig
from stats.exact import (
    Universe,
    copies_dist,
    kitty_points_dist,
    length_dist,
    spread_dist,
)
from stats.report import build_report
from stats.simulate import simulate


# --- exact sanity -----------------------------------------------------------


@pytest.mark.parametrize("n", [7, 8, 9])
def test_distributions_sum_to_one(n):
    cfg = GameConfig.for_players(n)
    N, h, k = cfg.total_cards, cfg.hand_size, cfg.kitty_size
    assert isclose(sum(copies_dist(N, 3, h)), 1)
    assert isclose(sum(copies_dist(N, 3, h + k)), 1)
    assert isclose(sum(length_dist(N, h, 39)), 1)
    kd = kitty_points_dist(cfg)
    assert isclose(sum(kd.values()), 1)
    assert isclose(sum(p * v for p, v in kd.items()), k * 300 / 162)
    for r in range(4):
        assert isclose(sum(spread_dist(r, n - 1, h).values()), 1)


def test_spread_patterns():
    assert set(spread_dist(3, 6, 20)) == {(3,), (2, 1), (1, 1, 1)}
    assert spread_dist(0, 6, 20) == {(): 1.0}
    assert isclose(spread_dist(1, 6, 20)[(1,)], 1)


def test_e_sets_single_type():
    u = Universe(162, 23, 3)
    for w in (1, 2, 3):
        assert isclose(u.e_sets(1, w), u.p_type_at_least(w))
        assert isclose(u.p_any_set(1, w), u.p_type_at_least(w))


# --- brute force on a tiny universe -----------------------------------------


def test_bruteforce_small_universe():
    copies, n_types, hand = 2, 6, 5
    total = copies * n_types
    levels = [[0], [1, 2], [3]]  # types 4, 5 are outside the "suit"
    suit_types = [t for lv in levels for t in lv]
    u = Universe(total, hand, copies)

    n_hands = any_set = any_tractor = 0
    sets_sum = tractors_sum = 0
    for combo in combinations(range(total), hand):
        n_hands += 1
        cnt = [0] * n_types
        for card in combo:
            cnt[card // copies] += 1
        has = [any(cnt[t] >= 2 for t in lv) for lv in levels]
        n_sets = sum(1 for t in suit_types if cnt[t] >= 2)
        runs, i = 0, 0
        while i < len(has):
            if has[i]:
                j = i
                while j + 1 < len(has) and has[j + 1]:
                    j += 1
                runs += j > i
                i = j + 1
            else:
                i += 1
        any_set += n_sets > 0
        sets_sum += n_sets
        any_tractor += runs > 0
        tractors_sum += runs

    sizes = [len(lv) for lv in levels]
    assert isclose(u.p_any_set(len(suit_types), 2), any_set / n_hands)
    assert isclose(u.e_sets(len(suit_types), 2), sets_sum / n_hands)
    assert isclose(u.p_any_tractor(sizes, 2), any_tractor / n_hands)
    assert isclose(u.e_tractors(sizes, 2), tractors_sum / n_hands)


# --- agreement and determinism ----------------------------------------------

HEARTS_3 = TrumpContext(3, Suit.HEARTS)


@pytest.mark.parametrize(
    "players,ctx,deals",
    [
        (7, HEARTS_3, 5000),
        (8, HEARTS_3, 2000),
        (9, HEARTS_3, 2000),
        (7, TrumpContext(3, None), 2000),
    ],
)
def test_sim_agrees_with_exact(players, ctx, deals):
    cfg = GameConfig.for_players(players)
    sim = simulate(cfg, ctx, deals, seed=11)
    text, checks = build_report(cfg, ctx, sim)
    assert len(checks) >= 100
    worst = max(checks, key=lambda c: abs(c.z))
    assert abs(worst.z) < 5, (worst.label, worst.sim, worst.exact, worst.z)
    assert f"## {players} players" in text


def test_determinism():
    cfg = GameConfig.for_players(7)
    a = simulate(cfg, HEARTS_3, 300, seed=5)
    b = simulate(cfg, HEARTS_3, 300, seed=5)
    assert a == b
