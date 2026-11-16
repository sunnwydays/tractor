# Deal statistics

Trump context: trump rank 3, trump suit ♥

- Deals per player count: 100,000
- Seed: 1 (each player count uses seed + number of players)
- Regenerate: `python -m stats.report --deals 100000 --seed 1 --trump-rank 3 --trump-suit H --players 7 8 9 --out reports/deal_stats.md`

## How to read this

- Seat 0 is "the player"; everything is at the deal, before the kitty swap, unless stated.
- Pair = a card type held 2+ times (a triple counts as a pair); triple = held 3+ times. A tractor of width w is a maximal run of 2+ consecutive levels each holding a w-set (w=2 pairs, w=3 triples); cards equal in rank share a level.
- Trump is fixed in advance, so this is a random player's hand, not a declarer who picked trump because they were long in it.
- sim = Monte Carlo through the engine; exact = combinatorics.

## Agreement

- Checks: 382
- Max |z|: 2.75
- All within 4 standard errors.

## 7 players (22 cards each, kitty 8, 2 friends)

### Pairs, triples and tractors

**Pairs**

| Suit | P(≥1) sim | P(≥1) exact | E[count] sim | E[count] exact |
|---|---|---|---|---|
| ♠ (33 cards) | 43.68% | 43.51% | 0.5378 | 0.5358 |
| ♣ (33 cards) | 43.60% | 43.51% | 0.5369 | 0.5358 |
| ♦ (33 cards) | 43.51% | 43.51% | 0.5366 | 0.5358 |
| trump (63 cards) | 67.79% | 67.95% | 1.0226 | 1.0229 |

**Triples**

| Suit | P(≥1) sim | P(≥1) exact | E[count] sim | E[count] exact |
|---|---|---|---|---|
| ♠ (33 cards) | 2.40% | 2.42% | 0.0241 | 0.0244 |
| ♣ (33 cards) | 2.43% | 2.42% | 0.0245 | 0.0244 |
| ♦ (33 cards) | 2.37% | 2.42% | 0.0239 | 0.0244 |
| trump (63 cards) | 4.67% | 4.58% | 0.0473 | 0.0465 |

**Tractors of pairs**

| Suit | P(≥1) sim | P(≥1) exact | E[count] sim | E[count] exact |
|---|---|---|---|---|
| ♠ (33 cards) | 1.92% | 1.96% | 0.0193 | 0.0197 |
| ♣ (33 cards) | 1.97% | 1.96% | 0.0198 | 0.0197 |
| ♦ (33 cards) | 2.00% | 1.96% | 0.0200 | 0.0197 |
| trump (63 cards) | 4.49% | 4.54% | 0.0452 | 0.0458 |

**Tractors of triples**

| Suit | P(≥1) sim | P(≥1) exact | E[count] sim | E[count] exact |
|---|---|---|---|---|
| ♠ (33 cards) | 0.0050% | 0.0033% | 0.000050 | 0.000033 |
| ♣ (33 cards) | 0.0040% | 0.0033% | 0.000040 | 0.000033 |
| ♦ (33 cards) | 0.0030% | 0.0033% | 0.000030 | 0.000033 |
| trump (63 cards) | 0.0080% | 0.0078% | 0.000080 | 0.000078 |

### Jokers

| Hand has | sim | exact |
|---|---|---|
| big-joker pair | 4.87% | 4.87% |
| small-joker pair | 4.90% | 4.87% |
| any joker pair (declare 无主) | 9.57% | 9.54% |
| joker triple (3 identical jokers) | 0.44% | 0.44% |

### Void and short suits

| Suit | P(void) sim | P(void) exact | P(≤2 cards) sim | P(≤2 cards) exact |
|---|---|---|---|---|
| ♠ (33 cards) | 0.42% | 0.44% | 12.63% | 12.63% |
| ♣ (33 cards) | 0.44% | 0.44% | 12.58% | 12.63% |
| ♦ (33 cards) | 0.40% | 0.44% | 12.58% | 12.63% |
| trump (63 cards) | 0.0010% | 0.0007% | 0.14% | 0.12% |

**Length distribution** (cells: sim / exact; lengths below 0.1% omitted)

