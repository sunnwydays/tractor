# Milestone 2: rules engine, simple bots, round stats (done 2026-11-15)

## What was built
- `engine/config.py`: every named option plus one per `[?]` line.
- `engine/rules.py`: pure card rules: `decompose`, leads, throws, follow legality, trick winner.
- `engine/scoring.py`: score table, level changes, must-defend, J penalty, kitty multiplier, solo bonus, game winner.
- `engine/state.py`: `RoundState` + `new_round`, `legal_actions`, `is_legal`, `apply` (pure; phases DEAL → BURY → CALL → PLAY → DONE). `state_for_play` builds a play-phase state by hand (tests, later puzzles).
- `engine/view.py`: `PlayerView` / `make_view`: what one player may know.
- `engine/runner.py`: `play_round`, `play_match` (carries levels and the next declaring team).
- `bots/`: `Bot.choose(view, legal) -> action`, `RandomBot`, `GreedyBot`.
- `stats/rounds.py`, `stats/round_report.py`: per-round summary, aggregation, report.

## Commands
- Tests: `python -m pytest -q` (215 tests, about 50 s; most of it is the random-round invariants).
- Report: `python -m stats.round_report` → `reports/round_stats.md` (flags: `--rounds`, `--seed`, `--players`, `--bots`, `--workers`, `--out`). 10k rounds × 3 player counts × 2 bots takes about 3.5 min using all cores. Output doesn't depend on `--workers`.
- Speed: a random round is about 9–13 ms, a greedy round about 14–21 ms (7–9 players).

## Defaults picked for the `[?]` options
| Rule | Option | Default |
|---|---|---|
| Deck threshold | `two_deck_max_players` | 5 (stored only; setups exist for 7–9 players) |
| Nobody declares | `no_declaration` | `"redeal"` (the only value implemented) |
| Alive call, landlord plays a copy | `alive_landlord_copy` | `"waste"` (matches the "ending up alone by accident" line); `"ignore"` also works |
| Kitty multiplier for triple / tractor | `kitty_multiplier.triple`, `.tractor` | ×4, same as a pair |
| Special rules at K, A | `k_rule`, `a_rule` | `"none"` (nothing else implemented) |

Other options added: `friends_pass_must_defend` (True), `solo_win_multiplier` (2), `split_triple_to_follow_pair` (False).

## Ambiguous rules: please confirm
**Declaring**
- You can declare when you're dealt a level card or joker, and in a closing round after the deal that goes round the table until everyone passes. So contesting with cards you already hold waits for one of those two moments.
- Joker declarations need a pair. Strength: joker pair > any level-card declaration; among jokers, more copies, then big over small.
- The current declarer can only reinforce (same card, more copies), not switch suit.
- Later rounds use the same rule as round 1: eligible players flip a card of their own level.

**Friend calls**
- A call is card + ordinal + dead/alive. Slot k goes to whoever plays the k-th counted copy.
- Dead: the landlord's own copies never count; legal only when landlord's copies (hand + buried) = decks − number of calls on that card.
- Alive + `"waste"`: the landlord's copy counts as a played copy, and wastes the slot only if that ordinal was called (so "the 2nd K♠" while holding one K♠ is safe).
- Calls can't be in the trump suit; in 无主 all four suits are callable.

**Play**
- A play is split into groups biggest-first (333 44 = tractor 33-44 + single 3). More than one group = a throw.
- A throw's group is beatable when another player holds a higher same-shape group in that suit (trumping doesn't count). The forced play is the smallest beatable group: fewest cards, then lowest.
- Following a tractor: play a same-length tractor if you have one, otherwise as many pairs as you can. Shorter tractors aren't required.
- Triple exemption: a triple is never forced apart to cover a pair demand (pair lead, or pairs owed for a tractor), but you may split it by choice.
- Beating a throw with trumps: match every group; compare the top card of the biggest group.

**Scoring**
- Points are tracked per player and summed at the end, so a friend's points move with them whenever they reveal.
- Kitty multiplier uses the biggest group of the last trick's lead.
- J penalty hits revealed friends only. Peasants never pass a must-defend level.
- Total over 300 still gives peasants +3 (the table's top row).

## Caps in `legal_actions` (`is_legal` accepts everything)
- Throws: only "top k cards of a suit" are listed. RandomBot picks these often (about 7 failed throws a round); GreedyBot never throws.
- Follows: all legal follows when there are ≤ 400 candidates (always true for single and pair leads); beyond that a structured subset.
- Friend calls: the top 4 callable ranks per suit, ordinals 1..m, alive, plus the dead variant where possible.
- Bury is one card per action, so it's fully enumerated.
- Redeals stop with an error after 1000 in a row.

## GreedyBot in one screen
- Declares with ≥ 36% would-be trumps (someone always declares in the closing round); buries pointless short-suit cards; calls the highest cards it doesn't fully hold (dead when it can).
- Leads boss cards, fishes for friends in the called suit, then long suits; follows by revealing, feeding teammates, winning point tricks cheaply, else dumping low.
- First numbers (7 players, 10k rounds): landlord team wins 36% (random: 14%), friends revealed by trick 2–3, almost no kitty points buried.

## Not done (left for later)
- Greedy throws, and card counting beyond "is my top card boss".
- Other `no_declaration` behaviours and any K / A rules.
