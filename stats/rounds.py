"""Per-round facts from finished RoundStates, plus simulation and aggregation.

`summarize_round` turns a DONE state into a flat dict, `simulate` plays matches and
collects those dicts, `aggregate` turns a list of them into the numbers for the report.
"""

from __future__ import annotations

import random
from collections import Counter
from typing import Callable

from engine.config import LANDLORD, GameConfig
from engine.runner import play_match
from engine.scoring import score_row
from engine.state import RoundState

PERCENTILES = (5, 25, 50, 75, 95)


# --- one round --------------------------------------------------------------


def _call_mode(state: RoundState) -> str:
    if state.solo_called:
        return "solo"
    alive = {call.alive for call in state.calls}
    if alive == {True}:
        return "alive"
    if alive == {False}:
        return "dead"
    return "mixed"


def _reinforced(history) -> bool:
    """Did a player declare the same card again over their own declaration?"""
    return any(a.player == b.player and a.card == b.card for a, b in zip(history, history[1:]))


def _landlord_off_lengths(state: RoundState) -> list[int]:
    """Landlord's cards per off suit after the bury, rebuilt from what they played."""
    ctx = state.ctx
    count: Counter = Counter()
    for rec in state.tricks:
        for seat, cards in rec.plays:
            if seat == state.landlord:
                count.update(ctx.effective_suit(c) for c in cards)
    off = [s for s in range(4) if ctx.trump_suit is None or s != int(ctx.trump_suit)]
    return [count[s] for s in off]


def summarize_round(state: RoundState) -> dict:
    """A finished round as a flat dict of facts (all derived from the state)."""
    res = state.result
    ctx = state.ctx
    cfg = state.config
    table = cfg.resolved_score_table
    landlord = state.landlord
    history = state.declare_history

    slot_tricks = list(state.slot_tricks)
    slot_wasted = [seat == landlord for seat in state.slots]
    others = [seat for seat in state.slots if seat is not None and seat != landlord]
    off_lengths = _landlord_off_lengths(state)

    return {
        "tricks": len(state.tricks),
        "trick_points": res.trick_points,
        "kitty_points": res.kitty_points,
        "kitty_multiplier": res.kitty_multiplier,
        "kitty_won": res.kitty_points * res.kitty_multiplier,
        "peasant_total": res.peasant_points,
        "winner": res.winner,
        "landlord_won": res.winner == LANDLORD,
        "base_gain": res.base_gain,
        "row": table.index(score_row(cfg, res.peasant_points)),
        "landlord": landlord,
        "trump_rank": ctx.trump_rank,
        "no_trump": ctx.trump_suit is None,
        "declarations": len(history),
        "contested": len({d.player for d in history}) >= 2,
        "reinforced": _reinforced(history),
        "redeals": state.redeals,
        "solo_called": state.solo_called,
        "call_mode": _call_mode(state),
        "slot_tricks": slot_tricks,
        "slot_wasted": slot_wasted,
        "friends": len(set(others)),
        "double_friend": len(others) != len(set(others)),
        "failed_throws": sum(1 for rec in state.tricks if rec.attempted is not None),
        "off_lengths": off_lengths,
        "shortest_off": min(off_lengths),
    }


# --- simulation -------------------------------------------------------------


def simulate(
    config: GameConfig,
    bot_factory: Callable[[int], object],
    rounds: int,
    seed: int,
    *,
    max_rounds_per_match: int = 20,
) -> list[dict]:
    """Play matches with fresh bots until `rounds` rounds are collected.

    `bot_factory(seed)` makes one bot; every seat gets its own seed derived from `seed`.
    """
    rng = random.Random(f"rounds/{seed}")
    rows: list[dict] = []
    while len(rows) < rounds:
        match_seed = rng.getrandbits(48)
        bots = [bot_factory(rng.getrandbits(48)) for _ in range(config.num_players)]
        for state in play_match(config, bots, match_seed, max_rounds=max_rounds_per_match):
            rows.append(summarize_round(state))
            if len(rows) == rounds:
                break
    return rows


# --- aggregation ------------------------------------------------------------


