# Finding Friends lab

A tool to play, watch and analyze our house version of Finding Friends (找朋友), a Tractor / Shengji variant with 3 decks and 7–9 players.

Right now it is a simulator: a full rules engine, two simple bots, and two statistics reports. There is no UI yet, so everything runs from the terminal.

- Rules: [game_rules.md](game_rules.md)
- Goals and roadmap: [plans/project-brief.md](plans/project-brief.md)
- What each milestone built: [plans/done/](plans/done/)

## Setup

Python 3.12. The only dependency is pytest.

```
pip install pytest
```

## What you can run

| Command | What it does |
|---|---|
| `python -m pytest -q` | Runs the tests (about 50 s). |
| `python -m stats.report` | Deal statistics → [reports/deal_stats.md](reports/deal_stats.md) |
| `python -m stats.round_report` | Round statistics from simulated games → [reports/round_stats.md](reports/round_stats.md) |

Both reports overwrite the committed file unless you pass `--out`.

**Deal stats** answer questions about the deal alone: how often a player holds a tractor, a triple or a joker pair, how often they are void or short in a suit, how many points sit in the kitty, and how friend calls land. Flags: `--deals`, `--seed`, `--trump-rank`, `--trump-suit S|H|C|D|none`, `--players`, `--out`.

**Round stats** play whole rounds with bots and report tricks per round, peasant points, kitty multipliers, level changes, the landlord team's win rate, when friends are revealed, dead vs alive calls, and how often 无主 is declared. Flags: `--rounds` (default 10000), `--seed`, `--players 7 8 9`, `--bots random greedy`, `--workers`, `--out`. The full default run takes about 3.5 minutes on all cores; `--rounds 1000` is a quick look.

## Play a round in Python

```python
from engine.config import GameConfig
from engine.runner import play_round
from bots.greedy_bot import GreedyBot

cfg = GameConfig.for_players(7)
final = play_round(cfg, [GreedyBot(seed=i) for i in range(7)], seed=42)

print(final.result)     # points, winner, new levels
print(final.tricks[0])  # every trick is recorded
```

`play_match` in `engine/runner.py` plays several rounds in a row and carries the levels and the next declaring team.

## Trying a house-rule variant

Every rule that varies between groups is an option on `GameConfig`, including the open questions marked `[?]` in the rules:

```python
cfg = GameConfig.for_players(7, alive_landlord_copy="ignore", j_penalty=False)
```

The report commands always use the defaults. To compare variants, call `stats.rounds.simulate(config, bot_factory, rounds, seed)` and `stats.rounds.aggregate(rows)` yourself.

## Layout

| Folder | Contents |
|---|---|
| `engine/` | Cards, config, dealing, hand analysis, play rules, scoring, round state, player view, runner |
| `bots/` | `RandomBot` and `GreedyBot`. A bot is anything with `choose(view, legal_actions) -> action` |
| `stats/` | Deal stats (exact + Monte Carlo) and round stats |
| `reports/` | Generated reports |
| `tests/` | pytest suite |
| `plans/` | Project brief and done notes |

The engine is pure functions over an immutable round state: `new_round`, `legal_actions(state)`, `is_legal(state, action)`, `apply(state, action)`. Each player only sees a `PlayerView`, so bots, and later humans and the UI, share one interface.

## Not built yet

- Playing a hand yourself and a replay viewer (milestone 3, a local web UI).
- A harness to A/B strategy ideas (milestone 4).
- Strong bots (milestone 5).
