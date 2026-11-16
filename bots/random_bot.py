"""A bot that picks uniformly among the legal actions."""

from __future__ import annotations

import random

from engine.state import Action
from engine.view import PlayerView


class RandomBot:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def choose(self, view: PlayerView, legal: list[Action]) -> Action:
        return self.rng.choice(legal)
