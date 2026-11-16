"""Card-structure rules: leads, throws, following and trick winners.

Pure functions over card ints and a TrumpContext (no game state).

- A pair / triple is 2 / 3 IDENTICAL card ints; a tractor is 2+ consecutive
  levels of pairs (or of triples) in one effective suit.
- A lead is one group (single, pair, triple, tractor) or a throw of several.
- Followers must play the same number of cards, follow suit if they can and
  match the lead's structure as well as their suit holding allows.
- A trick is won by the highest matching play of the led suit, unless a
  play made only of trumps matches the lead structure (then trump wins).
"""

from __future__ import annotations

from bisect import insort
from collections import Counter
from dataclasses import dataclass
from itertools import product
from math import comb

from engine.cards import TRUMP, TrumpContext, points
from engine.hand import tractors_from_counts

FOLLOW_ENUM_CAP = 400  # follow_options enumerates everything up to this many multisets
_MAX_WAYS = 30  # structured follow_options: ways of picking the required structure


@dataclass(frozen=True)
class Group:
    """One structure inside a play."""

    width: int  # 1 single, 2 pair, 3 triple
    length: int  # 1, or 2+ = tractor
    top: int  # ctx.order of the highest level
    cards: tuple[int, ...]  # sorted

    @property
    def size(self) -> int:
        return self.width * self.length


@dataclass(frozen=True)
class Lead:
    suit: int  # effective suit of the lead
    groups: tuple[Group, ...]  # decompose() output, largest first
    cards: tuple[int, ...]

    @property
    def n(self) -> int:
        return len(self.cards)

    @property
    def is_throw(self) -> bool:
        return len(self.groups) > 1


# --- structure helpers -----------------------------------------------------


def _levels(types, ctx: TrumpContext) -> dict[int, int]:
    """order -> smallest card type at that order."""
    order = ctx.order
    level: dict[int, int] = {}
    for c in types:
        o = order(c)
        if o not in level or c < level[o]:
            level[o] = c
    return level


def _runs(types, ctx: TrumpContext, length: int) -> list[list[int]]:
    """Every run of `length` consecutive orders among the card types, lowest first.

    One card per level (the smallest card type at that order).
    """
    level = _levels(types, ctx)
    os = sorted(level)
    return [
        [level[o] for o in os[i : i + length]]
        for i in range(len(os) - length + 1)
        if os[i + length - 1] - os[i] == length - 1
    ]


def _avail(counts, width: int, split: bool) -> list[int]:
    """Card types usable as a width-2 or width-3 unit.

    Without `split`, a type held exactly 3 times is a triple only (house rule:
    you need not split a triple to follow a pair).
    """
    if width == 3:
        return [c for c, n in counts.items() if n >= 3]
    return [c for c, n in counts.items() if n >= 2 and (split or n != 3)]


def _cards_of(run, width: int) -> tuple[int, ...]:
    return tuple(sorted(c for c in run for _ in range(width)))


def decompose(cards, ctx: TrumpContext) -> tuple[Group, ...]:
    """Split same-suit cards greedily into groups, biggest first.

    Repeatedly take the structure with the most cards (ties: wider, then higher
    top) from what is left; runs are always maximal.
    """
    n = len(cards)
    order = ctx.order
    if n == 1:
        c = cards[0]
        return (Group(1, 1, order(c), (c,)),)
    counts = Counter(cards)
    if n == 2 and len(counts) == 1:
        c = cards[0]
        return (Group(2, 1, order(c), (c, c)),)

    groups = []
    while counts:
        best = None  # (key, width, run)
        for w in (3, 2, 1):
            level = _levels([c for c, k in counts.items() if k >= w], ctx)
            if not level:
                continue
            os = sorted(level)
            i = 0
            while i < len(os):
                j = i
                if w > 1:
                    while j + 1 < len(os) and os[j + 1] == os[j] + 1:
                        j += 1
                key = (w * (j - i + 1), w, os[j])
                if best is None or key > best[0]:
                    best = (key, w, [level[o] for o in os[i : j + 1]])
                i = j + 1
        key, w, run = best
        groups.append(Group(w, len(run), key[2], _cards_of(run, w)))
        for c in run:
            counts[c] -= w
            if not counts[c]:
                del counts[c]
    return tuple(groups)


