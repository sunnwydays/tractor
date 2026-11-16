"""Write reports/round_stats.md: what whole rounds look like with bots at the table.

    python -m stats.round_report [--rounds 10000] [--seed 1] [--players 7 8 9]
                                 [--bots random greedy] [--workers N] [--out reports/round_stats.md]

The numbers do not depend on --workers: rounds are split into fixed-size chunks and
every chunk has its own seed.
"""

from __future__ import annotations

import argparse
import multiprocessing
import os
import random
import sys
import time
from pathlib import Path

from engine.config import LANDLORD, GameConfig
from stats.rounds import PERCENTILES, aggregate, simulate

CHUNK = 250  # rounds per job; fixed so results do not depend on the worker count
BOTS = ("random", "greedy")


# --- bots -------------------------------------------------------------------


def bot_factory(name: str):
    """A function seed -> bot. GreedyBot is imported only when asked for."""
    if name == "random":
        from bots.random_bot import RandomBot

        return RandomBot
    if name == "greedy":
        from bots.greedy_bot import GreedyBot

        return GreedyBot
    raise ValueError(f"unknown bot {name!r}; choose from {BOTS}")


# --- jobs -------------------------------------------------------------------


def make_jobs(players: list[int], bots: list[str], rounds: int, seed: int) -> list[tuple]:
    """(players, bot, chunk index, rounds in chunk, chunk seed), in a fixed order."""
    jobs = []
    for npl in players:
        for bot in bots:
            for i, start in enumerate(range(0, rounds, CHUNK)):
                chunk_seed = random.Random(f"{seed}/{npl}/{bot}/{i}").getrandbits(48)
                jobs.append((npl, bot, i, min(CHUNK, rounds - start), chunk_seed))
    return jobs


def run_job(job: tuple) -> tuple:
    npl, bot, i, count, chunk_seed = job
    rows = simulate(GameConfig.for_players(npl), bot_factory(bot), count, chunk_seed)
    return npl, bot, i, rows


def run_all(jobs: list[tuple], workers: int) -> dict:
    """{(players, bot): rows in chunk order}. Progress goes to stderr."""
    start = time.time()
    done: dict[tuple, list] = {}
    if workers <= 1:
        results = map(run_job, jobs)
        pool = None
    else:
        pool = multiprocessing.Pool(workers)
        results = pool.imap_unordered(run_job, jobs)
    try:
        for k, (npl, bot, i, rows) in enumerate(results, 1):
            done[(npl, bot, i)] = rows
            print(f"\r{k}/{len(jobs)} jobs, {time.time() - start:.0f}s", end="", file=sys.stderr, flush=True)
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    print(file=sys.stderr)
    merged: dict[tuple, list] = {}
    for (npl, bot, i) in sorted(done):
        merged.setdefault((npl, bot), []).extend(done[(npl, bot, i)])
    return merged


# --- formatting -------------------------------------------------------------


def pct(x: float) -> str:
    return "-" if x != x else f"{x * 100:.1f}%"


def f2(x: float) -> str:
    return "-" if x != x else f"{x:.2f}"


def f1(x: float) -> str:
    return "-" if x != x else f"{x:.1f}"


def table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return out + [""]


def _spread_rows(label: str, get, fmt, bots, aggs) -> list[list[str]]:
    """Rows 'label mean / p5 / ... / p95' for a spread dict taken with get(agg)."""
    rows = [[f"{label} mean"] + [fmt(get(aggs[b])["mean"]) for b in bots]]
    for q in PERCENTILES:
        rows.append([f"{label} p{q}"] + [fmt(get(aggs[b])[f"p{q}"]) for b in bots])
    return rows


# --- one player count -------------------------------------------------------


