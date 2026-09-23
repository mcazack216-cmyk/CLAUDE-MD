"""Command-line interface: scan for value bets, list sports, settle and summarize logged bets."""

import argparse
import json
import os
import sys

from sportsbet import odds_api, tracker
from sportsbet.value import find_value_bets, kelly_stake

DEFAULT_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bets.csv")


def _api_key(args):
    key = args.api_key or os.environ.get("ODDS_API_KEY")
    if not key:
        sys.exit("No API key. Set ODDS_API_KEY or pass --api-key (free key: https://the-odds-api.com).")
    return key


def _load_events(args):
    if args.sample:
        with open(args.sample) as f:
            return json.load(f)
    key = _api_key(args)
    if args.sports == "all":
        sport_keys = [s["key"] for s in odds_api.list_sports(key)]
    else:
        sport_keys = [s.strip() for s in args.sports.split(",") if s.strip()]
    if args.max_sports:
        sport_keys = sport_keys[: args.max_sports]
    events, remaining = [], None
    for sport in sport_keys:
        try:
            data, remaining = odds_api.get_odds(key, sport, regions=args.regions)
        except odds_api.OddsAPIError as e:
            print(f"skip {sport}: {e}", file=sys.stderr)
            continue
        events.extend(data)
    print(f"Scanned {len(sport_keys)} sports, {len(events)} events. "
          f"API requests remaining: {remaining}", file=sys.stderr)
    return events


def cmd_scan(args):
    events = _load_events(args)
    bets = find_value_bets(events, min_ev=args.min_ev, min_books=args.min_books, max_price=args.max_price)
    for b in bets:
        b.stake = kelly_stake(b.fair_prob, b.price, args.bankroll, args.kelly, args.max_stake_pct)
    bets = [b for b in bets if b.stake > 0]
    if not bets:
        print("No value bets found at these thresholds.")
        return 0
    print(f"{'EV':>6}  {'Price':>6}  {'Fair%':>6}  {'Stake':>7}  {'Book':<14} {'Pick':<24} Event (sport, start)")
    for b in bets:
        print(f"{b.ev:>6.1%}  {b.price:>6.2f}  {b.fair_prob:>6.1%}  {b.stake:>7.2f}  "
              f"{b.book:<14} {b.outcome:<24} {b.event} ({b.sport}, {b.commence_time}) [fair: {b.fair_source}]")
    if args.log:
        added = tracker.log_bets(args.log_file, bets)
        print(f"\nLogged {len(added)} new bet(s) to {args.log_file}")
    return 0


def cmd_sports(args):
    for s in odds_api.list_sports(_api_key(args)):
        print(f"{s['key']:<40} {s['title']}")
    return 0


def cmd_settle(args):
    row = tracker.settle(args.log_file, args.id, args.result)
    print(f"Bet {row['id']} ({row['outcome']} @ {row['price']}): {row['result']}, P&L {row['pnl']}")
    return 0


def cmd_summary(args):
    for k, v in tracker.summary(args.log_file).items():
        print(f"{k:>13}: {v}")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="sportsbet", description=__doc__)
    p.add_argument("--api-key", help="The Odds API key (default: $ODDS_API_KEY)")
    p.add_argument("--log-file", default=DEFAULT_LOG, help="bet log CSV (default: %(default)s)")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="find value bets")
    s.add_argument("--sports", default="all", help='"all" in-season sports, or comma-separated sport keys')
    s.add_argument("--max-sports", type=int, default=0, help="cap sports scanned to save API quota (0 = no cap)")
    s.add_argument("--regions", default="us,eu", help="bookmaker regions: us, us2, uk, eu, au (default: %(default)s)")
    s.add_argument("--min-ev", type=float, default=0.03, help="minimum expected value per unit (default: %(default)s)")
    s.add_argument("--min-books", type=int, default=3, help="books needed for a consensus price (default: %(default)s)")
    s.add_argument("--max-price", type=float, default=10.0, help="ignore odds above this (default: %(default)s)")
    s.add_argument("--bankroll", type=float, default=100.0, help="bankroll for stake sizing (default: %(default)s)")
    s.add_argument("--kelly", type=float, default=0.25, help="Kelly fraction (default: %(default)s)")
    s.add_argument("--max-stake-pct", type=float, default=0.05, help="max stake as share of bankroll (default: %(default)s)")
    s.add_argument("--sample", help="read events from a JSON file instead of the API")
    s.add_argument("--log", action="store_true", help="record suggestions in the bet log")
    s.set_defaults(func=cmd_scan)

    s = sub.add_parser("sports", help="list in-season sports")
    s.set_defaults(func=cmd_sports)

    s = sub.add_parser("settle", help="record a bet result")
    s.add_argument("id", type=int)
    s.add_argument("result", choices=["win", "loss", "push"])
    s.set_defaults(func=cmd_settle)

    s = sub.add_parser("summary", help="show performance of logged bets")
    s.set_defaults(func=cmd_summary)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)
