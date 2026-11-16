import pytest

from engine.config import LANDLORD, PEASANTS, GameConfig, KittyMultiplier
from engine.scoring import advance_level, score_round, score_row

CFG3 = GameConfig.for_players(7)  # 3 decks
CFG2 = GameConfig(num_players=5, num_decks=2, kitty_size=8, num_friends=1)  # 2 decks


@pytest.mark.parametrize(
    "points,winner,gain",
    [
        (0, LANDLORD, 3), (4, LANDLORD, 3),
        (5, LANDLORD, 2), (55, LANDLORD, 2),
        (60, LANDLORD, 1), (115, LANDLORD, 1),
        (120, PEASANTS, 0), (175, PEASANTS, 0),
        (180, PEASANTS, 1), (235, PEASANTS, 1),
        (240, PEASANTS, 2), (295, PEASANTS, 2),
        (300, PEASANTS, 3), (400, PEASANTS, 3),
    ],
)
def test_score_table_3_decks(points, winner, gain):
    assert score_row(CFG3, points)[1:] == (winner, gain)


@pytest.mark.parametrize(
    "points,winner,gain",
    [
        (0, LANDLORD, 3), (5, LANDLORD, 2), (35, LANDLORD, 2),
        (40, LANDLORD, 1), (75, LANDLORD, 1),
        (80, PEASANTS, 0), (115, PEASANTS, 0),
        (120, PEASANTS, 1), (155, PEASANTS, 1),
        (160, PEASANTS, 2), (195, PEASANTS, 2),
        (200, PEASANTS, 3), (300, PEASANTS, 3),
    ],
)
def test_score_table_2_decks(points, winner, gain):
    assert score_row(CFG2, points)[1:] == (winner, gain)


def test_advance_basic_and_cap():
    f = lambda lv, g, p=True: advance_level(lv, g, CFG3, can_pass_must_defend=p)
    assert f(3, 2) == 5
    assert f(13, 3) == 14
    assert f(14, 3) == 14


def test_must_defend_stops():
    f = lambda lv, g, p=True: advance_level(lv, g, CFG3, can_pass_must_defend=p)
    assert f(8, 3) == 10  # arriving stops
    assert f(9, 2) == 10
    assert f(10, 2) == 11  # leaves 10 on first step, then stops at J
    assert f(10, 2, False) == 10
    assert f(10, 1, False) == 10
    assert f(11, 3) == 14  # 12, 13, A
    assert f(11, 3, False) == 11
    assert f(12, 3) == 14


def _round(config=CFG3, **kw):
    n = config.num_players
    args = dict(
        levels=(5,) * n, landlord=0, friends=(1, 2), solo_called=False, trump_rank=5,
        points_won=(0,) * n, kitty_points=0, last_trick_winner=0,
        last_trick_width=1, last_trick_length=1,
    )
    args.update(kw)
    return score_round(config, **args)


def pts(peasant_total, n=7):
    """points_won with all peasant points on seat 3 (peasants are 3..n-1)."""
    p = [0] * n
    p[3] = peasant_total
    return tuple(p)


def test_landlord_wins():
    r = _round(points_won=pts(30))
    assert (r.winner, r.base_gain, r.gain) == (LANDLORD, 2, 2)
    assert r.new_levels == (7, 7, 7, 5, 5, 5, 5)
    assert r.landlord_team == (0, 1, 2)
    assert r.peasants == (3, 4, 5, 6)
    assert r.next_eligible == (0, 1, 2)
    assert r.game_winner is None
    assert not r.j_penalty_applied


def test_friend_points_do_not_count_for_peasants():
    p = [100, 100, 100, 10, 0, 0, 0]
    assert _round(points_won=tuple(p)).trick_points == 10


def test_peasants_win_levels_and_no_double():
    r = _round(points_won=pts(200), solo_called=True, friends=())
    assert (r.winner, r.base_gain, r.gain) == (PEASANTS, 1, 1)
    assert r.new_levels == (5, 6, 6, 6, 6, 6, 6)  # no friends: seats 1-6 are peasants
    assert r.next_eligible == (1, 2, 3, 4, 5, 6)


def test_peasants_win_no_level_change():
    r = _round(points_won=pts(130))
    assert r.winner == PEASANTS and r.new_levels == (5,) * 7
    assert r.next_eligible == (3, 4, 5, 6)


