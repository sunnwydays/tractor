# Round statistics

- Rounds per player count and bot: 10,000
- Seed: 1
- Regenerate: `python -m stats.round_report --rounds 10000 --seed 1 --players 7 8 9 --bots random greedy --out reports/round_stats.md`
- Bots: random, greedy
- Each round comes from a match of up to 20 rounds with fresh bots, so levels and trump ranks vary.
- Everything below the Run time line is independent of the worker count.
- Run time: 220s

Config defaults (same for every player count unless the player table says otherwise):

- Start level 3, must-defend levels [10, 11, 14], J penalty True, win by defending A.
- Permanent trump ranks [2]; nobody declares -> redeal.
- Solo allowed True (x2 on a win); alive-call landlord copy: waste; split triple to follow a pair: False.
- Kitty multiplier: single x2, pair x4, triple x4, tractor x4.
- Score table (peasant points -> result): [(0, 'landlord', 3), (5, 'landlord', 2), (60, 'landlord', 1), (120, 'peasants', 0), (180, 'peasants', 1), (240, 'peasants', 2), (300, 'peasants', 3)].

## 7 players (22 cards each, kitty 8, 2 friends)

Rounds: random 10,000, greedy 10,000

### Tricks and points

Each hand has 22 cards, so a round has at most 22 tricks; a pair, tractor or throw lead uses several cards per trick and shortens the round. The decks hold 300 points.

|  | random | greedy |
|---|---|---|
| tricks mean | 20.09 | 16.85 |
| tricks min | 13 | 10 |
| tricks max | 22 | 22 |
| failed throws per round | 6.782 | 0.000 |
| rounds with a failed throw | 100.0% | 0.0% |

Peasant points: from tricks alone, and the total after the kitty multiplier.

|  | random | greedy |
|---|---|---|
| trick points mean | 164.8 | 136.5 |
| trick points p5 | 80.0 | 50.0 |
| trick points p25 | 130.0 | 100.0 |
| trick points p50 | 165.0 | 135.0 |
| trick points p75 | 200.0 | 175.0 |
| trick points p95 | 245.0 | 220.0 |
| total mean | 182.7 | 136.6 |
| total p5 | 85.0 | 50.0 |
| total p25 | 140.0 | 100.0 |
| total p50 | 185.0 | 135.0 |
| total p75 | 225.0 | 175.0 |
| total p95 | 275.0 | 220.0 |

### Kitty

Buried = face value of the kitty the landlord buried. Won = what the peasants get from it (buried x multiplier, 0 if the landlord team takes the last trick). x2 / x4 = the peasants took the last trick with a single / a pair or bigger.

|  | random | greedy |
|---|---|---|
| buried points mean | 14.7 | 0.1 |
| won by peasants mean | 17.9 | 0.1 |
| x2 fires | 55.5% | 47.3% |
| x4 fires | 2.3% | 1.3% |

### Result

Score-table rows by peasant total; `gain` is the base levels before any solo bonus.

|  | random | greedy |
|---|---|---|
| 0+ pts: landlord win, gain 3 | 0.0% | 0.4% |
| 5+ pts: landlord win, gain 2 | 1.1% | 6.2% |
| 60+ pts: landlord win, gain 1 | 12.8% | 29.5% |
| 120+ pts: peasants win, gain 0 | 32.2% | 40.8% |
| 180+ pts: peasants win, gain 1 | 36.2% | 20.8% |
| 240+ pts: peasants win, gain 2 | 15.9% | 2.2% |
| 300+ pts: peasants win, gain 3 | 1.8% | 0.0% |
| **landlord team wins** | 13.9% | 36.2% |

### Friends

Reveal = the trick number in which the slot's card was played (wasted slots, where the landlord played the card, are left out). Solo rounds have no slots and are left out of everything except the mode table and team sizes.

|  | random | greedy |
|---|---|---|
| slot 1 reveal mean / median | 7.2 / 6.0 | 1.6 / 1.0 |
| slot 2 reveal mean / median | 9.4 / 9.0 | 3.1 / 3.0 |
| all slots reveal mean | 8.3 | 2.4 |
| all slots reveal p5 | 1.0 | 1.0 |
| all slots reveal p25 | 4.0 | 1.0 |
| all slots reveal p50 | 7.0 | 2.0 |
| all slots reveal p75 | 12.0 | 3.0 |
| all slots reveal p95 | 18.0 | 6.0 |

