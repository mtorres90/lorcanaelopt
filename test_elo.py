import unittest

from elo import (K_PROVISIONAL, K_STABLE, PROVISIONAL_GAMES, START_RATING, Match,
                 compute, expected_score, k_factor)


def m(i, a, b, score, rnd=1, date="2026-01-10", event="e1"):
    return Match(i, event, date, rnd, a, b, score)


class EloTests(unittest.TestCase):
    def test_expected_score_is_symmetric(self):
        self.assertAlmostEqual(expected_score(1000, 1000), 0.5)
        self.assertAlmostEqual(expected_score(1200, 1000) + expected_score(1000, 1200), 1.0)

    def test_win_between_equals_moves_half_k(self):
        stats, _ = compute([m(1, "a", "b", 1.0)])
        self.assertAlmostEqual(stats["a"].rating, START_RATING + K_PROVISIONAL / 2)
        self.assertAlmostEqual(stats["b"].rating, START_RATING - K_PROVISIONAL / 2)

    def test_draw_between_equals_changes_nothing(self):
        stats, _ = compute([m(1, "a", "b", 0.5)])
        self.assertAlmostEqual(stats["a"].rating, START_RATING)
        self.assertEqual(stats["a"].draws, 1)

    def test_bye_and_self_matches_are_ignored(self):
        stats, _ = compute([m(1, "a", "", 1.0), m(2, "a", "a", 1.0)])
        self.assertEqual(stats, {})

    def test_same_round_uses_ratings_from_before_the_round(self):
        # Ordem das partidas dentro da ronda nao pode mudar o resultado.
        ms = [m(1, "a", "b", 1.0, rnd=1), m(2, "c", "d", 1.0, rnd=1)]
        s1, _ = compute(ms)
        s2, _ = compute(list(reversed(ms)))
        self.assertEqual({k: v.rating for k, v in s1.items()},
                         {k: v.rating for k, v in s2.items()})

    def test_later_round_uses_updated_ratings(self):
        stats, hist = compute([m(1, "a", "b", 1.0, rnd=1), m(2, "a", "c", 1.0, rnd=2)])
        second = [h for h in hist if h.match_id == 2 and h.player == "a"][0]
        self.assertAlmostEqual(second.rating_before, START_RATING + K_PROVISIONAL / 2)
        self.assertGreater(stats["a"].rating, second.rating_before)

    def test_history_records_both_players(self):
        _, hist = compute([m(1, "a", "b", 0.0)])
        by_player = {h.player: h for h in hist}
        self.assertEqual(by_player["a"].score, 0.0)
        self.assertEqual(by_player["b"].score, 1.0)
        self.assertLess(by_player["a"].delta, 0)

    def test_k_drops_after_provisional_period(self):
        self.assertEqual(k_factor(PROVISIONAL_GAMES - 1), K_PROVISIONAL)
        self.assertEqual(k_factor(PROVISIONAL_GAMES), K_STABLE)

    def test_chronological_order_wins_over_input_order(self):
        early = m(1, "a", "b", 1.0, date="2026-01-10")
        late = m(2, "b", "a", 1.0, date="2026-02-10", event="e2")
        s1, _ = compute([early, late])
        s2, _ = compute([late, early])
        self.assertAlmostEqual(s1["a"].rating, s2["a"].rating)


if __name__ == "__main__":
    unittest.main()
