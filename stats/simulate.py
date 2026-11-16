"""Monte Carlo deal statistics, driven through the engine's deal() and analyze_hand()."""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field

from engine.cards import BIG_JOKER, SMALL_JOKER, TrumpContext, points
from engine.config import GameConfig
from engine.deal import deal
from engine.hand import analyze_hand

STRUCTS = ("pairs", "triples", "pair_tractors", "triple_tractors")


@dataclass
class SimResult:
    n_deals: int
    call_card: int
    # group -> Counter(length -> deals)
    lengths: dict[int, Counter] = field(default_factory=dict)
    # (group, struct) -> [deals with count>=1, sum count, sum count^2]
    structs: dict[tuple[int, str], list[int]] = field(default_factory=dict)
    big_pair: int = 0
    small_pair: int = 0
    any_joker_pair: int = 0
    joker_triple: int = 0
    kitty_hist: Counter = field(default_factory=Counter)
    call_deal_hist: Counter = field(default_factory=Counter)  # copies at the deal
    call_joint: Counter = field(default_factory=Counter)  # (c, pattern) -> deals


def simulate(
    config: GameConfig,
    ctx: TrumpContext,
    n_deals: int,
    seed: int,
    call_card: int | None = None,
) -> SimResult:
    rng = random.Random(seed)
    groups = ctx.groups
    if call_card is None:
        call_card = ctx.levels(groups[0])[-1][0]
    res = SimResult(n_deals=n_deals, call_card=call_card)
    lengths = {g: Counter() for g in groups}
    structs = {(g, s): [0, 0, 0] for g in groups for s in STRUCTS}
    res.lengths = lengths
    res.structs = structs

    kitty_hist = res.kitty_hist
    call_deal_hist = res.call_deal_hist
    call_joint = res.call_joint
    big_pair = small_pair = any_pair = triple = 0

    tallies = {g: [structs[(g, s)] for s in STRUCTS] for g in groups}
    pt = [points(c) for c in range(54)]

    for _ in range(n_deals):
        dl = deal(config, rng)
        hands = dl.hands
        mine = hands[0]
        for g, gs in analyze_hand(mine, ctx).items():
            lengths[g][gs.length] += 1
            for tally, v in zip(
                tallies[g], (gs.pairs, gs.triples, gs.pair_tractors, gs.triple_tractors)
            ):
                if v:
                    tally[0] += 1
                    tally[1] += v
                    tally[2] += v * v

        nb = mine.count(BIG_JOKER)
        ns = mine.count(SMALL_JOKER)
        if nb >= 2:
            big_pair += 1
        if ns >= 2:
            small_pair += 1
        if nb >= 2 or ns >= 2:
            any_pair += 1
        if nb >= 3 or ns >= 3:
            triple += 1

        kit = dl.kitty
        kitty_hist[sum([pt[c] for c in kit])] += 1

        c0 = mine.count(call_card)
        call_deal_hist[c0] += 1
        pattern = tuple(
            sorted(
                [n for n in [h.count(call_card) for h in hands[1:]] if n], reverse=True
            )
        )
        call_joint[(c0 + kit.count(call_card), pattern)] += 1

    res.big_pair, res.small_pair = big_pair, small_pair
    res.any_joker_pair, res.joker_triple = any_pair, triple
    return res