def build_section(config: GameConfig, bots: list[str], aggs: dict) -> str:
    A = lambda f: [f(aggs[b]) for b in bots]  # noqa: E731  one cell per bot
    cols = ["", *bots]
    n_slots = config.num_friends
    out = [
        f"## {config.num_players} players ({config.hand_size} cards each, kitty {config.kitty_size}, "
        f"{config.num_friends} friends)",
        "",
        "Rounds: " + ", ".join(f"{b} {aggs[b]['n']:,}" for b in bots),
        "",
    ]

    out += ["### Tricks and points", ""]
    out += [
        f"Each hand has {config.hand_size} cards, so a round has at most {config.hand_size} tricks; "
        "a pair, tractor or throw lead uses several cards per trick and shortens the round. "
        f"The decks hold {config.total_points} points.",
        "",
    ]
    rows = [
        ["tricks mean"] + A(lambda a: f2(a["tricks"]["mean"])),
        ["tricks min"] + A(lambda a: str(a["tricks"]["min"])),
        ["tricks max"] + A(lambda a: str(a["tricks"]["max"])),
        ["failed throws per round"] + A(lambda a: f"{a['failed_throws_mean']:.3f}"),
        ["rounds with a failed throw"] + A(lambda a: pct(a["failed_throws_any"])),
    ]
    out += table(cols, rows)
    out += ["Peasant points: from tricks alone, and the total after the kitty multiplier.", ""]
    rows = _spread_rows("trick points", lambda a: a["trick_points"], f1, bots, aggs)
    rows += _spread_rows("total", lambda a: a["peasant_total"], f1, bots, aggs)
    out += table(cols, rows)

    out += ["### Kitty", ""]
    out += [
        "Buried = face value of the kitty the landlord buried. Won = what the peasants get from it "
        "(buried x multiplier, 0 if the landlord team takes the last trick). "
        "x2 / x4 = the peasants took the last trick with a single / a pair or bigger.",
        "",
    ]
    rows = [
        ["buried points mean"] + A(lambda a: f1(a["kitty"]["buried_mean"])),
        ["won by peasants mean"] + A(lambda a: f1(a["kitty"]["won_mean"])),
        ["x2 fires"] + A(lambda a: pct(a["kitty"]["x2"])),
        ["x4 fires"] + A(lambda a: pct(a["kitty"]["x4"])),
    ]
    out += table(cols, rows)

    out += ["### Result", ""]
    out += ["Score-table rows by peasant total; `gain` is the base levels before any solo bonus.", ""]
    rows = []
    for i, (low, side, gain) in enumerate(config.resolved_score_table):
        who = "landlord" if side == LANDLORD else "peasants"
        rows.append([f"{low}+ pts: {who} win, gain {gain}"] + A(lambda a, i=i: pct(a["rows"].get(i, 0.0))))
    rows.append(["**landlord team wins**"] + A(lambda a: pct(a["landlord_win"])))
    out += table(cols, rows)

    out += ["### Friends", ""]
    out += [
        "Reveal = the trick number in which the slot's card was played (wasted slots, where the "
        "landlord played the card, are left out). Solo rounds have no slots and are left out of "
        "everything except the mode table and team sizes.",
        "",
    ]
    rows = []
    for i in range(n_slots):
        rows.append([f"slot {i + 1} reveal mean / median"] + A(lambda a, i=i: _mm(a, i)))
    rows.append(["all slots reveal mean"] + A(lambda a: f1(a["reveal_all"]["mean"])))
    for q in PERCENTILES:
        rows.append([f"all slots reveal p{q}"] + A(lambda a, q=q: f1(a["reveal_all"][f"p{q}"])))
    out += table(cols, rows)
    rows = []
    for i in range(n_slots):
        rows.append([f"slot {i + 1} never filled"] + A(lambda a, i=i: pct(a["slots"][i]["never"]) if i < len(a["slots"]) else "-"))
    rows += [
        ["any slot never filled (per round)"] + A(lambda a: pct(a["never_filled_round"])),
        ["slots never filled (per slot)"] + A(lambda a: pct(a["never_filled_slot"])),
        ["any slot wasted (landlord played it)"] + A(lambda a: pct(a["wasted_round"])),
        ["slots wasted (per slot)"] + A(lambda a: pct(a["wasted_slot"])),
        ["one player fills two slots"] + A(lambda a: pct(a["double_friend"])),
    ]
    out += table(cols, rows)

    out += ["**Team size** (landlord + distinct friends)", ""]
    sizes = sorted({s for b in bots for s in aggs[b]["team_sizes"]})
    rows = [[f"{s} players"] + A(lambda a, s=s: pct(a["team_sizes"].get(s, 0.0))) for s in sizes]
    out += table(cols, rows)

    out += ["**Call mode** (dead = every call is dead, alive = every call alive, mixed = both)", ""]
    rows = []
    for mode in ("dead", "alive", "mixed", "solo"):
        rows.append([f"{mode}: share of rounds"] + A(lambda a, m=mode: pct(a["modes"][m]["share"])))
        rows.append([f"{mode}: landlord win"] + A(lambda a, m=mode: pct(a["modes"][m]["landlord_win"])))
    out += table(cols, rows)

    out += ["### Declaring", ""]
    rows = [
        ["无主 (joker declaration)"] + A(lambda a: pct(a["no_trump"])),
        ["contested (2+ players declared)"] + A(lambda a: pct(a["contested"])),
        ["reinforced (same player, same card, more copies)"] + A(lambda a: pct(a["reinforced"])),
        ["declarations per round"] + A(lambda a: f2(a["declarations_mean"])),
        ["redealt (nobody declared)"] + A(lambda a: pct(a["redealt"])),
        ["redeals per round"] + A(lambda a: f"{a['redeals_mean']:.3f}"),
    ]
    out += table(cols, rows)

    out += ["### Landlord after the kitty swap", ""]
    out += [
        "Off-suit lengths of the landlord's hand after burying. This depends on each table's bury "
        "policy (RandomBot buries at random), so the greedy column is the meaningful one.",
        "",
    ]
    rows = [
        ["P(void in at least one off suit)"] + A(lambda a: pct(a["void_off"])),
        ["P(<= 2 cards in at least one off suit)"] + A(lambda a: pct(a["short_off"])),
        ["mean shortest off-suit length"] + A(lambda a: f2(a["shortest_off_mean"])),
    ]
    out += table(cols, rows)
    return "\n".join(out)


