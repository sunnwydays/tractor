# Project brief: Finding Friends (找朋友) lab

A personal tool to **play, watch and analyze** our house version of Finding Friends (rules in `game_rules.md`), growing from card-counting stats to strong machine play.

## Goals, in priority order

1. **Deal stats (no engine needed).** Monte Carlo over deals, exact combinatorics where it's easy. Questions:
   - P(a player holds a tractor / triple / pair of jokers), by suit and for trump.
   - P(a player is void or short in a suit), at the deal and after the kitty swap.
   - Kitty points distribution.
   - Friend calls: for "Nth X♠ dead/alive", how many copies the landlord / others hold, and P(the call lands where you want).
   - Everything parameterized by `num_players` (7/8/9), decks, trump rank/suit.
2. **Rules engine + simple bots.** Full round per `game_rules.md` (declaring, kitty, friend calls, follow rules, throws, scoring, levels), config options for every `[?]`. Random and greedy bots so whole rounds can be simulated. Unlocks round stats:
   - tricks per round, peasant points per round, kitty points won, level change distribution;
   - when friends get revealed (trick N), dead vs alive outcomes.
3. **Play and visualize.** Local web UI: me vs bots, plus a replay viewer that steps through simulated games (every hand visible, trick by trick). A live "counter" panel: cards played, remaining points, who's void in what, P(each player holds X).
4. **Human strategy principles.** Turn ideas into bot rules and A/B them over many games, e.g. "void a short suit early", "bury points vs no points", "dead vs alive calls", "when to go solo", "when should a friend reveal". Output: a list of principles with measured win-rate effect.
5. **Strong machine play.** ISMCTS first (no training needed), then maybe Deep Monte Carlo RL (DouZero / ShengJi+ style). Advice mode in the UI: "what to bury", "which friends to call", "what to play".

## Tech

- Python core (`engine/`, `stats/`, `bots/`), pure functions over a game state; each player gets only its own view, so humans, bots and the UI use one interface.
- Stats via scripts or notebooks; plots with matplotlib.
- Web UI later: small Python server (FastAPI) + plain JS/HTML front end.
- Performance: start in plain Python; optimize (numpy / numba / Rust core) only when RL actually needs millions of games.

## First milestone: deal stats

Card model, config for 7/8/9 players, dealer, and a stats module that answers the goal-1 questions.

**Done when:**
- `pytest` passes, covering card counts, deal sizes and tractor detection (incl. skipping trump rank and 2s).
- One command prints a report (markdown) with the goal-1 numbers for 7, 8 and 9 players, from ≥100k deals each, with exact values matching simulation where both exist.

## Later milestones (rough)

2. Engine + random/greedy bots → round-stats report.
3. Web UI: replay viewer, then playing vs bots.
4. Strategy A/B harness + principles list.
5. ISMCTS bot; then decide whether RL is worth it.

## Out of scope

- Online play with friends (robertying.com/shengji covers that).
- Other variants (4-player Tractor, 斗地主).
- Mobile app, accounts, polish beyond "usable by me".
- Settling the score bands up front: they stay config options; balancing them is a possible later use of the simulator, not a goal now.