| length | ♠ | ♣ | ♦ | trump |
|---|---|---|---|---|
| 0 | 0.42% / 0.44% | 0.44% / 0.44% | 0.40% / 0.44% | - |
| 1 | 3.05% / 2.98% | 3.02% / 2.98% | 2.99% / 2.98% | - |
| 2 | 9.16% / 9.20% | 9.11% / 9.20% | 9.18% / 9.20% | 0.13% / 0.10% |
| 3 | 17.34% / 17.29% | 17.47% / 17.29% | 17.32% / 17.29% | 0.50% / 0.52% |
| 4 | 22.29% / 22.19% | 22.07% / 22.19% | 22.22% / 22.19% | 1.87% / 1.84% |
| 5 | 20.46% / 20.69% | 20.66% / 20.69% | 20.69% / 20.69% | 4.69% / 4.77% |
| 6 | 14.53% / 14.52% | 14.62% / 14.52% | 14.58% / 14.52% | 9.43% / 9.45% |
| 7 | 7.82% / 7.86% | 7.76% / 7.86% | 7.86% / 7.86% | 14.63% / 14.66% |
| 8 | 3.38% / 3.33% | 3.33% / 3.33% | 3.30% / 3.33% | 18.31% / 18.11% |
| 9 | 1.19% / 1.12% | 1.14% / 1.12% | 1.10% / 1.12% | 18.07% / 18.02% |
| 10 | 0.30% / 0.30% | 0.31% / 0.30% | 0.27% / 0.30% | 14.39% / 14.54% |
| 11 | - | - | - | 9.48% / 9.55% |
| 12 | - | - | - | 5.12% / 5.12% |
| 13 | - | - | - | 2.28% / 2.23% |
| 14 | - | - | - | 0.78% / 0.79% |
| 15 | - | - | - | 0.26% / 0.22% |

### Trump length

Mean trump cards in hand: sim 8.557, exact 8.556 (63 trump cards).

| k | P(≥k) sim | P(≥k) exact |
|---|---|---|
| 3 | 99.86% | 99.88% |
| 4 | 99.36% | 99.36% |
| 5 | 97.49% | 97.52% |
| 6 | 92.80% | 92.74% |
| 7 | 83.37% | 83.29% |
| 8 | 68.74% | 68.63% |
| 9 | 50.43% | 50.52% |
| 10 | 32.36% | 32.51% |
| 11 | 17.97% | 17.97% |
| 12 | 8.48% | 8.42% |
| 13 | 3.37% | 3.30% |
| 14 | 1.09% | 1.07% |
| 15 | 0.31% | 0.28% |

### Kitty points

The kitty as dealt, before the landlord buries.

Mean kitty points: sim 14.836, exact 14.815.

| percentile | sim | exact |
|---|---|---|
| 10% | 0 | 0 |
| 25% | 10 | 10 |
| 50% | 15 | 15 |
| 75% | 20 | 20 |
| 90% | 30 | 30 |
| 95% | 30 | 30 |
| 99% | 40 | 40 |

| points | sim | exact |
|---|---|---|
| 0 | 12.91% | 12.72% |
| 5 | 10.08% | 10.26% |
| 10 | 23.71% | 23.82% |
| 15 | 14.87% | 14.91% |
| 20 | 17.70% | 17.74% |
| 25 | 8.80% | 8.73% |
| 30 | 6.97% | 6.89% |
| 35 | 2.71% | 2.66% |
| 40 | 1.54% | 1.53% |
| 45 | 0.46% | 0.46% |
| 50 | 0.19% | 0.20% |

### Friend calls

Call card: A♠ (every non-trump card is symmetric). Seat 0 is the landlord.
With 3 copies, if the landlord holds c there are 3 - c out there. A dead call for (3 - c) friends on that card is possible only when the landlord holds exactly c; otherwise the call is alive.

**A. Copies the landlord holds**

| copies landlord holds | at the deal sim | at the deal exact | after picking up the kitty sim | after picking up the kitty exact |
|---|---|---|---|---|
| 0 | 64.27% | 64.35% | 53.70% | 53.87% |
| 1 | 30.73% | 30.78% | 37.37% | 37.29% |
| 2 | 4.78% | 4.65% | 8.33% | 8.26% |
| 3 | 0.23% | 0.22% | 0.60% | 0.58% |

