"""Hand analysis: pure functions over a list of cards and a TrumpContext.

Conventions:
- A pair is 2 identical cards, a triple 3. A triple also counts as a pair.
- A tractor of width w (2 = pairs, 3 = triples) is a run of 2+ consecutive
  levels in one effective suit, each level holding w+ identical cards.
  Tractors are reported as maximal runs, so 5-5-6-6-7-7 is one tractor of
  length 3, not three overlapping ones.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping

from engine.cards import TrumpContext


@dataclass(frozen=True)
class Tractor:
    group: int  # effective suit
    width: int  # 2 = pairs, 3 = triples
    start: int  # order of the lowest level
    # One entry per level, low to high. A level usually has one card type;
    # it has several when equal cards each qualify (e.g. 2♠2♠ and 2♣2♣),
    # and any one of them can be used for that level.
    levels: tuple[tuple[int, ...], ...]

    @property
    def length(self) -> int:
        return len(self.levels)


@dataclass(frozen=True)
class GroupSummary:
    length: int = 0
    pairs: int = 0  # card types held 2+ times
    triples: int = 0  # card types held 3+ times
    pair_tractors: int = 0
    triple_tractors: int = 0


def group_by_suit(cards: Iterable[int], ctx: TrumpContext) -> dict[int, list[int]]:
    """Cards split by effective suit, each list sorted low to high."""
    out: dict[int, list[int]] = {g: [] for g in ctx.groups}
    for c in cards:
        out[ctx.effective_suit(c)].append(c)
    for held in out.values():
        held.sort(key=lambda c: (ctx.order(c), c))
    return out


def find_sets(cards: Iterable[int], size: int) -> list[int]:
    """Card types held at least `size` times."""
    return sorted(c for c, n in Counter(cards).items() if n >= size)


def find_pairs(cards: Iterable[int]) -> list[int]:
    return find_sets(cards, 2)


def find_triples(cards: Iterable[int]) -> list[int]:
    return find_sets(cards, 3)


def tractors_from_counts(
    counts: Mapping[int, int], ctx: TrumpContext, width: int = 2
) -> list[Tractor]:
    by_group: dict[int, dict[int, list[int]]] = {}
    for c, n in counts.items():
        if n >= width:
            by_group.setdefault(ctx.effective_suit(c), {}).setdefault(
                ctx.order(c), []
            ).append(c)

    out: list[Tractor] = []
    for group in sorted(by_group):
        levels = by_group[group]
        run: list[int] = []
        for order in sorted(levels) + [None]:
            if run and order == run[-1] + 1:
                run.append(order)
                continue
            if len(run) >= 2:
                out.append(
                    Tractor(
                        group,
                        width,
                        run[0],
                        tuple(tuple(sorted(levels[o])) for o in run),
                    )
                )
            run = [] if order is None else [order]
    return out


def find_tractors(
    cards: Iterable[int], ctx: TrumpContext, width: int = 2
) -> list[Tractor]:
    """Maximal tractors of pairs (width 2) or triples (width 3)."""
    return tractors_from_counts(Counter(cards), ctx, width)


def analyze_hand(cards: Iterable[int], ctx: TrumpContext) -> dict[int, GroupSummary]:
    """Per effective suit: length and number of pairs, triples and tractors."""
    counts = Counter(cards)
    length = dict.fromkeys(ctx.groups, 0)
    pairs = dict.fromkeys(ctx.groups, 0)
    triples = dict.fromkeys(ctx.groups, 0)
    for c, n in counts.items():
        g = ctx.effective_suit(c)
        length[g] += n
        if n >= 2:
            pairs[g] += 1
            if n >= 3:
                triples[g] += 1

    tractors = {2: dict.fromkeys(ctx.groups, 0), 3: dict.fromkeys(ctx.groups, 0)}
    for width in (2, 3):
        # A tractor needs two qualifying card types in the same suit.
        qualifying = pairs if width == 2 else triples
        if any(n >= 2 for n in qualifying.values()):
            for t in tractors_from_counts(counts, ctx, width):
                tractors[width][t.group] += 1

    return {
        g: GroupSummary(length[g], pairs[g], triples[g], tractors[2][g], tractors[3][g])
        for g in ctx.groups
    }
