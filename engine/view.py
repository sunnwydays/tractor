"""What one player may know: a cheap field copy of the state without hidden cards."""

from __future__ import annotations

from dataclasses import dataclass

from engine import rules, scoring
from engine.cards import TrumpContext
from engine.config import GameConfig
from engine.state import Declaration, FriendCall, Phase, RoundState, TrickRecord


@dataclass(frozen=True, slots=True)
class PlayerView:
    player: int
    config: GameConfig
    phase: Phase
    to_act: int
    levels: tuple[int, ...]
    eligible: tuple[int, ...]
    first_seat: int
    deal_complete: bool
    hand: tuple[int, ...]
    hand_sizes: tuple[int, ...]
    declaration: Declaration | None
    declare_history: tuple[Declaration, ...]
    landlord: int | None
    ctx: TrumpContext | None
    kitty: tuple[int, ...] | None  # landlord only
    buried: tuple[int, ...] | None  # landlord only
    num_buried: int
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


def make_view(st: RoundState, player: int) -> PlayerView:
    """The state as `player` sees it: own hand only, kitty and buried only for the landlord."""
    mine = player == st.landlord
    return PlayerView(
        player, st.config, st.phase, st.to_act, st.levels, st.eligible, st.first_seat,
        st.deal_complete, st.hands[player], tuple(map(len, st.hands)), st.declaration,
        st.declare_history, st.landlord, st.ctx, st.kitty if mine else None,
        st.buried if mine else None, len(st.buried), st.calls, st.solo_called, st.slots,
        st.slot_tricks, st.friends, st.leader, st.trick, st.lead, st.attempted, st.tricks,
        st.points_won, st.result,
    )  # fmt: skip