**B. Where the remaining copies are** (assumes the landlord does not bury copies of the called card)

| landlord holds | spread | sim | exact |
|---|---|---|---|
| 0 | one player holds all 3 | 2.42% | 2.47% |
| 0 | one player holds 2, another holds 1 | 40.72% | 40.69% |
| 0 | 3 players hold 1 each | 56.86% | 56.84% |
| 1 | one player holds all 2 | 16.27% | 16.03% |
| 1 | 2 players hold 1 each | 83.73% | 83.97% |
| 2 | 1 player holds it | 100.00% | 100.00% |

## 8 players (19 cards each, kitty 10, 3 friends)

### Pairs, triples and tractors

**Pairs**

| Suit | P(≥1) sim | P(≥1) exact | E[count] sim | E[count] exact |
|---|---|---|---|---|
| ♠ (33 cards) | 34.65% | 34.55% | 0.4011 | 0.4021 |
| ♣ (33 cards) | 34.58% | 34.55% | 0.4013 | 0.4021 |
| ♦ (33 cards) | 34.59% | 34.55% | 0.4031 | 0.4021 |
| trump (63 cards) | 56.72% | 56.81% | 0.7674 | 0.7676 |

**Triples**

| Suit | P(≥1) sim | P(≥1) exact | E[count] sim | E[count] exact |
|---|---|---|---|---|
| ♠ (33 cards) | 1.49% | 1.53% | 0.0149 | 0.0153 |
| ♣ (33 cards) | 1.49% | 1.53% | 0.0149 | 0.0153 |
| ♦ (33 cards) | 1.51% | 1.53% | 0.0151 | 0.0153 |
| trump (63 cards) | 2.77% | 2.90% | 0.0280 | 0.0293 |

**Tractors of pairs**

| Suit | P(≥1) sim | P(≥1) exact | E[count] sim | E[count] exact |
|---|---|---|---|---|
| ♠ (33 cards) | 1.08% | 1.08% | 0.0108 | 0.0108 |
| ♣ (33 cards) | 1.04% | 1.08% | 0.0104 | 0.0108 |
| ♦ (33 cards) | 1.09% | 1.08% | 0.0109 | 0.0108 |
| trump (63 cards) | 2.55% | 2.53% | 0.0257 | 0.0254 |

**Tractors of triples**

| Suit | P(≥1) sim | P(≥1) exact | E[count] sim | E[count] exact |
|---|---|---|---|---|
| ♠ (33 cards) | 0.0020% | 0.0012% | 0.000020 | 0.000012 |
| ♣ (33 cards) | 0.0000% | 0.0012% | 0.000000 | 0.000012 |
| ♦ (33 cards) | 0.0010% | 0.0012% | 0.000010 | 0.000012 |
| trump (63 cards) | 0.0020% | 0.0028% | 0.000020 | 0.000028 |

### Jokers

| Hand has | sim | exact |
|---|---|---|
| big-joker pair | 3.59% | 3.66% |
| small-joker pair | 3.62% | 3.66% |
| any joker pair (declare 无主) | 7.10% | 7.20% |
| joker triple (3 identical jokers) | 0.27% | 0.28% |

### Void and short suits

| Suit | P(void) sim | P(void) exact | P(≤2 cards) sim | P(≤2 cards) exact |
|---|---|---|---|---|
| ♠ (33 cards) | 1.00% | 0.98% | 20.71% | 20.79% |
| ♣ (33 cards) | 0.97% | 0.98% | 20.71% | 20.79% |
| ♦ (33 cards) | 0.96% | 0.98% | 20.81% | 20.79% |
| trump (63 cards) | 0.0040% | 0.0041% | 0.49% | 0.48% |

**Length distribution** (cells: sim / exact; lengths below 0.1% omitted)

