# sportsbet — value-bet finder for all sports

Scans every in-season sport on [The Odds API](https://the-odds-api.com), estimates the
fair probability of each outcome, and flags sportsbooks paying more than it's worth.
It **suggests** bets; you place them yourself. Sportsbooks generally ban bots.

## How it works

1. **Fair price.** For each game, the de-vigged odds of a sharp book (Pinnacle,
   Betfair Exchange, Matchbook) are treated as the true probability. If no sharp
   book is quoting, the median de-vigged probability across at least 3 books is used.
2. **Value.** For each outcome, the best price at any other book is compared with
   the fair probability: `EV = fair_prob × price − 1`. Bets at or above `--min-ev`
   (default 3%) are listed.
3. **Stake.** Quarter-Kelly on your bankroll, capped at 5% per bet.
4. **Tracking.** `--log` records suggestions to `bets.csv`, which you then `settle`
   for win, loss or push, and `summary` compares real profit with the model's
   expected profit.

Uses only the head-to-head (moneyline) market and Python's standard library. No
dependencies to install.

## Setup

Get a free API key at https://the-odds-api.com. The free tier gives 500 requests a
month. Each sport scanned costs one request per region (`us,eu` = 2 per sport), so
a full all-sports scan can use 100+ requests. Use `--max-sports` or `--sports` to
save quota.

```sh
export ODDS_API_KEY=your_key
cd sports-betting
```

## Usage

```sh
python3 -m sportsbet scan --sample sample_odds.json     # try it offline
python3 -m sportsbet sports                              # list in-season sports
python3 -m sportsbet scan --bankroll 200 --log           # scan all sports, log picks
python3 -m sportsbet scan --sports basketball_nba,soccer_epl --min-ev 0.05
python3 -m sportsbet settle 3 win                        # record a result
python3 -m sportsbet summary                             # performance so far
```

Key options for `scan`: `--regions` (us, us2, uk, eu, au), `--min-ev`,
`--bankroll`, `--kelly`, `--max-stake-pct`, `--max-price` (skip long shots),
`--max-sports`.

## Tests

```sh
python3 -m unittest discover -v
```

## Caveats

- An edge against a soft book's line is real, but small, and it takes hundreds of
  bets before results beat the noise. Judge the model by `summary` over time,
  not by one week.
- Odds move. Check the price is still there before you bet.
- Books limit or ban accounts that consistently win this way.
- Sports betting is only legal in some places. Check yours.