def _mm(a: dict, i: int) -> str:
    if i >= len(a["slots"]):
        return "-"
    r = a["slots"][i]["reveal"]
    return f"{f1(r['mean'])} / {f1(r['p50'])}"


def config_lines(config: GameConfig) -> list[str]:
    d = GameConfig.for_players(config.num_players)
    km = d.kitty_multiplier
    return [
        f"- Start level {d.start_level}, must-defend levels {list(d.must_defend_levels)}, "
        f"J penalty {d.j_penalty}, win by defending A.",
        f"- Permanent trump ranks {list(d.permanent_trump_ranks)}; nobody declares -> {d.no_declaration}.",
        f"- Solo allowed {d.allow_solo} (x{d.solo_win_multiplier} on a win); alive-call landlord copy: "
        f"{d.alive_landlord_copy}; split triple to follow a pair: {d.split_triple_to_follow_pair}.",
        f"- Kitty multiplier: single x{km.single}, pair x{km.pair}, triple x{km.triple}, tractor x{km.tractor}.",
        f"- Score table (peasant points -> result): {list(d.resolved_score_table)}.",
    ]


# --- CLI --------------------------------------------------------------------


def build_report(args, merged: dict, runtime: float) -> str:
    cmd = (
        f"python -m stats.round_report --rounds {args.rounds} --seed {args.seed} "
        f"--players {' '.join(map(str, args.players))} --bots {' '.join(args.bots)} --out {args.out}"
    )
    head = [
        "# Round statistics",
        "",
        f"- Rounds per player count and bot: {args.rounds:,}",
        f"- Seed: {args.seed}",
        f"- Regenerate: `{cmd}`",
        f"- Bots: {', '.join(args.bots)}",
        "- Each round comes from a match of up to 20 rounds with fresh bots, so levels and trump ranks vary.",
        "- Everything below the Run time line is independent of the worker count.",
        f"- Run time: {runtime:.0f}s",
        "",
        "Config defaults (same for every player count unless the player table says otherwise):",
        "",
        *config_lines(GameConfig.for_players(args.players[0])),
        "",
    ]
    sections = []
    for npl in args.players:
        aggs = {b: aggregate(merged[(npl, b)]) for b in args.bots}
        sections.append(build_section(GameConfig.for_players(npl), args.bots, aggs))
    return "\n".join(head) + "\n" + "\n".join(sections) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m stats.round_report")
    ap.add_argument("--rounds", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--players", type=int, nargs="+", default=[7, 8, 9])
    ap.add_argument("--bots", nargs="+", default=list(BOTS), choices=BOTS)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--out", default="reports/round_stats.md")
    args = ap.parse_args(argv)

    t0 = time.time()
    jobs = make_jobs(args.players, args.bots, args.rounds, args.seed)
    merged = run_all(jobs, args.workers)
    runtime = time.time() - t0

    text = build_report(args, merged, runtime)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")
    print(f"runtime {runtime:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
