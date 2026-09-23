import json
import os
import tempfile
import unittest

from sportsbet import tracker
from sportsbet.value import devig, expected_value, fair_probabilities, find_value_bets, kelly_stake

SAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_odds.json")


class ValueTests(unittest.TestCase):
    def test_devig_sums_to_one(self):
        probs = devig({"A": 1.90, "B": 1.90})
        self.assertAlmostEqual(probs["A"], 0.5)
        self.assertAlmostEqual(sum(probs.values()), 1.0)

    def test_expected_value(self):
        self.assertAlmostEqual(expected_value(0.5, 2.10), 0.05)

    def test_kelly_zero_for_negative_edge(self):
        self.assertEqual(kelly_stake(0.4, 2.0, 100), 0.0)

    def test_kelly_capped(self):
        # Full Kelly here is 20%; quarter Kelly is 5%, cap is 2%.
        self.assertEqual(kelly_stake(0.6, 2.0, 100, fraction=0.25, max_pct=0.02), 2.0)

    def test_sharp_book_preferred_over_consensus(self):
        prices = {"pinnacle": {"A": 2.0, "B": 2.0}, "x": {"A": 1.5, "B": 3.0}, "y": {"A": 1.5, "B": 3.0}}
        fair, source = fair_probabilities(prices)
        self.assertEqual(source, "pinnacle")
        self.assertAlmostEqual(fair["A"], 0.5)

    def test_consensus_needs_min_books(self):
        fair, source = fair_probabilities({"x": {"A": 2.0, "B": 2.0}}, min_books=3)
        self.assertIsNone(fair)

    def test_sample_finds_expected_bets(self):
        with open(SAMPLE) as f:
            events = json.load(f)
        bets = find_value_bets(events, min_ev=0.03)
        picks = {(b.outcome, b.book) for b in bets}
        self.assertEqual(picks, {("Los Angeles Lakers", "draftkings"), ("Chelsea", "betsson")})
        self.assertTrue(all(b.ev >= 0.03 for b in bets))


class TrackerTests(unittest.TestCase):
    def test_log_settle_summary(self):
        with open(SAMPLE) as f:
            bets = find_value_bets(json.load(f))
        for b in bets:
            b.stake = 10.0
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bets.csv")
            self.assertEqual(len(tracker.log_bets(path, bets)), 2)
            self.assertEqual(len(tracker.log_bets(path, bets)), 0)  # duplicates skipped
            tracker.settle(path, 1, "win")
            tracker.settle(path, 2, "loss")
            s = tracker.summary(path)
            self.assertEqual((s["settled"], s["wins"], s["losses"], s["staked"]), (2, 1, 1, 20.0))


if __name__ == "__main__":
    unittest.main()