def play_suit(cards, ctx: TrumpContext) -> int | None:
    """The common effective suit of the cards, None if mixed or empty."""
    if not cards:
        return None
    eff = ctx.effective_suit
    suit = eff(cards[0])
    for c in cards:
        if eff(c) != suit:
            return None
    return suit


def make_lead(cards, ctx: TrumpContext) -> Lead:
    suit = play_suit(cards, ctx)
    if suit is None:
        raise ValueError("a lead must be non-empty and of one effective suit")
    return Lead(suit, decompose(cards, ctx), tuple(sorted(cards)))


# --- leads -----------------------------------------------------------------


def _tractor_options(counts, ctx: TrumpContext, width: int) -> list[tuple[int, ...]]:
    """Every sub-run of length >= 2 of every maximal tractor of this width."""
    out = []
    for t in tractors_from_counts(counts, ctx, width):
        levels = t.levels
        for i in range(len(levels) - 1):
            for j in range(i + 2, len(levels) + 1):
                for choice in product(*levels[i:j]):
                    out.append(_cards_of(choice, width))
    return out


def _throw_candidates(hand, ctx: TrumpContext, structs: set) -> list[tuple[int, ...]]:
    """Per suit, the top k cards (k >= 2) whenever that is not one structure."""
    suit_of, order = ctx._group, ctx._order  # direct tables: hot path
    suits: dict[int, list[int]] = {}
    for c in sorted(hand):
        suits.setdefault(suit_of[c], []).append(c)
    out = []
    for suit in sorted(suits):
        cards = suits[suit]
        if len(cards) < 2:
            continue
        cards.sort(key=order.__getitem__)  # stable: by (order, card)
        acc: list[int] = []
        for c in reversed(cards):
            insort(acc, c)
            if len(acc) >= 2:
                t = tuple(acc)
                if t not in structs:
                    out.append(t)
    return out


def lead_options(hand, ctx: TrumpContext, *, throws=True) -> list[tuple[int, ...]]:
    """Candidate leads: singles, pairs, triples, tractor sub-runs, top-k throws.

    A bounded list for bots; `is_legal_lead` accepts any legal lead.
    """
    counts = Counter(hand)
    types = sorted(counts)
    out = [(c,) for c in types]
    pair_types = [c for c in types if counts[c] >= 2]
    multi = [(c, c) for c in pair_types]
    triple_types = [c for c in pair_types if counts[c] >= 3]
    multi += [(c, c, c) for c in triple_types]
    if len(pair_types) >= 2:
        multi += _tractor_options(counts, ctx, 2)
        if len(triple_types) >= 2:
            multi += _tractor_options(counts, ctx, 3)
    out += multi
    if throws:
        out += _throw_candidates(hand, ctx, set(multi))
    return out


def is_legal_lead(cards, hand, ctx: TrumpContext) -> bool:
    """Non-empty, held in the hand, and all one effective suit."""
    if not cards or play_suit(cards, ctx) is None:
        return False
    held = Counter(hand)
    return all(held[c] >= k for c, k in Counter(cards).items())


def _beats(counts, g: Group, ctx: TrumpContext) -> bool:
    """Does a hand (counts in the throw's suit) hold a same-shape, higher structure?"""
    types = [c for c, n in counts.items() if n >= g.width]
    order = ctx.order
    if g.length == 1:
        return any(order(c) > g.top for c in types)
    return any(order(run[-1]) > g.top for run in _runs(types, ctx, g.length))


def throw_result(cards, ctx: TrumpContext, other_hands) -> tuple[int, ...]:
    """What is actually played when `cards` is led.

    A single group always stands. For a throw, a group is beatable if another
    hand holds a same-suit structure of the same width (more copies count) and
    length with a higher top; then only the smallest beatable group (fewest
    cards, then lowest top) is played.
    """
    cards = tuple(sorted(cards))
    if len(cards) == 1:
        return cards
    groups = decompose(cards, ctx)
    if len(groups) == 1:
        return cards
    eff = ctx.effective_suit
    suit = eff(cards[0])
    opponents = [Counter(c for c in h if eff(c) == suit) for h in other_hands]
    best = None
    for g in groups:
        if any(_beats(counts, g, ctx) for counts in opponents):
            key = (g.size, g.top)
            if best is None or key < best[0]:
                best = (key, g)
    return cards if best is None else best[1].cards


