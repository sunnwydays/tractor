"""Game state for one round: deal, declare, bury, call friends, play, score.

`RoundState` is an immutable snapshot. `apply(state, action)` returns a new one
and never mutates its input; `legal_actions` lists candidate actions for the
player to act and `is_legal` is the full rule check.

Phases: DEAL (cards dealt one at a time; players may declare while it happens
and in a closing round), BURY (landlord buries the kitty), CALL (landlord calls
friends or goes solo), PLAY (tricks), DONE (scored).
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, replace
from enum import Enum
from functools import lru_cache
from itertools import combinations_with_replacement

from engine import rules, scoring
from engine.cards import BIG_JOKER, SMALL_JOKER, Suit, TrumpContext, points
from engine.config import GameConfig
from engine.deal import build_deck

MAX_REDEALS = 1000  # guard against a table that never declares


class Phase(Enum):
    DEAL = "deal"
    BURY = "bury"
    CALL = "call"
    PLAY = "play"
    DONE = "done"


# --- actions ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Pass:
    """Declare nothing (deal phase)."""


@dataclass(frozen=True, slots=True)
class Declare:
    """Flip `count` copies of a level card (1..3) or a joker (count >= 2)."""

    card: int
    count: int


@dataclass(frozen=True, slots=True)
class BuryCard:
    card: int


@dataclass(frozen=True, slots=True)
class FriendCall:
    """'The `ordinal`-th `card`', alive or dead. Part of CallFriends."""

    card: int
    ordinal: int
    alive: bool = True


@dataclass(frozen=True, slots=True)
class CallFriends:
    calls: tuple[FriendCall, ...]


@dataclass(frozen=True, slots=True)
class GoSolo:
    """Call the kitty: play alone against everyone."""


@dataclass(frozen=True, slots=True)
class Play:
    cards: tuple[int, ...]  # sorted


Action = Pass | Declare | BuryCard | CallFriends | GoSolo | Play


@dataclass(frozen=True, slots=True)
class Declaration:
    player: int
    card: int
    count: int


@dataclass(frozen=True, slots=True)
class TrickRecord:
    leader: int
    plays: tuple[tuple[int, tuple[int, ...]], ...]  # (seat, cards) in play order
    winner: int
    points: int
    attempted: tuple[int, ...] | None  # cards of a failed throw
    joined: tuple[int, ...]  # seats that became friends at the end of this trick


@dataclass(frozen=True, slots=True)
class RoundState:
    config: GameConfig
    seed: int | str
    redeals: int
    levels: tuple[int, ...]
    eligible: tuple[int, ...]
    first_seat: int
    phase: Phase
    to_act: int
    deck: tuple[int, ...]
    dealt: int
    hands: tuple[tuple[int, ...], ...]
    declaration: Declaration | None
    declare_history: tuple[Declaration, ...]
    landlord: int | None
    ctx: TrumpContext | None
    kitty: tuple[int, ...]
    buried: tuple[int, ...]
    calls: tuple[FriendCall, ...]
    solo_called: bool
    slots: tuple[int | None, ...]
    slot_tricks: tuple[int | None, ...]
    friends: tuple[int, ...]
    leader: int
    trick: tuple[tuple[int, tuple[int, ...]], ...]
    lead: rules.Lead | None
    attempted: tuple[int, ...] | None
    tricks: tuple[TrickRecord, ...]
    points_won: tuple[int, ...]
    result: scoring.RoundResult | None
    closing_left: int  # closing round: players still to be passed over (-1 while dealing)
    copies_seen: tuple[tuple[int, int], ...]  # (called card, copies counted so far)

    @property
    def deal_complete(self) -> bool:
        if self.phase is not Phase.DEAL:
            return True
        return self.dealt == self.config.num_players * self.config.hand_size


# --- helpers ---------------------------------------------------------------


@lru_cache(maxsize=None)
def make_ctx(trump_rank: int, trump_suit: int | None, permanent: tuple[int, ...]) -> TrumpContext:
    return TrumpContext(trump_rank, None if trump_suit is None else Suit(trump_suit), permanent)


def _without(hand: tuple[int, ...], cards) -> tuple[int, ...]:
    """The sorted hand with one copy of each of `cards` removed."""
    h = list(hand)
    for c in cards:
        h.remove(c)
    return tuple(h)


def _replace_at(seq: tuple, i: int, value) -> tuple:
    return seq[:i] + (value,) + seq[i + 1 :]


def _next(seat: int, n: int) -> int:
    return (seat + 1) % n


# --- declaring -------------------------------------------------------------


def _strength(card: int, count: int) -> tuple[bool, int, bool]:
    return card >= SMALL_JOKER, count, card == BIG_JOKER


def _beats_declaration(decl: Declaration | None, p: int, card: int, count: int) -> bool:
    """May p declare (card, count) over the current declaration?"""
    if decl is None:
        return True
    if decl.player == p:  # reinforce: same card, more copies
        return card == decl.card and count > decl.count
    if _strength(card, count) <= _strength(decl.card, decl.count):
        return False
    return card >= SMALL_JOKER or decl.card >= SMALL_JOKER or card // 13 != decl.card // 13


def _declares(decl: Declaration | None, p: int, level: int, hand) -> list[Declare]:
    """Every legal Declare for p holding `hand` (eligibility is checked by the caller)."""
    out = []
    for suit in range(4):
        card = suit * 13 + level - 2
        for count in range(1, hand.count(card) + 1):
            if _beats_declaration(decl, p, card, count):
                out.append(Declare(card, count))
    for card in (SMALL_JOKER, BIG_JOKER):
        for count in range(2, hand.count(card) + 1):
            if _beats_declaration(decl, p, card, count):
                out.append(Declare(card, count))
    return out


def _declare_legal(st: RoundState, p: int, card: int, count: int) -> bool:
    if p not in st.eligible or count < 1 or not 0 <= card <= BIG_JOKER:
        return False
    if st.hands[p].count(card) < count:
        return False
    if card >= SMALL_JOKER:
        if count < 2:
            return False
    elif card % 13 + 2 != st.levels[p]:
        return False
    return _beats_declaration(st.declaration, p, card, count)


def _has_clothesless_hand(deck, config: GameConfig, first_seat: int) -> bool:
    """True if some player's dealt hand (kitty excluded) has no J, Q or K. Jokers and A don't count."""
    n = config.num_players
    clothed = [False] * n
    for i in range(n * config.hand_size):
        c = deck[i]
        if c < SMALL_JOKER and c % 13 + 2 in (11, 12, 13):
            clothed[(first_seat + i) % n] = True
    return not all(clothed)


def _fresh(config, seed, redeals, levels, eligible, first_seat) -> RoundState:
    """A newly shuffled deck, dealt up to the first decision."""
    if redeals > MAX_REDEALS:
        raise RuntimeError(f"nobody declared after {MAX_REDEALS} redeals")
    n = config.num_players
    deck = build_deck(config.num_decks)
    random.Random(f"{seed}/{redeals}").shuffle(deck)
    if config.no_face_redeal and _has_clothesless_hand(deck, config, first_seat):
        return _fresh(config, seed, redeals + 1, levels, eligible, first_seat)
    st = RoundState(
        config=config, seed=seed, redeals=redeals, levels=levels, eligible=eligible,
        first_seat=first_seat, phase=Phase.DEAL, to_act=first_seat, deck=tuple(deck),
        dealt=0, hands=((),) * n, declaration=None, declare_history=(), landlord=None,
        ctx=None, kitty=(), buried=(), calls=(), solo_called=False, slots=(),
        slot_tricks=(), friends=(), leader=first_seat, trick=(), lead=None,
        attempted=None, tricks=(), points_won=(0,) * n, result=None,
        closing_left=-1, copies_seen=(),
    )  # fmt: skip
    return _deal_on(st)


def _deal_on(st: RoundState) -> RoundState:
    """Deal card by card until a player may declare, or the deal is complete."""
    cfg = st.config
    n = cfg.num_players
    total = n * cfg.hand_size
    hands = [list(h) for h in st.hands]
    deck, levels, eligible, first, decl = st.deck, st.levels, st.eligible, st.first_seat, st.declaration
    for i in range(st.dealt, total):
        p = (first + i) % n
        c = deck[i]
        hands[p].append(c)
        if p in eligible and (c >= SMALL_JOKER or c % 13 + 2 == levels[p]):
            hands[p].sort()
            if _declares(decl, p, levels[p], hands[p]):
                new = tuple(tuple(sorted(h)) for h in hands)
                return replace(st, hands=new, dealt=i + 1, to_act=p)
    new = tuple(tuple(sorted(h)) for h in hands)
    return _closing_on(replace(st, hands=new, dealt=total, closing_left=n), first)


def _closing_on(st: RoundState, seat: int) -> RoundState:
    """Closing round: ask the next player with a legal Declare, until all are passed over."""
    n = st.config.num_players
    left = st.closing_left
    while left:
        if seat in st.eligible and _declares(st.declaration, seat, st.levels[seat], st.hands[seat]):
            return replace(st, to_act=seat, closing_left=left)
        left -= 1
        seat = _next(seat, n)
    return _finish_declaring(replace(st, closing_left=0))


def _finish_declaring(st: RoundState) -> RoundState:
    """Nobody declared: redeal. Otherwise the declarer is landlord and picks up the kitty."""
    decl = st.declaration
    if decl is None:
        return _fresh(st.config, st.seed, st.redeals + 1, st.levels, st.eligible, st.first_seat)
    cfg = st.config
    landlord = decl.player
    suit = None if decl.card >= SMALL_JOKER else decl.card // 13
    ctx = make_ctx(st.levels[landlord], suit, cfg.permanent_trump_ranks)
    kitty = st.deck[cfg.num_players * cfg.hand_size :]
    hand = tuple(sorted((*st.hands[landlord], *kitty)))
    return replace(
        st, phase=Phase.BURY, to_act=landlord, landlord=landlord, ctx=ctx, kitty=kitty,
        hands=_replace_at(st.hands, landlord, hand), leader=landlord,
    )  # fmt: skip


# --- friend calls ----------------------------------------------------------


def _calls_legal(st: RoundState, calls) -> bool:
    cfg, ctx = st.config, st.ctx
    if len(calls) != cfg.num_friends:
        return False
    trump_suit = ctx.trump_suit
    suit = None
    seen = set()
    per_card: dict[int, list[FriendCall]] = {}
    for call in calls:
        if not isinstance(call, FriendCall):
            return False
        c, o = call.card, call.ordinal
        if not 0 <= c < SMALL_JOKER:
            return False
        if suit is None:
            suit = c // 13
        if c // 13 != suit or (trump_suit is not None and c // 13 == trump_suit):
            return False
        rank = c % 13 + 2
        if rank == ctx.trump_rank or rank in ctx.permanent_trump_ranks:
            return False
        if not 1 <= o <= cfg.num_decks or (c, o) in seen:
            return False
        seen.add((c, o))
        per_card.setdefault(c, []).append(call)
    hand = st.hands[st.landlord]
    for c, group in per_card.items():
        alive = group[0].alive
        if any(call.alive != alive for call in group):
            return False
        if not alive:
            m = len(group)
            if sorted(call.ordinal for call in group) != list(range(1, m + 1)):
                return False
            if hand.count(c) + st.buried.count(c) != cfg.num_decks - m:
                return False
    return True


def _call_options(st: RoundState) -> list[Action]:
    """A structured subset: picks among the top 4 callable ranks, all alive, plus dead where possible."""
    cfg, ctx = st.config, st.ctx
    ranks = [
        r for r in range(14, 1, -1)
        if r != ctx.trump_rank and r not in ctx.permanent_trump_ranks
    ][:4]  # fmt: skip
    hand = st.hands[st.landlord]
    out: list[Action] = []
    for suit in range(4):
        if suit == ctx.trump_suit:
            continue
        cards = sorted(suit * 13 + r - 2 for r in ranks)
        for combo in combinations_with_replacement(cards, cfg.num_friends):
            counts = Counter(combo)
            if max(counts.values(), default=0) > cfg.num_decks:
                continue
            out.append(CallFriends(tuple(FriendCall(c, o) for c in sorted(counts) for o in range(1, counts[c] + 1))))
            dead = {c for c, m in counts.items() if hand.count(c) + st.buried.count(c) == cfg.num_decks - m}
            if dead:
                out.append(CallFriends(tuple(
                    FriendCall(c, o, c not in dead) for c in sorted(counts) for o in range(1, counts[c] + 1)
                )))  # fmt: skip
    if cfg.allow_solo:
        out.append(GoSolo())
    return out


def _start_play(st: RoundState, calls, solo: bool) -> RoundState:
    cards = sorted({c.card for c in calls})
    return replace(
        st, phase=Phase.PLAY, calls=tuple(calls), solo_called=solo,
        slots=(None,) * len(calls), slot_tricks=(None,) * len(calls),
        copies_seen=tuple((c, 0) for c in cards), leader=st.landlord, to_act=st.landlord,
    )  # fmt: skip


# --- play ------------------------------------------------------------------


def _fill_slots(st: RoundState, seat: int, cards):
    """Count the copies of called cards in a play; returns (copies_seen, slots, slot_tricks)."""
    called = {c for c, _ in st.copies_seen}
    if called.isdisjoint(cards):
        return st.copies_seen, st.slots, st.slot_tricks
    seen = dict(st.copies_seen)
    slots, slot_tricks = list(st.slots), list(st.slot_tricks)
    trick_no = len(st.tricks) + 1
    is_landlord = seat == st.landlord
    for c in cards:
        if c not in seen:
            continue
        if is_landlord:  # dead calls ignore the landlord's copies
            alive = next(call.alive for call in st.calls if call.card == c)
            if not alive or st.config.alive_landlord_copy == "ignore":
                continue
        seen[c] += 1
        for i, call in enumerate(st.calls):
            if call.card == c and call.ordinal == seen[c] and slots[i] is None:
                slots[i], slot_tricks[i] = seat, trick_no
    return (
        tuple((c, seen[c]) for c, _ in st.copies_seen),
        tuple(slots),
        tuple(slot_tricks),
    )


def _play_legal(st: RoundState, cards) -> bool:
    ctx, hand = st.ctx, st.hands[st.to_act]
    if not st.trick:
        return rules.is_legal_lead(cards, hand, ctx)
    return rules.is_legal_follow(
        cards, hand, st.lead, ctx, split_triples=st.config.split_triple_to_follow_pair
    )


def _apply_play(st: RoundState, cards: tuple[int, ...]) -> RoundState:
    cfg, ctx = st.config, st.ctx
    seat = st.to_act
    n = cfg.num_players
    lead, attempted = st.lead, None
    if not st.trick:
        if len(cards) > 1:
            others = [h for i, h in enumerate(st.hands) if i != seat]
            played = rules.throw_result(cards, ctx, others)
            if played != cards:
                attempted, cards = cards, played
        lead = rules.make_lead(cards, ctx)
    copies_seen, slots, slot_tricks = _fill_slots(st, seat, cards)
    hands = _replace_at(st.hands, seat, _without(st.hands[seat], cards))
    trick = st.trick + ((seat, cards),)
    if len(trick) < n:
        return replace(
            st, hands=hands, trick=trick, lead=lead, to_act=_next(seat, n),
            attempted=attempted or st.attempted, copies_seen=copies_seen,
            slots=slots, slot_tricks=slot_tricks,
        )  # fmt: skip
    return _end_trick(
        replace(
            st, hands=hands, trick=trick, lead=lead, attempted=attempted or st.attempted,
            copies_seen=copies_seen, slots=slots, slot_tricks=slot_tricks,
        )  # fmt: skip
    )


def _end_trick(st: RoundState) -> RoundState:
    """Award the trick, reveal new friends, and score the round after the last trick."""
    ctx, n = st.ctx, st.config.num_players
    winner = st.trick[rules.trick_winner([cards for _, cards in st.trick], ctx)][0]
    pts = sum(points(c) for _, cards in st.trick for c in cards)
    trick_no = len(st.tricks) + 1
    joined = []
    for seat, filled in zip(st.slots, st.slot_tricks):
        if filled == trick_no and seat != st.landlord and seat not in st.friends and seat not in joined:
            joined.append(seat)
    record = TrickRecord(st.leader, st.trick, winner, pts, st.attempted, tuple(joined))
    points_won = _replace_at(st.points_won, winner, st.points_won[winner] + pts)
    friends = st.friends + tuple(joined)
    st = replace(
        st, tricks=st.tricks + (record,), points_won=points_won, friends=friends,
        trick=(), attempted=None, leader=winner, to_act=winner,
    )  # fmt: skip
    if st.hands[winner]:
        return replace(st, lead=None)
    group = st.lead.groups[0]
    result = scoring.score_round(
        st.config, levels=st.levels, landlord=st.landlord, friends=friends,
        solo_called=st.solo_called, trump_rank=ctx.trump_rank, points_won=points_won,
        kitty_points=sum(points(c) for c in st.buried), last_trick_winner=winner,
        last_trick_width=group.width, last_trick_length=group.length,
    )  # fmt: skip
    return replace(st, phase=Phase.DONE, lead=None, result=result)


# --- public API ------------------------------------------------------------


def new_round(config: GameConfig, seed, *, levels=None, eligible=None, first_seat=0) -> RoundState:
    """Shuffle and deal up to the first decision. Defaults: everyone at the start level and eligible."""
    n = config.num_players
    levels = tuple(levels) if levels is not None else (config.start_level,) * n
    eligible = tuple(sorted(eligible)) if eligible is not None else tuple(range(n))
    return _fresh(config, seed, 0, levels, eligible, first_seat)


def legal_actions(st: RoundState) -> list[Action]:
    """Candidate actions for `st.to_act` (complete except CallFriends, which is a subset)."""
    p = st.to_act
    if st.phase is Phase.DEAL:
        return [Pass(), *_declares(st.declaration, p, st.levels[p], st.hands[p])]
    if st.phase is Phase.BURY:
        return [BuryCard(c) for c in sorted(set(st.hands[p]))]
    if st.phase is Phase.CALL:
        return _call_options(st)
    if st.phase is Phase.PLAY:
        hand, ctx = st.hands[p], st.ctx
        if not st.trick:
            options = rules.lead_options(hand, ctx)
        else:
            options = rules.follow_options(
                hand, st.lead, ctx, split_triples=st.config.split_triple_to_follow_pair
            )
        return [Play(o) for o in options]
    return []


def is_legal(st: RoundState, action) -> bool:
    """The full rule check for `st.to_act` (accepts more than legal_actions lists)."""
    p = st.to_act
    if st.phase is Phase.DEAL:
        if isinstance(action, Pass):
            return True
        return isinstance(action, Declare) and _declare_legal(st, p, action.card, action.count)
    if st.phase is Phase.BURY:
        return isinstance(action, BuryCard) and action.card in st.hands[p]
    if st.phase is Phase.CALL:
        if isinstance(action, GoSolo):
            return st.config.allow_solo
        return isinstance(action, CallFriends) and _calls_legal(st, action.calls)
    if st.phase is Phase.PLAY:
        return isinstance(action, Play) and _play_legal(st, action.cards)
    return False


def apply(st: RoundState, action) -> RoundState:
    """The state after `action`; raises ValueError if it is not legal. Never mutates `st`."""
    if not is_legal(st, action):
        raise ValueError(f"illegal action in phase {st.phase.name}: {action!r}")
    p, n = st.to_act, st.config.num_players
    if st.phase is Phase.DEAL:
        if isinstance(action, Declare):
            decl = Declaration(p, action.card, action.count)
            st = replace(st, declaration=decl, declare_history=st.declare_history + (decl,))
            left = n - 1
        else:
            left = st.closing_left - 1
        if st.closing_left < 0:  # still dealing (a window may open on the last card)
            return _deal_on(st)
        return _closing_on(replace(st, closing_left=left), _next(p, n))
    if st.phase is Phase.BURY:
        buried = tuple(sorted((*st.buried, action.card)))
        st = replace(st, buried=buried, hands=_replace_at(st.hands, p, _without(st.hands[p], (action.card,))))
        return replace(st, phase=Phase.CALL) if len(buried) == st.config.kitty_size else st
    if st.phase is Phase.CALL:
        if isinstance(action, GoSolo):
            return _start_play(st, (), True)
        return _start_play(st, action.calls, False)
    return _apply_play(st, tuple(sorted(action.cards)))


# --- test / puzzle helper ----------------------------------------------------


def state_for_play(
    config: GameConfig,
    hands,
    landlord: int,
    trump_rank: int,
    trump_suit,
    calls=(),
    buried=(),
    *,
    leader: int | None = None,
    levels=None,
    solo: bool = False,
    friends=(),
    points_won=None,
    seed=0,
) -> RoundState:
    """A PLAY-phase state with the given hands (any sizes), ready for `leader` (default landlord)."""
    n = config.num_players
    if levels is None:
        levels = [config.start_level] * n
        levels[landlord] = trump_rank
    suit = None if trump_suit is None else int(trump_suit)
    ctx = make_ctx(trump_rank, suit, config.permanent_trump_ranks)
    decl = Declaration(landlord, BIG_JOKER, 2) if suit is None else Declaration(landlord, suit * 13 + trump_rank - 2, 1)
    leader = landlord if leader is None else leader
    calls = tuple(calls)
    st = RoundState(
        config=config, seed=seed, redeals=0, levels=tuple(levels), eligible=tuple(range(n)),
        first_seat=0, phase=Phase.PLAY, to_act=leader, deck=(), dealt=n * config.hand_size,
        hands=tuple(tuple(sorted(h)) for h in hands), declaration=decl, declare_history=(decl,),
        landlord=landlord, ctx=ctx, kitty=(), buried=tuple(sorted(buried)), calls=calls,
        solo_called=solo, slots=(None,) * len(calls), slot_tricks=(None,) * len(calls),
        friends=tuple(friends), leader=leader, trick=(), lead=None, attempted=None, tricks=(),
        points_won=tuple(points_won) if points_won is not None else (0,) * n, result=None,
        closing_left=0, copies_seen=tuple((c, 0) for c in sorted({c.card for c in calls})),
    )  # fmt: skip
    return st