| length | ♠ | ♣ | ♦ | trump |
|---|---|---|---|---|
| 0 | 1.00% / 0.98% | 0.97% / 0.98% | 0.96% / 0.98% | - |
| 1 | 5.51% / 5.55% | 5.45% / 5.55% | 5.62% / 5.55% | - |
| 2 | 14.20% / 14.26% | 14.29% / 14.26% | 14.23% / 14.26% | 0.42% / 0.41% |
| 3 | 22.10% / 22.17% | 22.09% / 22.17% | 22.09% / 22.17% | 1.71% / 1.71% |
| 4 | 23.52% / 23.33% | 23.43% / 23.33% | 23.35% / 23.33% | 4.87% / 4.89% |
| 5 | 17.83% / 17.65% | 17.72% / 17.65% | 17.70% / 17.65% | 10.22% / 10.18% |
| 6 | 9.88% / 9.94% | 9.95% / 9.94% | 9.98% / 9.94% | 16.01% / 16.03% |
| 7 | 4.14% / 4.26% | 4.33% / 4.26% | 4.20% / 4.26% | 19.47% / 19.50% |
| 8 | 1.38% / 1.41% | 1.32% / 1.41% | 1.43% / 1.41% | 18.62% / 18.61% |
| 9 | 0.36% / 0.36% | 0.37% / 0.36% | 0.34% / 0.36% | 14.10% / 14.06% |
| 10 | - | - | - | 8.41% / 8.44% |
| 11 | - | - | - | 4.03% / 4.02% |
| 12 | - | - | - | 1.47% / 1.51% |
| 13 | - | - | - | 0.48% / 0.45% |
| 14 | - | - | - | 0.11% / 0.10% |

### Trump length

Mean trump cards in hand: sim 7.389, exact 7.389 (63 trump cards).

| k | P(≥k) sim | P(≥k) exact |
|---|---|---|
| 3 | 99.51% | 99.52% |
| 4 | 97.80% | 97.81% |
| 5 | 92.94% | 92.92% |
| 6 | 82.71% | 82.74% |
| 7 | 66.70% | 66.71% |
| 8 | 47.23% | 47.21% |
| 9 | 28.61% | 28.60% |
| 10 | 14.51% | 14.54% |
| 11 | 6.10% | 6.10% |
| 12 | 2.07% | 2.08% |
| 13 | 0.60% | 0.57% |
| 14 | 0.12% | 0.12% |

### Kitty points

The kitty as dealt, before the landlord buries.

Mean kitty points: sim 18.528, exact 18.519.

| percentile | sim | exact |
|---|---|---|
| 10% | 5 | 5 |
| 25% | 10 | 10 |
| 50% | 20 | 20 |
| 75% | 25 | 25 |
| 90% | 35 | 35 |
| 95% | 40 | 40 |
| 99% | 50 | 50 |

| points | sim | exact |
|---|---|---|
| 0 | 7.42% | 7.46% |
| 5 | 7.59% | 7.65% |
| 10 | 18.43% | 18.50% |
| 15 | 14.87% | 14.72% |
| 20 | 18.69% | 18.68% |
| 25 | 11.92% | 11.83% |
| 30 | 10.12% | 10.20% |
| 35 | 5.22% | 5.21% |
| 40 | 3.31% | 3.34% |
| 45 | 1.34% | 1.38% |
| 50 | 0.69% | 0.69% |
| 55 | 0.24% | 0.23% |
| 60 | 0.10% | 0.0891% |

### Friend calls

Call card: A♠ (every non-trump card is symmetric). Seat 0 is the landlord.
With 3 copies, if the landlord holds c there are 3 - c out there. A dead call for (3 - c) friends on that card is possible only when the landlord holds exactly c; otherwise the call is alive.

**A. Copies the landlord holds**

| copies landlord holds | at the deal sim | at the deal exact | after picking up the kitty sim | after picking up the kitty exact |
|---|---|---|---|---|
| 0 | 68.77% | 68.61% | 54.98% | 55.11% |
| 1 | 27.62% | 27.74% | 36.81% | 36.60% |
| 2 | 3.50% | 3.52% | 7.72% | 7.76% |
| 3 | 0.12% | 0.14% | 0.49% | 0.53% |

**B. Where the remaining copies are** (assumes the landlord does not bury copies of the called card)