# --- following -------------------------------------------------------------


def _profile(counts, lead: Lead, ctx: TrumpContext, split: bool) -> tuple[int, int, int]:
    """(tractors, triple units, pair units) of the lead structure that `counts` can match."""
    counts = dict(counts)
    order = ctx.order
    tractors = triples = pairs = 0
    for g in lead.groups:
        w, units = g.width, g.length
        if w == 1:
            continue
        if units > 1:
            runs = _runs(_avail(counts, w, split), ctx, units)
            if runs:
                for c in runs[0]:
                    counts[c] -= w
                tractors += 1
                pairs += units
                if w == 3:
                    triples += units
                continue
        for _ in range(units):  # a led triple, or the pieces of a failed tractor
            if w == 3:
                avail = _avail(counts, 3, split)
                if avail:
                    c = min(avail, key=lambda c: (order(c), c))
                    counts[c] -= 3
                    triples += 1
                    pairs += 1
                    continue
            avail = _avail(counts, 2, split)
            if avail:
                c = min(avail, key=lambda c: (counts[c], order(c), c))
                counts[c] -= 2
                pairs += 1
    return tractors, triples, pairs


def match_profile(
    cards, lead: Lead, ctx: TrumpContext, *, split_triples=True
) -> tuple[int, int, int]:
    """How much of the lead's structure the cards (those in the lead suit) can match.

    Returns (tractors, triple_units, pair_units), matched greedily group by group.
    """
    eff, suit = ctx.effective_suit, lead.suit
    counts = Counter(c for c in cards if eff(c) == suit)
    return _profile(counts, lead, ctx, split_triples)


def _requirement(counts, lead: Lead, ctx: TrumpContext, split: bool) -> tuple[int, int, int]:
    if lead.groups[0].width == 1:  # only singles led
        return 0, 0, 0
    return _profile(counts, lead, ctx, split)


def _ge(a, b) -> bool:
    return a[0] >= b[0] and a[1] >= b[1] and a[2] >= b[2]


def is_legal_follow(
    cards, hand, lead: Lead, ctx: TrumpContext, *, split_triples=False
) -> bool:
    """Same count; all of the led suit if you hold n or fewer; else n cards of the
    suit whose structure match is at least what the hand's suit holding allows."""
    n = lead.n
    if len(cards) != n:
        return False
    held = Counter(hand)
    played = Counter(cards)
    for c, k in played.items():
        if held[c] < k:
            return False
    eff, suit = ctx.effective_suit, lead.suit
    suit_held = {c: k for c, k in held.items() if eff(c) == suit}
    held_in = sum(suit_held.values())
    played_in = sum(k for c, k in played.items() if eff(c) == suit)
    if held_in <= n:
        return played_in == held_in
    if played_in != n:
        return False
    required = _requirement(suit_held, lead, ctx, split_triples)
    return required == (0, 0, 0) or _ge(_profile(played, lead, ctx, True), required)


def _count_multisets(counts, r: int) -> int:
    """Number of distinct multisets of r cards given the copies of each type."""
    ways = [1] + [0] * r
    for n in counts:
        new = [0] * (r + 1)
        for j, w in enumerate(ways):
            if w:
                for k in range(min(n, r - j) + 1):
                    new[j + k] += w
        ways = new
    return ways[r]


def _small_pool(counts: Counter, r: int, cap: int) -> bool:
    return comb(len(counts) + r - 1, r) <= cap or _count_multisets(counts.values(), r) <= cap


def _iter_multisets(types, counts, r, start=0):
    if r == 0:
        yield ()
        return
    for i in range(start, len(types)):
        t = types[i]
        for k in range(1, min(counts[t], r) + 1):
            for tail in _iter_multisets(types, counts, r - k, i + 1):
                yield (t,) * k + tail


def _multisets(types, counts, r: int) -> list[tuple[int, ...]]:
    """All distinct multisets of r cards (sorted tuples); `types` is sorted."""
    if r == 1:
        return [(t,) for t in types]
    if r == 2:
        out = []
        for i, a in enumerate(types):
            if counts[a] >= 2:
                out.append((a, a))
            out.extend([(a, b) for b in types[i + 1 :]])
        return out
    return list(_iter_multisets(types, counts, r))


