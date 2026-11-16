"""Deck building and dealing."""

from __future__ import annotations

import random
from dataclasses import dataclass

from engine.cards import ALL_CARD_TYPES
from engine.config import GameConfig


@dataclass(frozen=True)
class Deal:
    hands: list[list[int]]
    kitty: list[int]


def build_deck(num_decks: int = 3) -> list[int]:
    return [c for c in ALL_CARD_TYPES for _ in range(num_decks)]


def deal(config: GameConfig, rng: random.Random | int | None = None) -> Deal:
    """Shuffle and deal one card at a time; the last `kitty_size` cards are the kitty.

    `rng` is a random.Random (reused across deals) or a seed.
    """
    if not isinstance(rng, random.Random):
        rng = random.Random(rng)
    deck = build_deck(config.num_decks)
    rng.shuffle(deck)
    n = config.num_players
    dealt = n * config.hand_size
    return Deal(
        hands=[deck[seat:dealt:n] for seat in range(n)],
        kitty=deck[dealt:],
    )
