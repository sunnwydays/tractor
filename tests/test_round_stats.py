import math

import pytest

from bots.random_bot import RandomBot
from engine.config import GameConfig
from stats import round_report
from stats.rounds import aggregate, percentile, simulate, summarize_round


@pytest.fixture(scope="module")
def rows7():
    return simulate(GameConfig.for_players(7), RandomBot, 12, 5)


def test_simulate_count_and_determinism(rows7):
    assert len(rows7) == 12
    assert rows7 == simulate(GameConfig.for_players(7), RandomBot, 12, 5)


@pytest.mark.parametrize("players", [7, 8, 9])
def test_summary_is_consistent(players):
    cfg = GameConfig.for_players(players)
    for r in simulate(cfg, RandomBot, 6, players):
        assert 1 <= r["tricks"] <= cfg.hand_size  # pair / tractor / throw leads use several cards per trick
        assert r["peasant_total"] == r["trick_points"] + r["kitty_won"]
        assert r["kitty_won"] == r["kitty_points"] * r["kitty_multiplier"]
        assert r["landlord_won"] == (r["winner"] == "landlord")
        assert len(r["slot_tricks"]) == (0 if r["solo_called"] else cfg.num_friends)
        assert (r["call_mode"] == "solo") == r["solo_called"]
        assert r["friends"] <= cfg.num_friends
        assert len(r["off_lengths"]) == (4 if r["no_trump"] else 3)
        assert r["shortest_off"] == min(r["off_lengths"])
        assert r["declarations"] >= 1
        assert sum(r["off_lengths"]) <= cfg.hand_size


def test_summary_matches_state():
    from bots.random_bot import RandomBot as B
    from engine.runner import play_round

    cfg = GameConfig.for_players(7)
    st = play_round(cfg, [B(i) for i in range(7)], "x1")
    r = summarize_round(st)
    assert r["peasant_total"] == st.result.peasant_points
    assert r["base_gain"] == st.result.base_gain
    assert r["landlord"] == st.landlord
    assert r["trump_rank"] == st.ctx.trump_rank
    assert r["failed_throws"] == sum(1 for t in st.tricks if t.attempted)
    # the landlord's post-bury hand, rebuilt from their plays, has the normal hand size
    played = sum(len(c) for t in st.tricks for s, c in t.plays if s == st.landlord)
    assert played == cfg.hand_size


def _row(**kw):
    base = {
        "tricks": 10, "trick_points": 100, "kitty_points": 10, "kitty_multiplier": 0, "kitty_won": 0,
        "peasant_total": 100, "winner": "landlord", "landlord_won": True, "base_gain": 1, "row": 0,
        "landlord": 0, "trump_rank": 3, "no_trump": False, "declarations": 1, "contested": False,
        "reinforced": False, "redeals": 0, "solo_called": False, "call_mode": "dead",
        "slot_tricks": [2, 4], "slot_wasted": [False, False], "friends": 2, "double_friend": False,
        "failed_throws": 0, "off_lengths": [3, 4, 5], "shortest_off": 3,
    }  # fmt: skip
    return {**base, **kw}


def test_aggregate_hand_made():
    rows = [
        _row(),
        _row(kitty_multiplier=2, kitty_won=20, peasant_total=120, winner="peasants", landlord_won=False,
             row=1, slot_tricks=[None, 6], friends=1, call_mode="alive", no_trump=True,
             contested=True, redeals=2, shortest_off=0, off_lengths=[0, 4, 5, 6]),
        _row(solo_called=True, call_mode="solo", slot_tricks=[], slot_wasted=[], friends=0,
             kitty_multiplier=4, kitty_won=40, shortest_off=2, off_lengths=[2, 3, 4]),
        _row(slot_wasted=[True, False], double_friend=True, friends=1, call_mode="mixed"),
    ]
    a = aggregate(rows)
    assert a["n"] == 4
    assert a["tricks"] == {"mean": 10, "min": 10, "max": 10}
    assert a["kitty"]["x2"] == 0.25 and a["kitty"]["x4"] == 0.25
    assert a["kitty"]["won_mean"] == 15
    assert a["landlord_win"] == 0.75
    assert a["rows"] == {0: 0.75, 1: 0.25}
    assert a["no_trump"] == 0.25 and a["contested"] == 0.25
    assert a["redealt"] == 0.25 and a["redeals_mean"] == 0.5
    assert a["void_off"] == 0.25 and a["short_off"] == 0.5
    assert a["shortest_off_mean"] == (3 + 0 + 2 + 3) / 4
    # slots exist in 3 non-solo rounds
    assert a["never_filled_slot"] == pytest.approx(1 / 6)
    assert a["never_filled_round"] == pytest.approx(1 / 3)
    assert a["wasted_slot"] == pytest.approx(1 / 6)
    assert a["double_friend"] == pytest.approx(1 / 3)
    assert a["slots"][0]["reveal"]["n"] == 1  # one wasted, one never filled
    assert a["slots"][1]["reveal"]["mean"] == pytest.approx((4 + 6 + 4) / 3)
    assert a["team_sizes"] == {1: 0.25, 2: 0.5, 3: 0.25}
    assert a["modes"]["solo"]["share"] == 0.25
    assert a["modes"]["alive"]["landlord_win"] == 0.0
    assert math.isnan(aggregate([_row()])["modes"]["mixed"]["landlord_win"])


def test_percentile():
    v = list(range(1, 101))
    assert percentile(v, 5) == 5
    assert percentile(v, 50) == 50
    assert percentile(v, 95) == 95
    assert percentile([7], 25) == 7


def test_report_end_to_end(tmp_path):
    out = tmp_path / "sub" / "r.md"
    argv = ["--rounds", "20", "--seed", "3", "--players", "7", "--bots", "random",
            "--workers", "1", "--out", str(out)]  # fmt: skip
    assert round_report.main(argv) == 0
    text = out.read_text(encoding="utf-8")
    assert "## 7 players" in text and "### Friends" in text and "### Declaring" in text
    # deterministic apart from the Run time line and independent of the worker count
    out2 = tmp_path / "r2.md"
    round_report.main(argv[:-4] + ["--workers", "2", "--out", str(out2)])

    def body(t):
        return [ln for ln in t.splitlines() if not ln.startswith("- Run time") and "--out" not in ln]

    assert body(text) == body(out2.read_text(encoding="utf-8"))


def test_jobs_do_not_depend_on_workers():
    jobs = round_report.make_jobs([7, 8], ["random"], 600, 1)
    assert [j[3] for j in jobs] == [250, 250, 100, 250, 250, 100]
    assert jobs == round_report.make_jobs([7, 8], ["random"], 600, 1)