def _match_highest(counts, groups, ctx: TrumpContext):
    """Match every group from `counts` with the highest structure available.

    Returns (cards used, order of the top of the first group) or None.
    """
    counts = dict(counts)
    order = ctx.order
    taken: list[int] = []
    top0 = None
    for g in groups:
        w, length = g.width, g.length
        avail = [c for c, n in counts.items() if n >= w]
        if length > 1:
            runs = _runs(avail, ctx, length)
            chosen = runs[-1] if runs else None
        else:
            chosen = [max(avail, key=lambda c: (order(c), c))] if avail else None
        if chosen is None:
            return None
        for c in chosen:
            counts[c] -= w
            taken.extend([c] * w)
        if top0 is None:
            top0 = order(chosen[-1])
    return taken, top0


def _trump_matches(rest, lead: Lead, ctx: TrumpContext) -> list[tuple[int, ...]]:
    """Plays made only of trumps that fully match the lead structure (void follower)."""
    trumps = Counter(c for c in rest if ctx.is_trump(c))
    groups = lead.groups
    if len(groups) > 1:
        m = _match_highest(trumps, groups, ctx)
        return [tuple(sorted(m[0]))] if m else []
    w, length = groups[0].width, groups[0].length
    avail = sorted(c for c, k in trumps.items() if k >= w)
    if length == 1:
        return [(c,) * w for c in avail]
    return [_cards_of(run, w) for run in _runs(avail, ctx, length)]


def _free_options(forced, rest, r: int, lead: Lead, ctx: TrumpContext, cap: int):
    """Short or void in the led suit: play all of `forced`, plus r free cards from `rest`."""
    if r == 0:
        return [tuple(sorted(forced))]
    pool = Counter(rest)
    if _small_pool(pool, r, cap):
        found = _multisets(sorted(pool), pool, r)
        if forced:
            found = [tuple(sorted((*forced, *ms))) for ms in found]
        return found
    order, is_trump = ctx.order, ctx.is_trump
    fills = [
        sorted(rest, key=lambda c: (points(c), is_trump(c), order(c), c))[:r],
        sorted(rest, key=lambda c: (-points(c), order(c), c))[:r],
    ]
    trumps = [c for c in rest if is_trump(c)]
    if len(trumps) >= r:
        fills.append(sorted(trumps, key=lambda c: (order(c), c))[:r])
    cands = {tuple(sorted((*forced, *f))) for f in fills}
    if not forced and lead.suit != TRUMP:
        cands.update(_trump_matches(rest, lead, ctx))
    return sorted(cands)


def _cores(counts, lead: Lead, ctx: TrumpContext, split: bool) -> list[list[int]]:
    """Up to _MAX_WAYS ways to build the lead's pair/triple/tractor units from `counts`."""
    out: list[list[int]] = []
    order = ctx.order

    def spread(opts):  # keep the two lowest and the two highest options
        return opts if len(opts) <= 4 else opts[:2] + opts[-2:]

    def take(counts, run, w):
        new = dict(counts)
        for c in run:
            new[c] -= w
        return new

    def rec(counts, tasks, taken):
        if len(out) >= _MAX_WAYS:
            return
        if not tasks:
            out.append(taken)
            return
        (w, length), rest = tasks[0], tasks[1:]
        if length > 1:
            runs = _runs(_avail(counts, w, split), ctx, length)
            if not runs:  # failed tractor: separate units
                rec(counts, [(w, 1)] * length + rest, taken)
                return
            for run in spread(runs):
                rec(take(counts, run, w), rest, taken + [c for c in run for _ in range(w)])
            return
        if w == 3 and not _avail(counts, 3, split):
            w = 2
        avail = sorted(_avail(counts, w, split), key=lambda c: (order(c), c))
        if not avail:
            rec(counts, rest, taken)
            return
        for c in spread(avail):
            rec(take(counts, [c], w), rest, taken + [c] * w)

    rec(dict(counts), [(g.width, g.length) for g in lead.groups if g.width > 1], [])
    return out


