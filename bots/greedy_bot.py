"""A simple rule-based bot: greedy on points, one small method per decision.

It only reads the PlayerView and always returns a member of `legal`.
"""

from __future__ import annotations

import random
from collections import Counter

from engine import rules
from engine.cards import SMALL_JOKER, TRUMP, points
from engine.state import (
    CallFriends,
    Declare,
    FriendCall,
    Pass,
    Phase,
    Play,
)
from engine.view import PlayerView

DECLARE_SUIT_SHARE = 0.36  # declare a suit when this share of my hand would be trump
DECLARE_NOTRUMP_SHARE = 0.30  # ... or this share for 无主
DECLARE_MIN_CARDS = 6
WORTH_POINTS = 5  # a trick is worth winning from this many points

_ACE = 14
_POINT_OF = tuple(points(c) for c in range(54))


def _shape(cards, ctx):
    """(category, size, top order) of a play that is one structure, None for a throw.

    category: 0 single, 1 pair, 2 triple, 3 tractor.
    """
    n = len(cards)
    if n == 1:
        return 0, 1, ctx.order(cards[0])
    counts = Counter(cards)
    k = len(counts)
    width = n // k
    if width * k != n or width < 2 or any(v != width for v in counts.values()):
        return None
    if k == 1:
        return width - 1, n, ctx.order(cards[0])
    orders = sorted({ctx.order(c) for c in counts})
    if len(orders) != k or orders[-1] - orders[0] != k - 1:
        return None
    return 3, n, orders[-1]


