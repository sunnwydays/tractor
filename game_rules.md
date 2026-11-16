# Finding Friends (找朋友) — house rules

Draft based on standard Finding Friends rules plus our house rules. Lines marked **[?]** are guesses or still open — edit freely.
Each rule that varies between groups has a name in `code` so it can become a config option later.

Terms: **landlord** (庄家) = declarer; **landlord team** = landlord + friends; **peasants** = everyone else.

## Setup

- Players: flexible, usually 7+ (`num_players`). Defaults below assume 7.
- Decks: 3 standard decks with jokers = 162 cards (`num_decks: 3`).
  - 7–9 players: 3 decks.
  - Fewer players → 2 decks. **[?]** Threshold — maybe ≤ 5 players = 2 decks?

| Players | Decks | Friends | Teams | Cards each + kitty |
|---|---|---|---|---|
| 7 | 3 | 2 | 3 vs 4 | 22 + 8 |
| 8 | 3 | 3 | 4 vs 4 | 19 + 10 |
| 9 | 3 | 3 | 4 vs 5 | 17 + 9 |

- Each player has their **own level**, starting at **3** (`start_level: 3`). Levels go 3 → A; you win by defending A (see Special levels).
- Points in the deck: 5 = 5, 10 = 10, K = 10. That's 100 per deck, **300 total** with 3 decks.

## Card ranking

The **trump rank** = the landlord's declared level. The **trump suit** is picked by declaring (or no-trump, 无主).

Trumps, low → high:
1. Trump-suit cards (3…A, skipping the trump rank)
2. 2s in off suits (all equal), then the 2 of the trump suit (`permanent_trump_ranks: [2]`)
3. Trump-rank cards in off suits (all equal to each other)
4. Trump-rank card in the trump suit
5. Small joker
6. Big joker

Off-suit cards rank 3…A (minus the trump rank, which counts as trump).
In 无主: only jokers, trump-rank cards and 2s are trump.

Identical cards played in the same trick: first one played wins.

## Dealing and declaring trump

- Cards are dealt one at a time, with a kitty (底牌) set aside — sizes per the player table in Setup (`kitty_size`).
- **Round 1:** everyone is at level 3. While being dealt, anyone may flip a **3** to set the trump suit and become landlord.
- **Later rounds:** only players on the team that won last round may declare (see "Next landlord"). They flip a card of **their own level**; that level becomes the trump rank and the declarer becomes landlord.
- **Contesting:** another eligible player can override with a **pair of their own level**; a **triple** beats a pair.
  - You can't contest in the **same suit** as the current declaration (e.g. someone flipped 3♥ — your pair of 3♥ can't take it).
  - You **can reinforce** your own single into a pair (or pair into triple) to protect it.
- **Double joker** (pair of jokers) overrides anything and makes it **无主** (no trump suit). The landlord's level is still the trump rank.
- **[?]** Nobody declares: never happened to us. Default: redeal.
- **No "clothes" redeal** (`no_face_redeal`): a player whose dealt hand has no face cards (J, Q, K) may call for a redeal (whole table).
  - Jokers and A are not face cards. The check is on the dealt hand only, before the kitty.

## Kitty

- The landlord picks up the kitty and buries the same number of cards face down.
- You can bury as many points as you want.

## Calling friends

- After burying, the landlord calls friends by naming an **ordinal + card**, e.g. "the 1st A♥", "the 2nd K♠".
- Number of friends: landlord team should never be bigger than the peasants.
  For 7 players: **2 friends** → 3 vs 4 (`num_friends`).
- Callable cards: **no trumps or jokers** (so no 2s or trump-rank cards); highest is **A**.
- **Both friends must be called in the same suit.**
- Each call is made **dead or alive** (死/活):
  - **Dead:** the landlord holds the remaining copies, so *anyone else* holding that card is guaranteed a friend.
    E.g. "two A♠ dead" (3 decks) → landlord has one A♠; the two other A♠ holders are the friends.
  - **Alive:** the landlord may not hold any, so holding the card only *might* make you a friend — the first N copies played by others count.
    E.g. "two A♠ alive" → up to 3 people could have one; whoever plays the first two are friends.
  - **[?]** On an alive call, if the landlord happens to play a copy, does it waste a slot (see below) or just not count?
- The person who plays the called card joins the landlord team once that trick finishes, and brings any points they've won.
- If the landlord plays their own called card, that friend slot is wasted (landlord team is smaller).
- If the same person fulfils two friend calls, the team is just smaller.
- **Going solo — calling the kitty:** the landlord can call the kitty instead of friends and play alone against everyone (`allow_solo`).
  - Winning solo **on purpose** (called the kitty) **doubles** your level gain from the score table. If you lose solo, the peasants gain levels normally (not doubled).
  - Ending up alone by accident (e.g. on alive calls the landlord plays their own copies first) is rare; it scores normally.