|  | random | greedy |
|---|---|---|
| slot 1 never filled | 0.0% | 0.0% |
| slot 2 never filled | 0.1% | 0.0% |
| any slot never filled (per round) | 0.1% | 0.0% |
| slots never filled (per slot) | 0.1% | 0.0% |
| any slot wasted (landlord played it) | 20.9% | 0.0% |
| slots wasted (per slot) | 11.2% | 0.0% |
| one player fills two slots | 11.0% | 18.2% |

**Team size** (landlord + distinct friends)

|  | random | greedy |
|---|---|---|
| 1 players | 4.0% | 0.0% |
| 2 players | 29.8% | 18.2% |
| 3 players | 66.2% | 81.8% |

**Call mode** (dead = every call is dead, alive = every call alive, mixed = both)

|  | random | greedy |
|---|---|---|
| dead: share of rounds | 11.7% | 47.3% |
| dead: landlord win | 14.3% | 25.5% |
| alive: share of rounds | 79.2% | 52.6% |
| alive: landlord win | 14.2% | 45.8% |
| mixed: share of rounds | 6.4% | 0.0% |
| mixed: landlord win | 14.8% | 33.3% |
| solo: share of rounds | 2.6% | 0.0% |
| solo: landlord win | 0.8% | - |

### Declaring

|  | random | greedy |
|---|---|---|
| 无主 (joker declaration) | 25.9% | 11.6% |
| contested (2+ players declared) | 41.7% | 27.3% |
| reinforced (same player, same card, more copies) | 15.3% | 14.8% |
| declarations per round | 1.63 | 1.45 |
| redealt (nobody declared) | 0.2% | 0.1% |
| redeals per round | 0.003 | 0.001 |

### Landlord after the kitty swap

Off-suit lengths of the landlord's hand after burying. This depends on each table's bury policy (RandomBot buries at random), so the greedy column is the meaningful one.

|  | random | greedy |
|---|---|---|
| P(void in at least one off suit) | 2.6% | 23.9% |
| P(<= 2 cards in at least one off suit) | 46.2% | 93.3% |
| mean shortest off-suit length | 2.56 | 1.17 |

## 8 players (19 cards each, kitty 10, 3 friends)

Rounds: random 10,000, greedy 10,000

### Tricks and points

Each hand has 19 cards, so a round has at most 19 tricks; a pair, tractor or throw lead uses several cards per trick and shortens the round. The decks hold 300 points.

|  | random | greedy |
|---|---|---|
| tricks mean | 17.54 | 14.83 |
| tricks min | 9 | 8 |
| tricks max | 19 | 19 |
| failed throws per round | 5.755 | 0.000 |
| rounds with a failed throw | 99.9% | 0.0% |

Peasant points: from tricks alone, and the total after the kitty multiplier.

|  | random | greedy |
|---|---|---|
| trick points mean | 150.1 | 109.4 |
| trick points p5 | 65.0 | 25.0 |
| trick points p25 | 115.0 | 75.0 |
| trick points p50 | 150.0 | 110.0 |
| trick points p75 | 185.0 | 145.0 |
| trick points p95 | 235.0 | 195.0 |
| total mean | 170.9 | 109.9 |
| total p5 | 70.0 | 25.0 |
| total p25 | 125.0 | 75.0 |
| total p50 | 170.0 | 110.0 |
| total p75 | 215.0 | 145.0 |
| total p95 | 270.0 | 200.0 |

### Kitty

Buried = face value of the kitty the landlord buried. Won = what the peasants get from it (buried x multiplier, 0 if the landlord team takes the last trick). x2 / x4 = the peasants took the last trick with a single / a pair or bigger.

|  | random | greedy |
|---|---|---|
| buried points mean | 18.4 | 1.2 |
| won by peasants mean | 20.8 | 0.5 |
| x2 fires | 52.5% | 38.7% |
| x4 fires | 1.9% | 1.4% |

### Result

Score-table rows by peasant total; `gain` is the base levels before any solo bonus.

|  | random | greedy |
|---|---|---|
| 0+ pts: landlord win, gain 3 | 0.0% | 1.8% |
| 5+ pts: landlord win, gain 2 | 2.8% | 14.5% |
| 60+ pts: landlord win, gain 1 | 17.5% | 40.0% |
| 120+ pts: peasants win, gain 0 | 33.8% | 33.5% |
| 180+ pts: peasants win, gain 1 | 30.8% | 9.6% |
| 240+ pts: peasants win, gain 2 | 13.4% | 0.6% |
| 300+ pts: peasants win, gain 3 | 1.7% | 0.0% |
| **landlord team wins** | 20.3% | 56.3% |