class GreedyBot:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)  # unused: the rules are deterministic

    def choose(self, view: PlayerView, legal):
        phase = view.phase
        if phase is Phase.DEAL:
            return self._declare(view, legal)
        if phase is Phase.BURY:
            return self._bury(view, legal)
        if phase is Phase.CALL:
            return self._call(view, legal)
        if view.trick:
            return self._follow(view, legal)
        return self._lead(view, legal)

    # --- declare -----------------------------------------------------------

    def _declare(self, view, legal):
        """Reinforce my own declaration; otherwise declare/contest only with enough would-be trumps."""
        declares = [a for a in legal if isinstance(a, Declare)]
        if not declares:
            return next(a for a in legal if isinstance(a, Pass))
        decl = view.declaration
        if decl is not None and decl.player == view.player:
            return max(declares, key=lambda a: a.count)

        hand = view.hand
        level = view.levels[view.player]
        perm = view.config.permanent_trump_ranks
        base = 0  # jokers, level rank and permanent ranks: trump whatever the suit
        per_suit = [0] * 4  # other cards, by printed suit
        for c in hand:
            if c >= SMALL_JOKER or c % 13 + 2 == level or c % 13 + 2 in perm:
                base += 1
            else:
                per_suit[c // 13] += 1

        def trumps(a):
            return base if a.card >= SMALL_JOKER else base + per_suit[a.card // 13]

        def enough(a):
            share = DECLARE_NOTRUMP_SHARE if a.card >= SMALL_JOKER else DECLARE_SUIT_SHARE
            return len(hand) >= DECLARE_MIN_CARDS and trumps(a) >= share * len(hand)

        def best(options):
            return max(options, key=lambda a: (trumps(a), a.count))

        if view.deal_complete and decl is None:  # someone must declare
            return best(declares)
        ok = [a for a in declares if enough(a)]
        return best(ok) if ok else next(a for a in legal if isinstance(a, Pass))

    # --- bury --------------------------------------------------------------

    def _bury(self, view, legal):
        """Bury the lowest score: non-trump, zero-point, unpaired non-A cards from the shortest suit, low first."""
        ctx = view.ctx
        counts = Counter(view.hand)
        suit_len = Counter(ctx.effective_suit(c) for c in view.hand)

        def score(action):
            c = action.card
            protected = counts[c] >= 2 or (c < SMALL_JOKER and c % 13 + 2 == _ACE)
            return (
                ctx.is_trump(c),
                points(c) > 0,
                protected,
                suit_len[ctx.effective_suit(c)],
                ctx.order(c),
            )

        return min(legal, key=score)

    # --- call friends ------------------------------------------------------

    def _call(self, view, legal):
        """Call the highest cards I hold fewer than all copies of, in the best off suit."""
        options = [a for a in legal if isinstance(a, CallFriends)]
        if not options:
            return legal[0]
        ideal = self._ideal_calls(view)
        if ideal in options:
            return ideal
        suit = ideal.calls[0].card // 13
        same_suit = [a for a in options if a.calls[0].card // 13 == suit]
        wanted = set(ideal.calls)
        pool = same_suit or options
        return max(pool, key=lambda a: len(wanted.intersection(a.calls)))

    def _ideal_calls(self, view) -> CallFriends:
        cfg, ctx = view.config, view.ctx
        decks = cfg.num_decks
        held = Counter(view.hand)
        held.update(view.buried or ())
        ranks = [
            r for r in range(_ACE, 2, -1)
            if r != ctx.trump_rank and r not in ctx.permanent_trump_ranks
        ]  # fmt: skip
        best = None  # ((rank sum, cards held in suit), calls)
        for suit in range(4):
            if suit == ctx.trump_suit:
                continue
            calls: list[FriendCall] = []
            need = cfg.num_friends
            for r in ranks:
                card = suit * 13 + r - 2
                free = decks - held[card]
                if free <= 0:
                    continue
                m = min(need, free)
                calls += [FriendCall(card, o, m != free) for o in range(1, m + 1)]
                need -= m
                if not need:
                    break
            score = (
                sum(c.card % 13 + 2 for c in calls),
                sum(1 for c in view.hand if ctx.effective_suit(c) == suit),
            )
            if best is None or score > best[0]:
                best = (score, calls)
        calls = sorted(best[1], key=lambda c: (c.card, c.ordinal))
        return CallFriends(tuple(calls))

    # --- lead --------------------------------------------------------------

    def _lead(self, view, legal):
        """Boss lead first, then fish for the friend (landlord), else the longest off suit, else trumps."""
        ctx = view.ctx
        cands = []  # (action, category, size, top order, effective suit)
        for a in legal:
            shape = _shape(a.cards, ctx)  # never throw
            if shape is not None:
                cands.append((a, *shape, ctx.effective_suit(a.cards[0])))
        off = [c for c in cands if c[4] != TRUMP]

        boss = self._boss_lead(view, off)
        if boss is not None:
            return boss
        fish = self._fish_lead(view, off)
        if fish is not None:
            return fish
        return self._plain_lead(view, off, cands)

    def _boss_lead(self, view, off):
        """The biggest off-suit structure nobody can beat (point cards on top are a plus)."""
        ctx = view.ctx
        seen = Counter(view.hand)
        seen.update(view.buried or ())
        for rec in view.tricks:
            for _, cards in rec.plays:
                seen.update(cards)
        decks = view.config.num_decks
        best = None
        for a, cat, size, top, suit in off:
            width = 1 if cat == 0 else (3 if cat == 2 else 2)
            if any(
                decks - seen[x] >= width
                for row in ctx.levels(suit)[top + 1 :]
                for x in row
            ):
                continue
            key = (cat, size, sum(points(c) for c in a.cards))
            if best is None or key > best[0]:
                best = (key, a)
        return best[1] if best else None

    def _fish_lead(self, view, off):
        """Landlord with an open friend slot: lead my lowest plain single of the called suit."""
        if view.player != view.landlord or None not in view.slots or not view.calls:
            return None
        called = {c.card for c in view.calls}
        suit = view.calls[0].card // 13
        singles = [
            c for c in off
            if c[1] == 0 and c[4] == suit and points(c[0].cards[0]) == 0
            and c[0].cards[0] not in called
        ]  # fmt: skip
        return min(singles, key=lambda c: c[3])[0] if singles else None

    def _plain_lead(self, view, off, cands):
        """Biggest structure of my longest off suit, else its lowest plain single; trumps: structures first."""
        if off:
            length = Counter(view.ctx.effective_suit(c) for c in view.hand if not view.ctx.is_trump(c))
            suit = max(length, key=length.get)
            mine = [c for c in off if c[4] == suit]
            structures = [c for c in mine if c[1] > 0]
            if structures:
                return max(structures, key=lambda c: (c[1], c[2], c[3]))[0]
            plain = [c for c in mine if points(c[0].cards[0]) == 0] or mine
            return min(plain, key=lambda c: c[3])[0]
        structures = [c for c in cands if c[1] > 0]
        if structures:
            return min(structures, key=lambda c: (-c[1], c[3]))[0]
        return min(cands, key=lambda c: c[3])[0]

    # --- follow ------------------------------------------------------------

    def _follow(self, view, legal):
        """Reveal as a friend, feed a teammate, win cheaply when it pays, else dump."""
        ctx, lead, me = view.ctx, view.lead, view.player
        is_trump = ctx.is_trump
        order = ctx.order
        point_of = _POINT_OF
        trump_led = lead.suit == TRUMP

        # who holds the trick, and what is in it
        best = (0, lead.groups[0].top)
        holder = view.trick[0][0]
        trick_points = 0
        for i, (seat, cards) in enumerate(view.trick):
            trick_points += sum(points(c) for c in cards)
            if i:
                key = rules.play_key(cards, lead, ctx)
                if key is not None and key > best:
                    best, holder = key, seat

        # sides (a guess): landlord + known friends; me too if I hold or filled a called card
        open_called = {c.card for c, seat in zip(view.calls, view.slots) if seat is None}
        landlord_side = {view.landlord, *view.friends}
        i_am_friend = me in landlord_side or me in view.slots or any(c in open_called for c in view.hand)
        mate_holds = (holder in landlord_side) == i_am_friend
        landlord_holds = holder in landlord_side

        cands = []  # (action, wins, points, spent trump, order sum, called card?, key)
        for a in legal:
            cards = a.cards
            key = rules.play_key(cards, lead, ctx)
            cands.append((
                a,
                key is not None and key > best,
                sum([point_of[c] for c in cards]),
                not trump_led and any([is_trump(c) for c in cards]),
                sum([order(c) for c in cards]),
                bool(open_called) and any([c in open_called for c in cards]),
                key,
            ))  # fmt: skip

        # reveal as a friend
        if me != view.landlord and me not in view.friends:
            reveal = [c for c in cands if c[5]]
            if reveal and (landlord_holds or any(c[1] for c in reveal)):
                return min(reveal, key=lambda c: (not c[1], c[4]))[0]

        # feed a teammate
        if mate_holds:
            return min(cands, key=lambda c: (c[3], -c[2], c[4]))[0]

        # win
        winners = [c for c in cands if c[1]]
        if winners:
            worth = [c for c in winners if trick_points + c[2] >= WORTH_POINTS]
            pool = worth or [c for c in winners if not c[3]]  # pointless: no trump spent
            if pool:
                return min(pool, key=lambda c: (c[6], c[2], c[4]))[0]

        # dump
        hand_counts = Counter(view.hand)

        def broken(cards):  # pairs / triples this play would split
            return sum(1 for c, k in Counter(cards).items() if hand_counts[c] >= 2 and k < hand_counts[c])

        return min(cands, key=lambda c: (c[2], c[3], c[4], broken(c[0].cards)))[0]