| landlord holds | spread | sim | exact |
|---|---|---|---|
| 0 | one player holds all 3 | 1.81% | 1.77% |
| 0 | one player holds 2, another holds 1 | 35.28% | 35.60% |
| 0 | 3 players hold 1 each | 62.91% | 62.63% |
| 1 | one player holds all 2 | 13.66% | 13.64% |
| 1 | 2 players hold 1 each | 86.34% | 86.36% |
| 2 | 1 player holds it | 100.00% | 100.00% |

## 9 players (17 cards each, kitty 9, 3 friends)

### Pairs, triples and tractors

**Pairs**

| Suit | P(≥1) sim | P(≥1) exact | E[count] sim | E[count] exact |
|---|---|---|---|---|
| ♠ (33 cards) | 28.60% | 28.66% | 0.3216 | 0.3226 |
| ♣ (33 cards) | 28.93% | 28.66% | 0.3267 | 0.3226 |
| ♦ (33 cards) | 28.81% | 28.66% | 0.3245 | 0.3226 |
| trump (63 cards) | 48.60% | 48.65% | 0.6153 | 0.6159 |

**Triples**

| Suit | P(≥1) sim | P(≥1) exact | E[count] sim | E[count] exact |
|---|---|---|---|---|
| ♠ (33 cards) | 1.04% | 1.07% | 0.0104 | 0.0108 |
| ♣ (33 cards) | 1.07% | 1.07% | 0.0107 | 0.0108 |
| ♦ (33 cards) | 1.09% | 1.07% | 0.0109 | 0.0108 |
| trump (63 cards) | 2.02% | 2.04% | 0.0203 | 0.0205 |

**Tractors of pairs**

| Suit | P(≥1) sim | P(≥1) exact | E[count] sim | E[count] exact |
|---|---|---|---|---|
| ♠ (33 cards) | 0.64% | 0.68% | 0.0064 | 0.0068 |
| ♣ (33 cards) | 0.70% | 0.68% | 0.0070 | 0.0068 |
| ♦ (33 cards) | 0.68% | 0.68% | 0.0068 | 0.0068 |
| trump (63 cards) | 1.64% | 1.60% | 0.0164 | 0.0161 |

**Tractors of triples**

| Suit | P(≥1) sim | P(≥1) exact | E[count] sim | E[count] exact |
|---|---|---|---|---|
| ♠ (33 cards) | 0.0000% | 0.0005% | 0.000000 | 0.000005 |
| ♣ (33 cards) | 0.0000% | 0.0005% | 0.000000 | 0.000005 |
| ♦ (33 cards) | 0.0000% | 0.0005% | 0.000000 | 0.000005 |
| trump (63 cards) | 0.0010% | 0.0013% | 0.000010 | 0.000013 |

### Jokers

| Hand has | sim | exact |
|---|---|---|
| big-joker pair | 2.99% | 2.93% |
| small-joker pair | 2.82% | 2.93% |
| any joker pair (declare 无主) | 5.75% | 5.80% |
| joker triple (3 identical jokers) | 0.21% | 0.20% |

### Void and short suits

| Suit | P(void) sim | P(void) exact | P(≤2 cards) sim | P(≤2 cards) exact |
|---|---|---|---|---|
| ♠ (33 cards) | 1.66% | 1.65% | 28.27% | 28.22% |
| ♣ (33 cards) | 1.67% | 1.65% | 27.91% | 28.22% |
| ♦ (33 cards) | 1.67% | 1.65% | 28.12% | 28.22% |
| trump (63 cards) | 0.0170% | 0.0128% | 1.21% | 1.16% |

**Length distribution** (cells: sim / exact; lengths below 0.1% omitted)

