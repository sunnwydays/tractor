"""Write reports/deal_stats.md: Monte Carlo vs exact deal statistics.

    python -m stats.report [--deals N] [--seed S] [--trump-rank R] [--trump-suit X]
                           [--players 7 8 9] [--out PATH]
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from engine.cards import TRUMP, TrumpContext, card_name, parse_rank, parse_suit
from engine.config import GameConfig
from stats.exact import Universe, copies_dist, kitty_points_dist, length_dist, spread_dist
from stats.simulate import STRUCTS, SimResult, simulate


@dataclass
class Check:
    label: str
    sim: float
    se: float
    exact: float

    @property
    def z(self) -> float:
        diff = self.sim - self.exact
        if self.se == 0:
            return 0.0 if diff == 0 else math.inf
        return diff / self.se


# --- formatting -------------------------------------------------------------


def pct(x: float) -> str:
    return f"{x * 100:.4f}%" if x < 0.001 else f"{x * 100:.2f}%"


def num(x: float) -> str:
    return f"{x:.6f}" if x < 0.001 else f"{x:.4f}"


def table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return out + [""]


# --- checks -----------------------------------------------------------------


class Checker:
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.checks: list[Check] = []

    def prob(self, label: str, hits: float, n: int, exact: float) -> float:
        """Record a sim-vs-exact probability check; returns the sim value."""
        if n == 0:
            return math.nan
        sim = hits / n
        se = math.sqrt(exact * (1 - exact) / n)
        if se == 0 and sim == exact:
            return sim
        self.checks.append(Check(f"{self.prefix} {label}", sim, se or 1e-12, exact))
        return sim

    def mean(self, label: str, total: float, total_sq: float, n: int, exact: float) -> float:
        sim = total / n
        var = max(total_sq - total * total / n, 0) / (n - 1) if n > 1 else 0
        se = math.sqrt(var / n)
        if se == 0:
            se = math.sqrt(exact / n)
        self.checks.append(Check(f"{self.prefix} {label}", sim, se, exact))
        return sim


def _hist_mean(hist) -> tuple[int, int, int]:
    n = sum(hist.values())
    return n, sum(k * v for k, v in hist.items()), sum(k * k * v for k, v in hist.items())


def _percentile(pmf: dict[int, float], q: float):
    cum = 0.0
    for v in sorted(pmf):
        cum += pmf[v]
        if cum >= q - 1e-12:
            return v
    return max(pmf)


def _pattern_label(parts: tuple[int, ...], r: int) -> str:
    if r == 1:
        return "1 player holds it"
    if len(parts) == 1:
        return f"one player holds all {r}"
    if all(p == 1 for p in parts):
        return f"{r} players hold 1 each"
    words = ["one player holds %d" % parts[0]] + [f"another holds {p}" for p in parts[1:]]
    return ", ".join(words)


# --- one player count -------------------------------------------------------


def build_report(config: GameConfig, ctx: TrumpContext, sim: SimResult) -> tuple[str, list[Check]]:
    n = sim.n_deals
    N, h, k, d = config.total_cards, config.hand_size, config.kitty_size, config.num_decks
    H = h + k
    U = Universe(N, h, d)
    ck = Checker(f"[{config.num_players}p]")
    out: list[str] = [
        f"## {config.num_players} players ({h} cards each, kitty {k}, {config.num_friends} friends)",
        "",
    ]

    groups = ctx.groups
    sizes = {g: [len(lv) for lv in ctx.levels(g)] for g in groups}
    ntypes = {g: sum(sizes[g]) for g in groups}
    ncards = {g: d * ntypes[g] for g in groups}
    gname = {g: ctx.group_name(g) for g in groups}

    # 1. pairs, triples, tractors
    out += ["### Pairs, triples and tractors", ""]
    titles = {
        "pairs": ("Pairs", "pairs"),
        "triples": ("Triples", "triples"),
        "pair_tractors": ("Tractors of pairs", "pair tractors"),
        "triple_tractors": ("Tractors of triples", "triple tractors"),
    }
    for s in STRUCTS:
        w = 3 if s.startswith("triple") else 2
        rows = []
        for g in groups:
            if s in ("pairs", "triples"):
                p_ex, e_ex = U.p_any_set(ntypes[g], w), U.e_sets(ntypes[g], w)
            else:
                p_ex, e_ex = U.p_any_tractor(sizes[g], w), U.e_tractors(sizes[g], w)
            n1, s1, s2 = sim.structs[(g, s)]
            lab = f"{gname[g]} {titles[s][1]}"
            p_sim = ck.prob(f"P(>=1) {lab}", n1, n, p_ex)
            e_sim = ck.mean(f"E[count] {lab}", s1, s2, n, e_ex)
            rows.append(
                [f"{gname[g]} ({ncards[g]} cards)", pct(p_sim), pct(p_ex), num(e_sim), num(e_ex)]
            )
        out += [f"**{titles[s][0]}**", ""]
        out += table(["Suit", "P(≥1) sim", "P(≥1) exact", "E[count] sim", "E[count] exact"], rows)

    # 2. jokers
    out += ["### Jokers", ""]
    jrows = []
    for lab, hits, ex in (
        ("big-joker pair", sim.big_pair, U.joker_pair_one()),
        ("small-joker pair", sim.small_pair, U.joker_pair_one()),
        ("any joker pair (declare 无主)", sim.any_joker_pair, U.joker_pair_any()),
        ("joker triple (3 identical jokers)", sim.joker_triple, U.joker_triple_any()),
    ):
        jrows.append([lab, pct(ck.prob(lab, hits, n, ex)), pct(ex)])
    out += table(["Hand has", "sim", "exact"], jrows)

    # 3. void and short suits
    out += ["### Void and short suits", ""]
    vrows = []
    for g in groups:
        pmf = length_dist(N, h, ncards[g])
        hist = sim.lengths[g]
        v_ex, s_ex = pmf[0], sum(pmf[:3])
        v_sim = ck.prob(f"P(void) {gname[g]}", hist[0], n, v_ex)
        s_sim = ck.prob(f"P(<=2 cards) {gname[g]}", sum(hist[i] for i in range(3)), n, s_ex)
        vrows.append([f"{gname[g]} ({ncards[g]} cards)", pct(v_sim), pct(v_ex), pct(s_sim), pct(s_ex)])
    out += table(["Suit", "P(void) sim", "P(void) exact", "P(≤2 cards) sim", "P(≤2 cards) exact"], vrows)

    out += ["**Length distribution** (cells: sim / exact; lengths below 0.1% omitted)", ""]
    pmfs = {g: length_dist(N, h, ncards[g]) for g in groups}
    lrows = []
    for L in range(h + 1):
        cells = []
        for g in groups:
            ex = pmfs[g][L]
            if ex >= 0.001:
                sm = ck.prob(f"P(length {L}) {gname[g]}", sim.lengths[g].get(L, 0), n, ex)
                cells.append(f"{pct(sm)} / {pct(ex)}")
            else:
                cells.append("-")
        if any(c != "-" for c in cells):
            lrows.append([str(L)] + cells)
    out += table(["length"] + [gname[g] for g in groups], lrows)

    # 4. trump length
    out += ["### Trump length", ""]
    hist = sim.lengths[TRUMP]
    pmf = length_dist(N, h, ncards[TRUMP])
    _, ts, ts2 = _hist_mean(hist)
    t_ex = h * ncards[TRUMP] / N
    t_sim = ck.mean("mean trump length", ts, ts2, n, t_ex)
    out += [f"Mean trump cards in hand: sim {t_sim:.3f}, exact {t_ex:.3f} ({ncards[TRUMP]} trump cards).", ""]
    trows = []
    for kk in range(h + 1):
        ex = sum(pmf[kk:])
        if 0.001 <= ex <= 0.999:
            sm = ck.prob(f"P(trump length >= {kk})", sum(v for L, v in hist.items() if L >= kk), n, ex)
            trows.append([str(kk), pct(sm), pct(ex)])
    out += table(["k", "P(≥k) sim", "P(≥k) exact"], trows)

    # 5. kitty points
    out += ["### Kitty points", ""]
    out += ["The kitty as dealt, before the landlord buries.", ""]
    kd = kitty_points_dist(config)
    kn, ks, ks2 = _hist_mean(sim.kitty_hist)
    k_ex = k * config.total_points / N
    k_exact_from_dist = sum(p * v for p, v in kd.items())
    assert abs(k_ex - k_exact_from_dist) < 1e-9
    k_sim = ck.mean("kitty mean points", ks, ks2, n, k_ex)
    out += [f"Mean kitty points: sim {k_sim:.3f}, exact {k_ex:.3f}.", ""]
    sim_pmf = {p: v / n for p, v in sim.kitty_hist.items()}
    prow = [
        [f"{q}%", str(_percentile(sim_pmf, q / 100)), str(_percentile(kd, q / 100))]
        for q in (10, 25, 50, 75, 90, 95, 99)
    ]
    out += table(["percentile", "sim", "exact"], prow)
    drow = []
    for pts, ex in kd.items():
        if ex >= 0.0005:
            sm = ck.prob(f"kitty points = {pts}", sim.kitty_hist.get(pts, 0), n, ex)
            drow.append([str(pts), pct(sm), pct(ex)])
    out += table(["points", "sim", "exact"], drow)

    # 6. friend calls
    out += ["### Friend calls", ""]
    out += [
        f"Call card: {card_name(sim.call_card)} (every non-trump card is symmetric). Seat 0 is the landlord.",
        f"With {d} copies, if the landlord holds c there are {d} - c out there. "
        f"A dead call for ({d} - c) friends on that card is possible only when the landlord "
        "holds exactly c; otherwise the call is alive.",
        "",
    ]
    n_by_c: dict[int, int] = {}
    for (c, _), v in sim.call_joint.items():
        n_by_c[c] = n_by_c.get(c, 0) + v
    deal_ex = copies_dist(N, d, h)
    kit_ex = copies_dist(N, d, H)
    arows = []
    for c in range(d + 1):
        a = ck.prob(f"call copies at deal = {c}", sim.call_deal_hist.get(c, 0), n, deal_ex[c])
        b = ck.prob(f"call copies after kitty = {c}", n_by_c.get(c, 0), n, kit_ex[c])
        arows.append([str(c), pct(a), pct(deal_ex[c]), pct(b), pct(kit_ex[c])])
    out += ["**A. Copies the landlord holds**", ""]
    out += table(
        ["copies landlord holds", "at the deal sim", "at the deal exact",
         "after picking up the kitty sim", "after picking up the kitty exact"],
        arows,
    )
    out += [
        "**B. Where the remaining copies are** (assumes the landlord does not bury copies "
        "of the called card)",
        "",
    ]
    brows = []
    for c in range(d):
        r = d - c
        spread = spread_dist(r, config.num_players - 1, h)
        nc = n_by_c.get(c, 0)
        for parts, ex in spread.items():
            lab = _pattern_label(parts, r)
            hits = sim.call_joint.get((c, parts), 0)
            sm = ck.prob(f"call spread c={c} {lab}", hits, nc, ex)
            brows.append([str(c), lab, "n/a" if nc == 0 else pct(sm), pct(ex)])
    out += table(["landlord holds", "spread", "sim", "exact"], brows)

    return "\n".join(out), ck.checks


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m stats.report")
    ap.add_argument("--deals", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--trump-rank", default="3")
    ap.add_argument("--trump-suit", default="H")
    ap.add_argument("--players", type=int, nargs="+", default=[7, 8, 9])
    ap.add_argument("--out", default="reports/deal_stats.md")
    args = ap.parse_args(argv)

    rank = parse_rank(args.trump_rank)
    suit = None if args.trump_suit.strip().lower() == "none" else parse_suit(args.trump_suit)
    ctx = TrumpContext(rank, suit)

    t0 = time.time()
    sections: list[str] = []
    all_checks: list[Check] = []
    per_count: list[tuple[int, int, float]] = []
    for npl in args.players:
        config = GameConfig.for_players(npl)
        sim = simulate(config, ctx, args.deals, args.seed + npl)
        section, checks = build_report(config, ctx, sim)
        sections.append(section)
        all_checks += checks
        per_count.append((npl, len(checks), max(abs(c.z) for c in checks)))
    runtime = time.time() - t0

    max_z = max(abs(c.z) for c in all_checks)
    bad = [c for c in all_checks if abs(c.z) > 4]
    cmd = (
        f"python -m stats.report --deals {args.deals} --seed {args.seed} "
        f"--trump-rank {args.trump_rank} --trump-suit {args.trump_suit} "
        f"--players {' '.join(map(str, args.players))} --out {args.out}"
    )
    head = [
        "# Deal statistics",
        "",
        f"Trump context: {ctx.describe()}",
        "",
        f"- Deals per player count: {args.deals:,}",
        f"- Seed: {args.seed} (each player count uses seed + number of players)",
        f"- Regenerate: `{cmd}`",
        "",
        "## How to read this",
        "",
        "- Seat 0 is \"the player\"; everything is at the deal, before the kitty swap, unless stated.",
        "- Pair = a card type held 2+ times (a triple counts as a pair); triple = held 3+ times. "
        "A tractor of width w is a maximal run of 2+ consecutive levels each holding a w-set "
        "(w=2 pairs, w=3 triples); cards equal in rank share a level.",
        "- Trump is fixed in advance, so this is a random player's hand, not a declarer who "
        "picked trump because they were long in it.",
        "- sim = Monte Carlo through the engine; exact = combinatorics.",
        "",
        "## Agreement",
        "",
        f"- Checks: {len(all_checks)}",
        f"- Max |z|: {max_z:.2f}",
    ]
    if bad:
        head.append(f"- Checks with |z| > 4: {len(bad)}")
        head += [f"  - {c.label}: sim {c.sim:.6g}, exact {c.exact:.6g}, z = {c.z:.2f}" for c in bad]
    else:
        head.append("- All within 4 standard errors.")
    head.append("")

    text = "\n".join(head) + "\n" + "\n".join(sections) + "\n"
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

    print(f"wrote {path}")
    print(f"runtime {runtime:.1f}s")
    for npl, nchk, mz in per_count:
        print(f"{npl} players: {nchk} checks, max |z| {mz:.2f}")
    print(f"total {len(all_checks)} checks, max |z| {max_z:.2f}, {len(bad)} with |z| > 4")
    for c in bad:
        print("  " + c.label.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