## Play

- Landlord leads the first trick. Winner of each trick leads the next.
- Legal leads (all from one suit, trump counts as one suit):
  - **Single**
  - **Pair** — 2 identical cards
  - **Triple** — 3 identical cards
  - **Tractor** (拖拉机) — 2+ consecutive pairs, or 2+ consecutive triples, in the same suit.
    Ranks are consecutive after removing trump-rank cards and 2s, e.g. if 7 is trump rank, 6-6-8-8 is a tractor.
    In trump, the whole trump order chains: trump-suit cards chain normally (e.g. trump 3-3-4-4, if neither is the trump rank), then trump-suit A pair → off-suit 2 pair → trump-suit 2 pair → off-suit trump-rank pair → trump-suit trump-rank pair → small-joker pair → big-joker pair.
    Off-suit 2s / trump-rank cards of different suits are equal rank, so e.g. 2♠2♠ + 2♣2♣ is *not* a tractor.
  - **Throw** (甩牌) — several of the above in one suit at once.
    The thrower asks the table whether anyone can beat **any group** in the throw.
    If someone can, the thrower must play **just the smallest beatable group** instead. No other penalty.
    (In practice you only throw when every group is the top remaining.)
- **Following:**
  - Must play the same number of cards.
  - Must follow suit if you can.
  - Within the suit, must match the structure as best you can: tractor → tractor, else pairs/triples; triple → triple, else a pair + a single; pair → pair, etc.
    You **don't** have to split a triple to follow a pair lead — you can play other cards of the suit instead. Only if the triple is all you have left in the suit do you play two cards from it.
  - If you're out of the suit, play anything (including trump).
- **Winning a trick:** the highest play of the led suit wins, unless someone trumps it with **the same structure** in trump.
  A non-matching play (e.g. two random trumps against a pair) can't win.

## Scoring

- Only the **peasants** collect points from tricks won.
- **Kitty:** if the peasants win the last trick, they get the kitty's points **× 2**.
  If they win the last trick **with a pair**, kitty points are **× 4** (`kitty_multiplier`).
  **[?]** Triple or tractor winning the last trick — higher multiplier?

Level changes — Shengji tables, by deck count (`score_table`). Step = 20 × decks; peasants win at 40 × decks.

| Result | 2 decks | 3 decks | 4 decks |
|---|---|---|---|
| Landlord team +3 | 0 | 0 | 0 |
| Landlord team +2 | 5–35 | 5–55 | 5–75 |
| Landlord team +1 | 40–75 | 60–115 | 80–155 |
| Peasants win, no level change | 80–115 | 120–175 | 160–235 |
| Peasants +1 | 120–155 | 180–235 | 240–315 |
| Peasants +2 | 160–195 | 240–295 | 320–395 |
| Peasants +3 | 200+ | 300+ | 400+ |

"Peasants win" (any of the bottom four rows) means the peasants declare next round.

### Next landlord
- Whichever team won the round declares next round: landlord team wins → they declare again; peasants win → peasants declare.

### Special levels
- **Must-defend levels: 10, J, A** (`must_defend_levels: [10, J, A]`).
  - Going up from below one stops at it (e.g. 8 +3 → 10).
  - You only move past it by **winning on the landlord team** while at that level.
  - This applies to friends too (house rule — strictly it's only the landlord, but that stalls the game).
- **J penalty:** if the landlord declared at J and the landlord team **loses** (`j_penalty`):
  - the landlord (who took the kitty) drops back to **3**;
  - every friend drops to **half their own level, rounded down** (e.g. 9 → 4, 10 → 5), but never below 3.
- **K:** **[?]** maybe special — describe.
- **A:** **[?]** any other special rules — describe.
- **Winning the game:** you win by **defending A** — winning **as the landlord** (the declarer, at A) (`win_condition`). A friend at A on the winning team does not win the game.

## Strategy notes (not rules — ideas for bots to learn / test)
- **Voiding a suit:** once you're out of a suit, you can trump in when it's led and win the trick. So it's often good to get rid of a short suit early (or bury it in the kitty as landlord).
- Running a suit you're long in forces others to discard or trump in.
- Friends usually want to reveal themselves when it helps (e.g. winning a trick with points for the landlord team); staying hidden can also mislead peasants.

## Still open
- Deck count threshold by player count.
- Kitty multiplier for triples/tractors.
- Solo scoring details.
- No-clothes redeal details (jokers, scope).
- Rules at K, A; details of J.
- Anything else from our games: _______