| length | ♠ | ♣ | ♦ | trump |
|---|---|---|---|---|
| 0 | 1.66% / 1.65% | 1.67% / 1.65% | 1.67% / 1.65% | - |
| 1 | 8.25% / 8.19% | 8.12% / 8.19% | 8.06% / 8.19% | 0.17% / 0.17% |
| 2 | 18.36% / 18.38% | 18.12% / 18.38% | 18.39% / 18.38% | 1.03% / 0.98% |
| 3 | 24.73% / 24.78% | 24.72% / 24.78% | 24.94% / 24.78% | 3.50% / 3.51% |
| 4 | 22.48% / 22.43% | 22.79% / 22.43% | 22.33% / 22.43% | 8.55% / 8.58% |
| 5 | 14.35% / 14.45% | 14.43% / 14.45% | 14.46% / 14.45% | 15.29% / 15.12% |
| 6 | 6.92% / 6.86% | 6.83% / 6.86% | 6.92% / 6.86% | 19.98% / 19.94% |
| 7 | 2.46% / 2.45% | 2.54% / 2.45% | 2.45% / 2.45% | 19.78% / 20.07% |
| 8 | 0.64% / 0.66% | 0.64% / 0.66% | 0.62% / 0.66% | 15.67% / 15.61% |
| 9 | 0.13% / 0.14% | 0.12% / 0.14% | 0.13% / 0.14% | 9.56% / 9.43% |
| 10 | - | - | - | 4.31% / 4.43% |
| 11 | - | - | - | 1.62% / 1.61% |
| 12 | - | - | - | 0.43% / 0.44% |

### Trump length

Mean trump cards in hand: sim 6.604, exact 6.611 (63 trump cards).

| k | P(≥k) sim | P(≥k) exact |
|---|---|---|
| 2 | 99.81% | 99.82% |
| 3 | 98.78% | 98.84% |
| 4 | 95.28% | 95.33% |
| 5 | 86.73% | 86.75% |
| 6 | 71.44% | 71.63% |
| 7 | 51.46% | 51.69% |
| 8 | 31.68% | 31.62% |
| 9 | 16.01% | 16.02% |
| 10 | 6.46% | 6.59% |
| 11 | 2.15% | 2.16% |
| 12 | 0.53% | 0.55% |
| 13 | 0.0970% | 0.11% |

### Kitty points

The kitty as dealt, before the landlord buries.

Mean kitty points: sim 16.632, exact 16.667.

| percentile | sim | exact |
|---|---|---|
| 10% | 5 | 5 |
| 25% | 10 | 10 |
| 50% | 15 | 15 |
| 75% | 25 | 25 |
| 90% | 30 | 30 |
| 95% | 35 | 35 |
| 99% | 45 | 45 |

| points | sim | exact |
|---|---|---|
| 0 | 9.76% | 9.75% |
| 5 | 8.90% | 8.92% |
| 10 | 21.27% | 21.15% |
| 15 | 15.02% | 15.04% |
| 20 | 18.56% | 18.49% |
| 25 | 10.44% | 10.43% |
| 30 | 8.46% | 8.61% |
| 35 | 3.93% | 3.88% |
| 40 | 2.30% | 2.35% |
| 45 | 0.83% | 0.84% |
| 50 | 0.37% | 0.39% |
| 55 | 0.10% | 0.11% |

### Friend calls

Call card: A♠ (every non-trump card is symmetric). Seat 0 is the landlord.
With 3 copies, if the landlord holds c there are 3 - c out there. A dead call for (3 - c) friends on that card is possible only when the landlord holds exactly c; otherwise the call is alive.

**A. Copies the landlord holds**

| copies landlord holds | at the deal sim | at the deal exact | after picking up the kitty sim | after picking up the kitty exact |
|---|---|---|---|---|
| 0 | 71.59% | 71.55% | 58.95% | 58.95% |
| 1 | 25.48% | 25.52% | 34.23% | 34.32% |
| 2 | 2.83% | 2.84% | 6.44% | 6.35% |
| 3 | 0.11% | 0.0978% | 0.37% | 0.37% |

**B. Where the remaining copies are** (assumes the landlord does not bury copies of the called card)

| landlord holds | spread | sim | exact |
|---|---|---|---|
| 0 | one player holds all 3 | 1.27% | 1.33% |
| 0 | one player holds 2, another holds 1 | 31.41% | 31.58% |
| 0 | 3 players hold 1 each | 67.32% | 67.10% |
| 1 | one player holds all 2 | 11.79% | 11.85% |
| 1 | 2 players hold 1 each | 88.21% | 88.15% |
| 2 | 1 player holds it | 100.00% | 100.00% |

