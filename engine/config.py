"""Game configuration. Every house-rule option from game_rules.md lands here.

Options that come from a `[?]` line in the rules are marked `[?]` below.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.cards import NUM_CARD_TYPES

# num_players -> (num_decks, kitty_size, num_friends), from the Setup table.
PLAYER_TABLE = {
    7: (3, 8, 2),
    8: (3, 10, 3),
    9: (3, 9, 3),
}

MAX_LEVEL = 14  # A

LANDLORD = "landlord"
PEASANTS = "peasants"

# (min peasant points, winning side, levels gained). The row that applies is
# the last one whose minimum is <= the peasants' points.
ScoreRow = tuple[int, str, int]


def default_score_table(num_decks: int) -> tuple[ScoreRow, ...]:
    """The Shengji table: step = 20 x decks, peasants win at 40 x decks."""
    step = 20 * num_decks
    return (
        (0, LANDLORD, 3),
        (5, LANDLORD, 2),
        (step, LANDLORD, 1),
        (2 * step, PEASANTS, 0),
        (3 * step, PEASANTS, 1),
        (4 * step, PEASANTS, 2),
        (5 * step, PEASANTS, 3),
    )


@dataclass(frozen=True)
class KittyMultiplier:
    """Kitty points multiplier when the peasants win the last trick, by the
    biggest structure of the winning play."""

    single: int = 2
    pair: int = 4
    triple: int = 4  # [?] same as a pair until we decide
    tractor: int = 4  # [?] same as a pair until we decide

    def for_structure(self, width: int, length: int) -> int:
        if length >= 2:
            return self.tractor
        return {1: self.single, 2: self.pair}.get(width, self.triple)


@dataclass(frozen=True)
class GameConfig:
    num_players: int = 7
    num_decks: int = 3
    kitty_size: int = 8
    num_friends: int = 2

    # Levels
    start_level: int = 3
    must_defend_levels: tuple[int, ...] = (10, 11, 14)
    # House rule: friends on a winning landlord team also pass their own
    # must-defend level. False = only the landlord does.
    friends_pass_must_defend: bool = True
    j_penalty: bool = True
    win_condition: str = "landlord_defends_ace"
    k_rule: str = "none"  # [?] special rule at K
    a_rule: str = "none"  # [?] special rule at A (beyond the win condition)

    # Cards
    permanent_trump_ranks: tuple[int, ...] = (2,)
    two_deck_max_players: int = 5  # [?] at most this many players -> 2 decks

    # Declaring
    no_declaration: str = "redeal"  # [?]
    # Redeal the whole table if any player's dealt hand has no J, Q or K
    # (jokers and A don't count).
    no_face_redeal: bool = True

    # Friends
    allow_solo: bool = True
    solo_win_multiplier: int = 2
    # [?] On an alive call, the landlord playing a copy of the called card:
    # "waste" = it counts as a played copy (and wastes the slot if that
    # ordinal was called); "ignore" = it doesn't count at all.
    alive_landlord_copy: str = "waste"

    # Play
    # False = you may keep a triple intact instead of following a pair lead.
    split_triple_to_follow_pair: bool = False

    # Scoring
    kitty_multiplier: KittyMultiplier = KittyMultiplier()
    score_table: tuple[ScoreRow, ...] | None = None  # None = default for the deck count

    def __post_init__(self) -> None:
        dealt = self.total_cards - self.kitty_size
        if self.num_players < 2 or dealt <= 0 or dealt % self.num_players:
            raise ValueError(
                f"{self.total_cards} cards minus a kitty of {self.kitty_size} "
                f"don't split evenly among {self.num_players} players"
            )
        if not 0 <= self.num_friends < self.num_players:
            raise ValueError(f"bad num_friends: {self.num_friends}")
        if self.no_declaration not in ("redeal",):
            raise ValueError(f"unknown no_declaration: {self.no_declaration!r}")
        if self.alive_landlord_copy not in ("waste", "ignore"):
            raise ValueError(f"unknown alive_landlord_copy: {self.alive_landlord_copy!r}")
        if self.win_condition not in ("landlord_defends_ace",):
            raise ValueError(f"unknown win_condition: {self.win_condition!r}")
        if self.k_rule != "none" or self.a_rule != "none":
            raise ValueError("no special K / A rules are implemented yet")

    @classmethod
    def for_players(cls, num_players: int, **options) -> GameConfig:
        if num_players not in PLAYER_TABLE:
            raise ValueError(
                f"no default setup for {num_players} players; "
                f"known: {sorted(PLAYER_TABLE)}"
            )
        decks, kitty, friends = PLAYER_TABLE[num_players]
        return cls(num_players, decks, kitty, friends, **options)

    @property
    def total_cards(self) -> int:
        return self.num_decks * NUM_CARD_TYPES

    @property
    def hand_size(self) -> int:
        return (self.total_cards - self.kitty_size) // self.num_players

    @property
    def total_points(self) -> int:
        return 100 * self.num_decks

    @property
    def resolved_score_table(self) -> tuple[ScoreRow, ...]:
        return self.score_table or default_score_table(self.num_decks)
