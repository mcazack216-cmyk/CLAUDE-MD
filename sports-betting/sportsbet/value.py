"""Fair-probability estimation, value detection and stake sizing."""

from dataclasses import dataclass
from statistics import median

# Books whose lines are efficient enough to serve as the "true" price, in priority order.
SHARP_BOOKS = ("pinnacle", "betfair_ex_eu", "betfair_ex_uk", "matchbook")


@dataclass
class ValueBet:
    sport: str
    event: str
    commence_time: str
    outcome: str
    book: str
    price: float
    fair_prob: float
    ev: float
    fair_source: str
    stake: float = 0.0


def devig(prices):
    """Convert decimal odds {outcome: price} to probabilities with the bookmaker margin removed."""
    raw = {name: 1.0 / price for name, price in prices.items()}
    total = sum(raw.values())
    return {name: p / total for name, p in raw.items()}


def expected_value(prob, price):
    """Expected profit per 1 unit staked."""
    return prob * price - 1.0


def kelly_stake(prob, price, bankroll, fraction=0.25, max_pct=0.05):
    """Fractional Kelly stake, capped at max_pct of bankroll. Returns 0 for negative-edge bets."""
    b = price - 1.0
    if b <= 0:
        return 0.0
    full_kelly = (b * prob - (1.0 - prob)) / b
    pct = min(max(full_kelly * fraction, 0.0), max_pct)
    return round(bankroll * pct, 2)


def market_prices(event, market="h2h"):
    """Return {book_key: {outcome: price}} for books that quote every outcome of the market."""
    by_book = {}
    for book in event.get("bookmakers", []):
        for m in book.get("markets", []):
            if m.get("key") == market:
                by_book[book["key"]] = {o["name"]: float(o["price"]) for o in m["outcomes"]}
    if not by_book:
        return {}
    outcomes = set().union(*(set(p) for p in by_book.values()))
    return {k: p for k, p in by_book.items() if set(p) == outcomes and all(v > 1.0 for v in p.values())}


def fair_probabilities(prices_by_book, min_books=3):
    """Estimate true outcome probabilities.

    Uses the first available sharp book; otherwise the median de-vigged probability across
    at least `min_books` books. Returns (probabilities, source) or (None, None).
    """
    for sharp in SHARP_BOOKS:
        if sharp in prices_by_book:
            return devig(prices_by_book[sharp]), sharp
    if len(prices_by_book) < min_books:
        return None, None
    devigged = [devig(p) for p in prices_by_book.values()]
    outcomes = devigged[0].keys()
    med = {o: median(d[o] for d in devigged) for o in outcomes}
    total = sum(med.values())
    return {o: p / total for o, p in med.items()}, "consensus"


def find_value_bets(events, min_ev=0.03, min_books=3, max_price=10.0):
    """Return the best-priced value bet per outcome for each event, sorted by EV descending.

    max_price filters out long shots, where small errors in the fair probability swamp the edge.
    """
    bets = []
    for event in events:
        prices = market_prices(event)
        fair, source = fair_probabilities(prices, min_books)
        if fair is None:
            continue
        name = f"{event.get('away_team')} @ {event.get('home_team')}"
        for outcome, prob in fair.items():
            book, price = max(
                ((b, p[outcome]) for b, p in prices.items() if b != source),
                key=lambda bp: bp[1],
                default=(None, 0.0),
            )
            if book is None or price > max_price:
                continue
            ev = expected_value(prob, price)
            if ev >= min_ev:
                bets.append(ValueBet(
                    sport=event.get("sport_title") or event.get("sport_key", ""),
                    event=name,
                    commence_time=event.get("commence_time", ""),
                    outcome=outcome,
                    book=book,
                    price=price,
                    fair_prob=prob,
                    ev=ev,
                    fair_source=source,
                ))
    return sorted(bets, key=lambda b: b.ev, reverse=True)
