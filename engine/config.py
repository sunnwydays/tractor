"""Game configuration. Every house-rule option from game_rules.md lands here."""

from __future__ import annotations

from dataclasses import dataclass

from engine.cards import NUM_CARD_TYPES

# num_players -> (num_decks, kitty_size, num_friends), from the Setup table.
PLAYER_TABLE = {
    7: (3, 8, 2),
    8: (3, 10, 3),
    9: (3, 9, 3),
}


@dataclass(frozen=True)
class GameConfig:
    num_players: int = 7
    num_decks: int = 3
    kitty_size: int = 8
    num_friends: int = 2

    def __post_init__(self) -> None:
        dealt = self.total_cards - self.kitty_size
        if self.num_players < 2 or dealt <= 0 or dealt % self.num_players:
            raise ValueError(
                f"{self.total_cards} cards minus a kitty of {self.kitty_size} "
                f"don't split evenly among {self.num_players} players"
            )
        if not 0 <= self.num_friends < self.num_players:
            raise ValueError(f"bad num_friends: {self.num_friends}")

    @classmethod
    def for_players(cls, num_players: int) -> GameConfig:
        if num_players not in PLAYER_TABLE:
            raise ValueError(
                f"no default setup for {num_players} players; "
                f"known: {sorted(PLAYER_TABLE)}"
            )
        decks, kitty, friends = PLAYER_TABLE[num_players]
        return cls(num_players, decks, kitty, friends)

    @property
    def total_cards(self) -> int:
        return self.num_decks * NUM_CARD_TYPES

    @property
    def hand_size(self) -> int:
        return (self.total_cards - self.kitty_size) // self.num_players

    @property
    def total_points(self) -> int:
        return 100 * self.num_decks