### Friends

Reveal = the trick number in which the slot's card was played (wasted slots, where the landlord played the card, are left out). Solo rounds have no slots and are left out of everything except the mode table and team sizes.

|  | random | greedy |
|---|---|---|
| slot 1 reveal mean / median | 6.2 / 6.0 | 2.0 / 2.0 |
| slot 2 reveal mean / median | 8.4 / 8.0 | 3.6 / 3.0 |
| slot 3 reveal mean / median | 9.2 / 9.0 | 5.8 / 5.0 |
| all slots reveal mean | 7.9 | 3.8 |
| all slots reveal p5 | 1.0 | 1.0 |
| all slots reveal p25 | 4.0 | 2.0 |
| all slots reveal p50 | 7.0 | 3.0 |
| all slots reveal p75 | 12.0 | 5.0 |
| all slots reveal p95 | 17.0 | 10.0 |

|  | random | greedy |
|---|---|---|
| slot 1 never filled | 0.0% | 0.0% |
| slot 2 never filled | 0.2% | 0.0% |
| slot 3 never filled | 2.7% | 0.0% |
| any slot never filled (per round) | 2.8% | 0.0% |
| slots never filled (per slot) | 1.0% | 0.0% |
| any slot wasted (landlord played it) | 24.2% | 0.2% |
| slots wasted (per slot) | 8.9% | 0.1% |
| one player fills two slots | 27.7% | 38.0% |

**Team size** (landlord + distinct friends)

|  | random | greedy |
|---|---|---|
| 1 players | 1.2% | 0.0% |
| 2 players | 6.2% | 1.8% |
| 3 players | 44.8% | 36.4% |
| 4 players | 47.7% | 61.8% |

**Call mode** (dead = every call is dead, alive = every call alive, mixed = both)

|  | random | greedy |
|---|---|---|
| dead: share of rounds | 8.9% | 94.2% |
| dead: landlord win | 22.9% | 57.3% |
| alive: share of rounds | 71.2% | 0.0% |
| alive: landlord win | 20.0% | - |
| mixed: share of rounds | 18.8% | 5.8% |
| mixed: landlord win | 21.6% | 39.3% |
| solo: share of rounds | 1.1% | 0.0% |
| solo: landlord win | 0.0% | - |

### Declaring

|  | random | greedy |
|---|---|---|
| 无主 (joker declaration) | 22.1% | 10.9% |
| contested (2+ players declared) | 35.7% | 23.6% |
| reinforced (same player, same card, more copies) | 12.4% | 10.9% |
| declarations per round | 1.52 | 1.37 |
| redealt (nobody declared) | 0.4% | 0.2% |
| redeals per round | 0.004 | 0.002 |

### Landlord after the kitty swap

Off-suit lengths of the landlord's hand after burying. This depends on each table's bury policy (RandomBot buries at random), so the greedy column is the meaningful one.

|  | random | greedy |
|---|---|---|
| P(void in at least one off suit) | 5.3% | 42.8% |
| P(<= 2 cards in at least one off suit) | 66.0% | 99.1% |
| mean shortest off-suit length | 2.08 | 0.73 |

## 9 players (17 cards each, kitty 9, 3 friends)

Rounds: random 10,000, greedy 10,000

### Tricks and points

Each hand has 17 cards, so a round has at most 17 tricks; a pair, tractor or throw lead uses several cards per trick and shortens the round. The decks hold 300 points.

|  | random | greedy |
|---|---|---|
| tricks mean | 15.84 | 13.64 |
| tricks min | 9 | 8 |
| tricks max | 17 | 17 |
| failed throws per round | 5.020 | 0.000 |
| rounds with a failed throw | 99.7% | 0.0% |

Peasant points: from tricks alone, and the total after the kitty multiplier.

|  | random | greedy |
|---|---|---|
| trick points mean | 161.5 | 120.1 |
| trick points p5 | 75.0 | 35.0 |
| trick points p25 | 125.0 | 85.0 |
| trick points p50 | 160.0 | 120.0 |
| trick points p75 | 195.0 | 155.0 |
| trick points p95 | 245.0 | 210.0 |
| total mean | 181.9 | 121.0 |
| total p5 | 80.0 | 35.0 |
| total p25 | 140.0 | 85.0 |
| total p50 | 180.0 | 120.0 |
| total p75 | 225.0 | 160.0 |
| total p95 | 280.0 | 210.0 |

