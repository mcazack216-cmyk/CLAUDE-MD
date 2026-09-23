"""CSV log of suggested bets, settlement, and performance summary."""

import csv
import os
from datetime import datetime, timezone

FIELDS = [
    "id", "logged_at", "sport", "event", "commence_time", "outcome", "book",
    "price", "fair_prob", "ev", "stake", "result", "pnl",
]


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _write(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def log_bets(path, bets):
    """Append bets to the log, skipping ones already logged (same event, outcome and book)."""
    rows = _read(path)
    seen = {(r["event"], r["commence_time"], r["outcome"], r["book"]) for r in rows}
    next_id = max((int(r["id"]) for r in rows), default=0) + 1
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    added = []
    for b in bets:
        key = (b.event, b.commence_time, b.outcome, b.book)
        if key in seen:
            continue
        row = {
            "id": next_id, "logged_at": now, "sport": b.sport, "event": b.event,
            "commence_time": b.commence_time, "outcome": b.outcome, "book": b.book,
            "price": f"{b.price:.3f}", "fair_prob": f"{b.fair_prob:.4f}", "ev": f"{b.ev:.4f}",
            "stake": f"{b.stake:.2f}", "result": "", "pnl": "",
        }
        rows.append(row)
        added.append(row)
        seen.add(key)
        next_id += 1
    _write(path, rows)
    return added


def settle(path, bet_id, result):
    """Record a result: win, loss, or push (stake returned)."""
    if result not in ("win", "loss", "push"):
        raise ValueError("result must be win, loss or push")
    rows = _read(path)
    for r in rows:
        if r["id"] == str(bet_id):
            stake, price = float(r["stake"]), float(r["price"])
            pnl = {"win": stake * (price - 1), "loss": -stake, "push": 0.0}[result]
            r["result"], r["pnl"] = result, f"{pnl:.2f}"
            _write(path, rows)
            return r
    raise KeyError(f"no bet with id {bet_id}")


def summary(path):
    rows = _read(path)
    settled = [r for r in rows if r["result"]]
    staked = sum(float(r["stake"]) for r in settled)
    pnl = sum(float(r["pnl"]) for r in settled)
    return {
        "logged": len(rows),
        "open": len(rows) - len(settled),
        "settled": len(settled),
        "wins": sum(r["result"] == "win" for r in settled),
        "losses": sum(r["result"] == "loss" for r in settled),
        "staked": round(staked, 2),
        "pnl": round(pnl, 2),
        "roi": round(pnl / staked, 4) if staked else 0.0,
        "expected_pnl": round(sum(float(r["ev"]) * float(r["stake"]) for r in settled), 2),
    }