def _in_suit_structured(hc: Counter, n: int, lead: Lead, ctx: TrumpContext, split: bool, required):
    """Large pool: build the required structure a few ways, then fill the rest."""
    order = ctx.order

    def legal(cand):
        return required == (0, 0, 0) or _ge(_profile(Counter(cand), lead, ctx, True), required)

    cands = set()
    for core in _cores(hc, lead, ctx, split):
        left = Counter(hc)
        left.subtract(core)
        rem = sorted(left.elements())
        r = n - len(core)
        if r:
            fills = [
                sorted(rem, key=lambda c: (points(c), order(c), c))[:r],
                sorted(rem, key=lambda c: (-points(c), order(c), c))[:r],
                sorted(rem, key=lambda c: (-order(c), c))[:r],
            ]
        else:
            fills = [[]]
        for f in fills:
            cand = tuple(sorted((*core, *f)))
            if len(cand) == n and legal(cand):
                cands.add(cand)
    if not cands:  # never empty: take the first legal multiset
        types = sorted(hc)
        cands.add(next(ms for ms in _iter_multisets(types, hc, n) if legal(ms)))
    return sorted(cands)


def _in_suit_options(hs, n: int, lead: Lead, ctx: TrumpContext, split: bool, cap: int):
    """The suit holds more than n cards: play n of them matching the required structure."""
    hc = Counter(hs)
    types = sorted(hc)
    required = _requirement(hc, lead, ctx, split)
    if not _small_pool(hc, n, cap):
        return _in_suit_structured(hc, n, lead, ctx, split, required)
    if n == 2:  # the only requirement a 2-card lead can make is "play a pair"
        if required[2]:
            return [(c, c) for c in types if hc[c] >= 2]
        return _multisets(types, hc, 2)
    found = _multisets(types, hc, n)
    if required == (0, 0, 0):
        return found
    return [ms for ms in found if _ge(_profile(Counter(ms), lead, ctx, True), required)]


def follow_options(
    hand, lead: Lead, ctx: TrumpContext, *, split_triples=False, cap=FOLLOW_ENUM_CAP
) -> list[tuple[int, ...]]:
    """Legal follows for bots (never empty, every entry passes is_legal_follow).

    All distinct legal multisets when there are at most `cap` candidates;
    otherwise a structured subset (see the spec).
    """
    n, suit = lead.n, lead.suit
    eff = ctx.effective_suit
    if n == 1:
        ins = {c for c in hand if eff(c) == suit}
        return [(c,) for c in sorted(ins or set(hand))]
    hs: list[int] = []
    rest: list[int] = []
    for c in hand:
        (hs if eff(c) == suit else rest).append(c)
    if len(hs) <= n:
        return _free_options(sorted(hs), rest, n - len(hs), lead, ctx, cap)
    return _in_suit_options(hs, n, lead, ctx, split_triples, cap)


# --- winning ---------------------------------------------------------------


def play_key(cards, lead: Lead, ctx: TrumpContext) -> tuple[int, int] | None:
    """Strength of a play against the lead, or None if it cannot win.

    A play can win only if it is all lead-suit or all trump and fully matches
    the lead structure. Key = (is trump over a non-trump lead, top order of the
    structure matched to the lead's biggest group).
    """
    if len(cards) != lead.n:
        return None
    eff = ctx.effective_suit
    suit = eff(cards[0])
    for c in cards:
        if eff(c) != suit:
            return None
    if suit != lead.suit and suit != TRUMP:
        return None
    flag = 1 if suit == TRUMP and lead.suit != TRUMP else 0
    groups = lead.groups
    if len(groups) == 1 and groups[0].length == 1:  # single, pair or triple
        c = cards[0]
        for x in cards:
            if x != c:
                return None
        return flag, ctx.order(c)
    m = _match_highest(Counter(cards), groups, ctx)
    return None if m is None else (flag, m[1])


def trick_winner(plays, ctx: TrumpContext) -> int:
    """Index of the winning play; plays[0] is the (throw-resolved) lead.

    A later play wins only with a strictly greater key, so equal plays favour
    the earlier one and a non-matching play never wins.
    """
    lead = make_lead(plays[0], ctx)
    best = (0, lead.groups[0].top)
    winner = 0
    for i in range(1, len(plays)):
        key = play_key(plays[i], lead, ctx)
        if key is not None and key > best:
            best, winner = key, i
    return winner
