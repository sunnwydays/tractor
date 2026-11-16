"""End-of-round scoring: kitty, score table, level changes, J penalty."""

from __future__ import annotations

from dataclasses import dataclass

from engine.config import LANDLORD, MAX_LEVEL, PEASANTS, GameConfig, ScoreRow


@dataclass(frozen=True)
class RoundResult:
    trick_points: int  # points in tricks won by the final peasants
    kitty_points: int  # face value of the buried cards
    kitty_multiplier: int  # 0 when the landlord team won the last trick
    peasant_points: int  # trick_points + kitty_points * kitty_multiplier
    winner: str  # LANDLORD or PEASANTS
    base_gain: int  # from the score table
    gain: int  # after the solo multiplier
    landlord_team: tuple[int, ...]  # landlord first, then friends
    peasants: tuple[int, ...]
    new_levels: tuple[int, ...]
    next_eligible: tuple[int, ...]  # the winning side: they may declare next round
    game_winner: int | None
    j_penalty_applied: bool


def score_row(config: GameConfig, peasant_points: int) -> ScoreRow:
    """The last table row whose minimum is <= peasant_points."""
    row = config.resolved_score_table[0]
    for r in config.resolved_score_table:
        if r[0] <= peasant_points:
            row = r
    return row


def advance_level(level: int, gain: int, config: GameConfig, *, can_pass_must_defend: bool) -> int:
    """Step up `gain` levels, capped at A. Arriving at a must-defend level stops
    there; leaving one is only possible on the first step, and only if allowed."""
    for step in range(gain):
        if level in config.must_defend_levels and (step > 0 or not can_pass_must_defend):
            break
        if level >= MAX_LEVEL:
            break
        level += 1
    return level


def score_round(
    config: GameConfig,
    *,
    levels,
    landlord,
    friends,
    solo_called,
    trump_rank,
    points_won,
    kitty_points,
    last_trick_winner,
    last_trick_width,
    last_trick_length,
) -> RoundResult:
    """Work out who won the round and every player's new level."""
    team = (landlord, *dict.fromkeys(f for f in friends if f != landlord))
    peasants = tuple(p for p in range(config.num_players) if p not in team)

    trick_points = sum(points_won[p] for p in peasants)
    if last_trick_winner in peasants:
        mult = config.kitty_multiplier.for_structure(last_trick_width, last_trick_length)
    else:
        mult = 0
    peasant_points = trick_points + kitty_points * mult

    _, winner, base_gain = score_row(config, peasant_points)
    new_levels = list(levels)
    j_penalty = False
    game_winner = None

    if winner == LANDLORD:
        gain = base_gain * config.solo_win_multiplier if solo_called else base_gain
        new_levels[landlord] = advance_level(
            levels[landlord], gain, config, can_pass_must_defend=True
        )
        for f in team[1:]:
            new_levels[f] = advance_level(
                levels[f], gain, config, can_pass_must_defend=config.friends_pass_must_defend
            )
        winners = tuple(sorted(team))
        if config.win_condition == "landlord_defends_ace" and trump_rank == MAX_LEVEL:
            game_winner = landlord
    else:
        gain = base_gain
        for p in peasants:
            new_levels[p] = advance_level(levels[p], gain, config, can_pass_must_defend=False)
        if config.j_penalty and trump_rank == 11:
            j_penalty = True
            new_levels[landlord] = config.start_level
            for f in team[1:]:
                new_levels[f] = max(config.start_level, levels[f] // 2)
        winners = peasants

    return RoundResult(
        trick_points=trick_points,
        kitty_points=kitty_points,
        kitty_multiplier=mult,
        peasant_points=peasant_points,
        winner=winner,
        base_gain=base_gain,
        gain=gain,
        landlord_team=team,
        peasants=peasants,
        new_levels=tuple(new_levels),
        next_eligible=winners,
        game_winner=game_winner,
        j_penalty_applied=j_penalty,
    )
