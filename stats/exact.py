"""Exact deal probabilities by counting (Python ints, divided only at the end).

Polynomials are lists of ints (index = power of x).  For an event that only
concerns a set S of m cards, poly[j] = number of ways to pick j cards of S so
that the event holds.  Then for a random hand of `hand` cards from `total`:

    P(event) = sum_j poly[j] * C(total - m, hand - j) / C(total, hand)
"""

from __future__ import annotations

from dataclasses import dataclass
from math import comb, factorial, prod


def _c(a: int, b: int) -> int:
    return comb(a, b) if 0 <= b <= a else 0


def pmul(p: list[int], q: list[int]) -> list[int]:
    out = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        if a:
            for j, b in enumerate(q):
                out[i + j] += a * b
    return out


def padd(p: list[int], q: list[int]) -> list[int]:
    n = max(len(p), len(q))
    return [(p[i] if i < len(p) else 0) + (q[i] if i < len(q) else 0) for i in range(n)]


def psub(p: list[int], q: list[int]) -> list[int]:
    n = max(len(p), len(q))
    return [(p[i] if i < len(p) else 0) - (q[i] if i < len(q) else 0) for i in range(n)]


def ppow(p: list[int], n: int) -> list[int]:
    out = [1]
    for _ in range(n):
        out = pmul(out, p)
    return out


def copies_dist(total: int, copies: int, draw: int) -> list[float]:
    """pmf of how many of one card type's `copies` land in a draw of `draw`."""
    denom = _c(total, draw)
    return [_c(copies, k) * _c(total - copies, draw - k) / denom for k in range(copies + 1)]


def length_dist(total: int, hand: int, n_cards: int) -> list[float]:
    """pmf of how many of a group's n_cards land in a hand (index = length)."""
    denom = _c(total, hand)
    return [_c(n_cards, n) * _c(total - n_cards, hand - n) / denom for n in range(hand + 1)]


@dataclass(frozen=True)
class Universe:
    """`total` cards, `copies` of each card type, a random hand of `hand` cards."""

    total: int
    hand: int
    copies: int

    # --- polynomial building blocks (per card type) ---
    def _all(self) -> list[int]:
        return [_c(self.copies, c) for c in range(self.copies + 1)]

    def _lt(self, w: int) -> list[int]:
        return [_c(self.copies, c) for c in range(min(w, self.copies + 1))]

    def _ge(self, w: int) -> list[int]:
        return psub(self._all(), self._lt(w))

    def _level_no(self, t: int, w: int) -> list[int]:
        return ppow(self._lt(w), t)

    def _level_has(self, t: int, w: int) -> list[int]:
        return psub(ppow(self._all(), t), ppow(self._lt(w), t))

    def prob(self, poly: list[int], m: int, draw: int | None = None) -> float:
        draw = self.hand if draw is None else draw
        num = sum(a * _c(self.total - m, draw - j) for j, a in enumerate(poly))
        return num / _c(self.total, draw)

    # --- sets ---
    def p_type_at_least(self, w: int, draw: int | None = None) -> float:
        return self.prob(self._ge(w), self.copies, draw)

    def copies_dist(self, draw: int | None = None) -> list[float]:
        return copies_dist(self.total, self.copies, self.hand if draw is None else draw)

    def p_any_set(self, n_types: int, w: int) -> float:
        return 1 - self.prob(self._level_no(n_types, w), n_types * self.copies)

    def e_sets(self, n_types: int, w: int) -> float:
        return n_types * self.p_type_at_least(w)

    # --- tractors ---
    def p_any_tractor(self, level_sizes: list[int], w: int) -> float:
        no, has = [1], [0]
        for t in level_sizes:
            no, has = (
                pmul(padd(no, has), self._level_no(t, w)),
                pmul(no, self._level_has(t, w)),
            )
        m = self.copies * sum(level_sizes)
        return 1 - self.prob(padd(no, has), m)

    def e_tractors(self, level_sizes: list[int], w: int) -> float:
        """Expected number of maximal runs of 2+ consecutive levels with a w-set."""
        total = 0.0
        for i in range(len(level_sizes) - 1):
            sizes = [level_sizes[i], level_sizes[i + 1]]
            poly = pmul(self._level_has(sizes[0], w), self._level_has(sizes[1], w))
            if i > 0:
                sizes.insert(0, level_sizes[i - 1])
                poly = pmul(self._level_no(sizes[0], w), poly)
            total += self.prob(poly, self.copies * sum(sizes))
        return total

    # --- jokers (two joker types, `copies` of each) ---
    def joker_pair_one(self) -> float:
        return self.p_type_at_least(2)

    def joker_pair_any(self) -> float:
        g = self._ge(2)
        return 2 * self.p_type_at_least(2) - self.prob(pmul(g, g), 2 * self.copies)

    def joker_triple_any(self) -> float:
        g = self._ge(3)
        return 2 * self.p_type_at_least(3) - self.prob(pmul(g, g), 2 * self.copies)


def kitty_points_dist(config) -> dict[int, float]:
    """points -> probability for a random kitty (5s are worth 5; 10s and Ks 10)."""
    d, n, k = config.num_decks, config.total_cards, config.kitty_size
    denom = _c(n, k)
    out: dict[int, int] = {}
    for a in range(min(4 * d, k) + 1):
        for b in range(min(8 * d, k - a) + 1):
            ways = _c(4 * d, a) * _c(8 * d, b) * _c(n - 12 * d, k - a - b)
            if ways:
                out[5 * a + 10 * b] = out.get(5 * a + 10 * b, 0) + ways
    return {pts: w / denom for pts, w in sorted(out.items())}


def _partitions(r: int, max_parts: int, max_part: int | None = None):
    if max_part is None:
        max_part = r
    if r == 0:
        yield ()
        return
    if max_parts == 0:
        return
    for first in range(min(r, max_part), 0, -1):
        for rest in _partitions(r - first, max_parts - 1, first):
            yield (first,) + rest


def spread_dist(r: int, players: int, hand: int) -> dict[tuple[int, ...], float]:
    """How r copies spread over `players` hands of `hand` cards each.

    Keys are descending tuples of the nonzero per-player counts.
    """
    if r == 0:
        return {(): 1.0}
    denom = _c(players * hand, r)
    out: dict[tuple[int, ...], float] = {}
    for parts in _partitions(r, players):
        mult = prod(factorial(parts.count(v)) for v in set(parts))
        ways = factorial(players) // factorial(players - len(parts)) // mult
        out[parts] = ways * prod(_c(hand, p) for p in parts) / denom
    return out
