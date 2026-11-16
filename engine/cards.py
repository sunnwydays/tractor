"""Card model.

A card is a plain int, 0..53, naming a card *type* (suit + rank, or a joker).
A multi-deck game simply holds several equal ints. Ints keep deals fast and
hashable; use the helpers below to read or print them.

    0..51  -> suit * 13 + (rank - 2), rank 2..14 (J=11, Q=12, K=13, A=14)
    52     -> small joker
    53     -> big joker

`TrumpContext` adds what depends on the round: each card's effective suit
(an off suit or TRUMP) and its order inside that suit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Suit(IntEnum):
    SPADES = 0
    HEARTS = 1
    CLUBS = 2
    DIAMONDS = 3


SUIT_SYMBOLS = "♠♥♣♦"
SUIT_LETTERS = "SHCD"
RANKS = tuple(range(2, 15))
RANK_NAMES = {11: "J", 12: "Q", 13: "K", 14: "A"}
RANK_VALUES = {"J": 11, "Q": 12, "K": 13, "A": 14}

SMALL_JOKER = 52
BIG_JOKER = 53
NUM_CARD_TYPES = 54
ALL_CARD_TYPES = tuple(range(NUM_CARD_TYPES))

# Effective-suit id for trump. Off suits use their Suit value (0..3).
TRUMP = 4


def make_card(suit: Suit | int, rank: int) -> int:
    if rank not in RANKS:
        raise ValueError(f"rank must be 2..14, got {rank}")
    return int(suit) * 13 + rank - 2


def is_joker(card: int) -> bool:
    return card >= SMALL_JOKER


def suit_of(card: int) -> Suit | None:
    """Printed suit (None for jokers). For the suit used in play, see TrumpContext."""
    return None if card >= SMALL_JOKER else Suit(card // 13)


def rank_of(card: int) -> int | None:
    """Printed rank 2..14 (None for jokers)."""
    return None if card >= SMALL_JOKER else card % 13 + 2


_POINTS = tuple(
    0 if c >= SMALL_JOKER else {5: 5, 10: 10, 13: 10}.get(c % 13 + 2, 0)
    for c in ALL_CARD_TYPES
)


def points(card: int) -> int:
    """5 = 5, 10 = 10, K = 10, everything else 0."""
    return _POINTS[card]


def rank_name(rank: int) -> str:
    return RANK_NAMES.get(rank, str(rank))


def card_name(card: int) -> str:
    if card == SMALL_JOKER:
        return "SJ"
    if card == BIG_JOKER:
        return "BJ"
    return f"{rank_name(card % 13 + 2)}{SUIT_SYMBOLS[card // 13]}"


def parse_suit(text: str) -> Suit:
    t = text.strip().upper()
    if len(t) == 1 and t in SUIT_LETTERS:
        return Suit(SUIT_LETTERS.index(t))
    if len(t) == 1 and t in SUIT_SYMBOLS:
        return Suit(SUIT_SYMBOLS.index(t))
    raise ValueError(f"unknown suit: {text!r}")


def parse_rank(text: str) -> int:
    t = text.strip().upper()
    rank = RANK_VALUES.get(t) or (int(t) if t.isdigit() else 0)
    if rank not in RANKS:
        raise ValueError(f"unknown rank: {text!r}")
    return rank


def parse_card(text: str) -> int:
    """Parse 'A♠', 'AS', '10h', 'SJ', 'BJ'."""
    t = text.strip().upper()
    if t == "SJ":
        return SMALL_JOKER
    if t == "BJ":
        return BIG_JOKER
    return make_card(parse_suit(t[-1]), parse_rank(t[:-1]))


@dataclass(frozen=True)
class TrumpContext:
    """Trump rank + trump suit (None = 无主) for one round.

    Each card gets an effective suit (`group`: an off suit 0..3, or TRUMP) and
    an `order` inside it. Orders are consecutive ints, so two cards can chain
    in a tractor exactly when their orders differ by 1. Cards that are equal
    in rank but different in suit (off-suit 2s, off-suit trump-rank cards)
    share an order.

    Trump order, low to high: trump-suit cards, off-suit 2s, trump-suit 2,
    off-suit trump rank, trump-suit trump rank, small joker, big joker.
    In 无主 the trump-suit steps don't exist, so the chain is
    2s -> trump rank -> small joker -> big joker.
    """

    trump_rank: int
    trump_suit: Suit | None = None
    permanent_trump_ranks: tuple[int, ...] = (2,)

    _group: tuple[int, ...] = field(init=False, repr=False, compare=False)
    _order: tuple[int, ...] = field(init=False, repr=False, compare=False)
    _levels: dict[int, tuple[tuple[int, ...], ...]] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.trump_rank not in RANKS:
            raise ValueError(f"trump rank must be 2..14, got {self.trump_rank}")
        if self.trump_suit is not None:
            object.__setattr__(self, "trump_suit", Suit(self.trump_suit))

        group = [TRUMP] * NUM_CARD_TYPES
        order = [0] * NUM_CARD_TYPES

        # Ranks that are always trump, low to high; the trump rank sits on top.
        special = sorted(set(self.permanent_trump_ranks) - {self.trump_rank})
        special.append(self.trump_rank)
        plain = [r for r in RANKS if r not in special]

        for suit in Suit:
            for i, rank in enumerate(plain):
                c = make_card(suit, rank)
                group[c] = TRUMP if suit == self.trump_suit else int(suit)
                order[c] = i

        level = len(plain) if self.trump_suit is not None else 0
        for rank in special:
            for suit in Suit:
                if suit != self.trump_suit:
                    order[make_card(suit, rank)] = level
            level += 1
            if self.trump_suit is not None:
                order[make_card(self.trump_suit, rank)] = level
                level += 1
        order[SMALL_JOKER] = level
        order[BIG_JOKER] = level + 1

        levels: dict[int, list[list[int]]] = {}
        for c in ALL_CARD_TYPES:
            rows = levels.setdefault(group[c], [])
            while len(rows) <= order[c]:
                rows.append([])
            rows[order[c]].append(c)

        object.__setattr__(self, "_group", tuple(group))
        object.__setattr__(self, "_order", tuple(order))
        object.__setattr__(
            self,
            "_levels",
            {g: tuple(tuple(r) for r in rows) for g, rows in levels.items()},
        )

    @property
    def groups(self) -> tuple[int, ...]:
        """Effective suits in play: the off suits, then TRUMP."""
        return tuple(int(s) for s in Suit if s != self.trump_suit) + (TRUMP,)

    def effective_suit(self, card: int) -> int:
        return self._group[card]

    def order(self, card: int) -> int:
        return self._order[card]

    def is_trump(self, card: int) -> bool:
        return self._group[card] == TRUMP

    def levels(self, group: int) -> tuple[tuple[int, ...], ...]:
        """Card types of an effective suit, low to high; equal cards share a level."""
        return self._levels[group]

    def group_name(self, group: int) -> str:
        if group != TRUMP:
            return SUIT_SYMBOLS[group]
        return "trump" if self.trump_suit is not None else "trump (无主)"

    def describe(self) -> str:
        suit = "无主" if self.trump_suit is None else SUIT_SYMBOLS[self.trump_suit]
        return f"trump rank {rank_name(self.trump_rank)}, trump suit {suit}"
