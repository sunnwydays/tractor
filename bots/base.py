"""The bot interface."""

from __future__ import annotations

from typing import Protocol

from engine.state import Action
from engine.view import PlayerView


class Bot(Protocol):
    def choose(self, view: PlayerView, legal: list[Action]) -> Action:
        """Pick one of `legal` for the player `view.player`."""
        ...