### Kitty

Buried = face value of the kitty the landlord buried. Won = what the peasants get from it (buried x multiplier, 0 if the landlord team takes the last trick). x2 / x4 = the peasants took the last trick with a single / a pair or bigger.

|  | random | greedy |
|---|---|---|
| buried points mean | 16.8 | 1.5 |
| won by peasants mean | 20.4 | 0.8 |
| x2 fires | 57.0% | 45.6% |
| x4 fires | 2.1% | 1.6% |

### Result

Score-table rows by peasant total; `gain` is the base levels before any solo bonus.

|  | random | greedy |
|---|---|---|
| 0+ pts: landlord win, gain 3 | 0.0% | 1.6% |
| 5+ pts: landlord win, gain 2 | 1.7% | 10.4% |
| 60+ pts: landlord win, gain 1 | 13.5% | 35.8% |
| 120+ pts: peasants win, gain 0 | 32.0% | 37.2% |
| 180+ pts: peasants win, gain 1 | 33.5% | 13.9% |
| 240+ pts: peasants win, gain 2 | 17.1% | 1.1% |
| 300+ pts: peasants win, gain 3 | 2.2% | 0.0% |
| **landlord team wins** | 15.3% | 47.8% |

### Friends

Reveal = the trick number in which the slot's card was played (wasted slots, where the landlord played the card, are left out). Solo rounds have no slots and are left out of everything except the mode table and team sizes.

|  | random | greedy |
|---|---|---|
| slot 1 reveal mean / median | 5.7 / 5.0 | 2.0 / 2.0 |
| slot 2 reveal mean / median | 7.5 / 7.0 | 3.5 / 3.0 |
| slot 3 reveal mean / median | 8.3 / 8.0 | 5.7 / 5.0 |
| all slots reveal mean | 7.2 | 3.7 |
| all slots reveal p5 | 1.0 | 1.0 |
| all slots reveal p25 | 3.0 | 2.0 |
| all slots reveal p50 | 7.0 | 3.0 |
| all slots reveal p75 | 11.0 | 5.0 |
| all slots reveal p95 | 15.0 | 10.0 |

|  | random | greedy |
|---|---|---|
| slot 1 never filled | 0.0% | 0.0% |
| slot 2 never filled | 0.1% | 0.0% |
| slot 3 never filled | 2.4% | 0.0% |
| any slot never filled (per round) | 2.5% | 0.0% |
| slots never filled (per slot) | 0.8% | 0.0% |
| any slot wasted (landlord played it) | 22.1% | 0.1% |
| slots wasted (per slot) | 8.2% | 0.1% |
| one player fills two slots | 24.2% | 33.1% |

**Team size** (landlord + distinct friends)

|  | random | greedy |
|---|---|---|
| 1 players | 1.2% | 0.0% |
| 2 players | 5.7% | 1.1% |
| 3 players | 39.9% | 32.1% |
| 4 players | 53.2% | 66.8% |

**Call mode** (dead = every call is dead, alive = every call alive, mixed = both)

|  | random | greedy |
|---|---|---|
| dead: share of rounds | 9.3% | 95.6% |
| dead: landlord win | 16.2% | 48.3% |
| alive: share of rounds | 72.3% | 0.0% |
| alive: landlord win | 14.8% | - |
| mixed: share of rounds | 17.3% | 4.4% |
| mixed: landlord win | 17.6% | 35.7% |
| solo: share of rounds | 1.1% | 0.0% |
| solo: landlord win | 0.0% | - |

### Declaring

|  | random | greedy |
|---|---|---|
| 无主 (joker declaration) | 20.7% | 10.7% |
| contested (2+ players declared) | 35.5% | 22.0% |
| reinforced (same player, same card, more copies) | 11.8% | 9.6% |
| declarations per round | 1.51 | 1.33 |
| redealt (nobody declared) | 0.3% | 0.2% |
| redeals per round | 0.003 | 0.002 |

### Landlord after the kitty swap

Off-suit lengths of the landlord's hand after burying. This depends on each table's bury policy (RandomBot buries at random), so the greedy column is the meaningful one.

|  | random | greedy |
|---|---|---|
| P(void in at least one off suit) | 8.0% | 50.7% |
| P(<= 2 cards in at least one off suit) | 78.7% | 99.7% |
| mean shortest off-suit length | 1.77 | 0.58 |

