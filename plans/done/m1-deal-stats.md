# Milestone 1: deal stats (done 2026-11-15)

## What was built
- `engine/cards.py`: cards as ints 0..53 (card types), points, names/parsing, and `TrumpContext` (effective suit + order of every card for a trump rank and trump suit or 无主).
- `engine/config.py`: `GameConfig` with the 7/8/9-player table (`GameConfig.for_players(n)`).
- `engine/deal.py`: `build_deck`, seeded `deal(config, rng_or_seed)` → hands + kitty.
- `engine/hand.py`: pure functions: `group_by_suit`, `find_pairs`, `find_triples`, `find_tractors`, `analyze_hand`.
- `stats/exact.py`: exact probabilities (hypergeometric + a small polynomial counting method that also covers tractors).
- `stats/simulate.py`: Monte Carlo through the engine's `deal` and `analyze_hand`.
- `stats/report.py`: builds the report and checks every sim value against its exact value.

## Commands
- Tests: `python -m pytest -q`
- Report: `python -m stats.report` → `reports/deal_stats.md` (flags: `--deals`, `--seed`, `--trump-rank`, `--trump-suit S|H|C|D|none`, `--players`, `--out`). About 20 s for 3 × 100k deals.

## Choices made along the way
- A triple counts as a pair. Tractors are counted as maximal runs (5-5-6-6-7-7 = one tractor of length 3).
- 无主: the trump chain is 2s → trump rank → small joker → big joker, with no gaps for the missing trump-suit steps.
- A♥A♥ + 2♥2♥ is not a tractor when ♥ is trump: the off-suit 2 level sits between them.
- Friend-call stats put the kitty in the landlord's hand and assume they don't bury copies of the called card.

## Not done (left for later)
- Void/short stats after the kitty swap (needs a burying policy, so it belongs with the bots in milestone 2).
- Trump length for a declarer who chose trump because they were long in it.