def test_peasant_on_must_defend_stays():
    r = _round(levels=(5, 5, 5, 10, 5, 5, 5), points_won=pts(250))
    assert r.new_levels[3] == 10
    assert r.new_levels[4] == 7


def test_landlord_passes_must_defend():
    r = _round(levels=(10, 5, 5, 5, 5, 5, 5), trump_rank=10, points_won=pts(0))
    assert r.new_levels[0] == 11


def test_friend_pass_option():
    lv = (5, 10, 5, 5, 5, 5, 5)
    assert _round(levels=lv, points_won=pts(0)).new_levels[1] == 11
    cfg = GameConfig.for_players(7, friends_pass_must_defend=False)
    assert _round(cfg, levels=lv, points_won=pts(0)).new_levels[1] == 10


def test_j_penalty():
    r = _round(levels=(11, 9, 10, 5, 5, 5, 5), trump_rank=11, points_won=pts(150))
    assert r.j_penalty_applied
    assert r.new_levels[:3] == (3, 4, 5)
    assert r.new_levels[3:] == (5, 5, 5, 5)
    r = _round(levels=(11, 5, 3, 5, 5, 5, 5), trump_rank=11, points_won=pts(150))
    assert r.new_levels[:3] == (3, 3, 3)  # 5 // 2 = 2 -> floor of 3


def test_j_penalty_not_applied():
    lv = (11, 9, 10, 5, 5, 5, 5)
    r = _round(levels=lv, trump_rank=11, points_won=pts(10))  # landlord wins
    assert not r.j_penalty_applied and r.new_levels[0] == 13
    r = _round(levels=lv, trump_rank=5, points_won=pts(150))  # not J
    assert not r.j_penalty_applied and r.new_levels[:3] == lv[:3]
    cfg = GameConfig.for_players(7, j_penalty=False)
    r = _round(cfg, levels=lv, trump_rank=11, points_won=pts(150))
    assert not r.j_penalty_applied and r.new_levels[:3] == lv[:3]


def test_kitty_multipliers():
    kw = dict(points_won=pts(100), kitty_points=20, last_trick_winner=3)
    r = _round(**kw, last_trick_width=1, last_trick_length=1)
    assert (r.kitty_multiplier, r.peasant_points) == (2, 140)
    r = _round(**kw, last_trick_width=2, last_trick_length=1)
    assert (r.kitty_multiplier, r.peasant_points) == (4, 180)
    assert r.winner == PEASANTS and r.base_gain == 1
    r = _round(**kw, last_trick_width=2, last_trick_length=2)
    assert r.kitty_multiplier == 4
    cfg = GameConfig.for_players(7, kitty_multiplier=KittyMultiplier(triple=6, tractor=8))
    assert _round(cfg, **kw, last_trick_width=3, last_trick_length=1).kitty_multiplier == 6
    assert _round(cfg, **kw, last_trick_width=2, last_trick_length=3).kitty_multiplier == 8


def test_landlord_team_last_trick_no_kitty():
    for winner in (0, 1):
        r = _round(points_won=pts(100), kitty_points=20, last_trick_winner=winner)
        assert r.kitty_multiplier == 0 and r.peasant_points == 100


def test_solo_doubling():
    r = _round(points_won=pts(0), solo_called=True, friends=())
    assert (r.base_gain, r.gain) == (3, 6)
    assert r.new_levels[0] == 10  # 5 + 6, stops at 10
    assert r.landlord_team == (0,)


def test_accidental_solo_not_doubled():
    r = _round(points_won=pts(0), solo_called=False, friends=())
    assert (r.base_gain, r.gain) == (3, 3)
    assert r.new_levels[0] == 8


def test_game_winner():
    lv = (14, 5, 5, 5, 5, 5, 5)
    r = _round(levels=lv, trump_rank=14, points_won=pts(10))
    assert r.game_winner == 0 and r.new_levels[0] == 14
    r = _round(levels=lv, trump_rank=14, points_won=pts(200))
    assert r.game_winner is None
    # a friend at A on the winning team does not win the game
    r = _round(levels=(5, 14, 5, 5, 5, 5, 5), trump_rank=5, points_won=pts(10))
    assert r.game_winner is None