def percentile(sorted_values: list[float], q: float) -> float:
    """Nearest-rank percentile (q in 0..100) of an already sorted list."""
    if not sorted_values:
        return float("nan")
    k = max(0, min(len(sorted_values) - 1, -(-len(sorted_values) * q // 100) - 1))
    return sorted_values[int(k)]


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else float("nan")


def _spread(values) -> dict:
    """mean, n and the percentiles of a list of numbers."""
    s = sorted(values)
    out = {"n": len(s), "mean": _mean(s)}
    for q in PERCENTILES:
        out[f"p{q}"] = percentile(s, q)
    return out


def _fractions(values, keys=None) -> dict:
    """{value: fraction}; with `keys`, every key is present (0.0 if unseen)."""
    c = Counter(values)
    n = sum(c.values())
    keys = sorted(c) if keys is None else keys
    return {k: (c[k] / n if n else float("nan")) for k in keys}


def aggregate(rows: list[dict]) -> dict:
    """The numbers for the report. `rows` come from summarize_round, one table setup."""
    n = len(rows)
    if n == 0:
        raise ValueError("no rows to aggregate")
    frac = lambda pred, rs=rows: _mean(1.0 if pred(r) else 0.0 for r in rs)  # noqa: E731

    tricks = [r["tricks"] for r in rows]
    num_rows = max(r["row"] for r in rows) + 1
    num_slots = max(len(r["slot_tricks"]) for r in rows)
    calls = [r for r in rows if not r["solo_called"]]  # rounds that have friend slots

    slots = []
    for i in range(num_slots):
        cells = [(r["slot_tricks"][i], r["slot_wasted"][i]) for r in calls if len(r["slot_tricks"]) > i]
        slots.append({
            "reveal": _spread([t for t, wasted in cells if t is not None and not wasted]),
            "never": _mean(1.0 if t is None else 0.0 for t, _ in cells),
            "wasted": _mean(1.0 if w else 0.0 for _, w in cells),
        })  # fmt: skip
    all_cells = [(t, w) for r in calls for t, w in zip(r["slot_tricks"], r["slot_wasted"])]

    modes = {}
    for mode in ("dead", "alive", "mixed", "solo"):
        sub = [r for r in rows if r["call_mode"] == mode]
        modes[mode] = {
            "share": len(sub) / n,
            "n": len(sub),
            "landlord_win": frac(lambda r: r["landlord_won"], sub) if sub else float("nan"),
        }

    team_sizes = _fractions([1 + r["friends"] for r in rows])
    shortest = [r["shortest_off"] for r in rows]

    return {
        "n": n,
        "tricks": {"mean": _mean(tricks), "min": min(tricks), "max": max(tricks)},
        "trick_points": _spread(r["trick_points"] for r in rows),
        "peasant_total": _spread(r["peasant_total"] for r in rows),
        "kitty": {
            "buried_mean": _mean(r["kitty_points"] for r in rows),
            "won_mean": _mean(r["kitty_won"] for r in rows),
            "x2": frac(lambda r: r["kitty_multiplier"] == 2),
            "x4": frac(lambda r: r["kitty_multiplier"] == 4),
        },
        "rows": _fractions([r["row"] for r in rows], list(range(num_rows))),
        "landlord_win": frac(lambda r: r["landlord_won"]),
        "slots": slots,
        "reveal_all": _spread([t for t, w in all_cells if t is not None and not w]),
        "never_filled_slot": _mean(1.0 if t is None else 0.0 for t, _ in all_cells),
        "never_filled_round": frac(lambda r: None in r["slot_tricks"], calls) if calls else float("nan"),
        "wasted_slot": _mean(1.0 if w else 0.0 for _, w in all_cells),
        "wasted_round": frac(lambda r: any(r["slot_wasted"]), calls) if calls else float("nan"),
        "double_friend": frac(lambda r: r["double_friend"], calls) if calls else float("nan"),
        "team_sizes": team_sizes,
        "modes": modes,
        "no_trump": frac(lambda r: r["no_trump"]),
        "contested": frac(lambda r: r["contested"]),
        "reinforced": frac(lambda r: r["reinforced"]),
        "redealt": frac(lambda r: r["redeals"] > 0),
        "redeals_mean": _mean(r["redeals"] for r in rows),
        "declarations_mean": _mean(r["declarations"] for r in rows),
        "failed_throws_mean": _mean(r["failed_throws"] for r in rows),
        "failed_throws_any": frac(lambda r: r["failed_throws"] > 0),
        "void_off": frac(lambda r: r["shortest_off"] == 0),
        "short_off": frac(lambda r: r["shortest_off"] <= 2),
        "shortest_off_mean": _mean(shortest),
    }
