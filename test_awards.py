import json
import tempfile
import unittest
from datetime import date
from itertools import count
from pathlib import Path

import awards
from elo import HistoryRow

_ids = count(1)


def hr(player, day, before, after, event="e1"):
    return HistoryRow(player, next(_ids), day, event, 1, "opp", 1.0, before, after, 1500.0)


def run(player, day, start, deltas, event="e1"):
    """Varias partidas seguidas do mesmo jogador: cada delta muda o Elo."""
    rows, r = [], start
    for d in deltas:
        rows.append(hr(player, day, r, r + d, event))
        r += d
    return rows


TODAY = date(2026, 9, 21)   # uma segunda-feira


class WeekTests(unittest.TestCase):
    def test_weeks_run_monday_to_sunday(self):
        self.assertEqual(awards.week_start("2026-09-14"), "2026-09-14")   # segunda
        self.assertEqual(awards.week_start("2026-09-20"), "2026-09-14")   # domingo
        self.assertEqual(awards.week_start("2026-09-21"), "2026-09-21")
        self.assertEqual(awards.week_end("2026-09-14"), "2026-09-20")


class WeeklyWinnerTests(unittest.TestCase):
    def test_most_elo_gained_in_the_week_wins_and_daily_gains_add_up(self):
        h = (run("a", "2026-09-12", 1500, [10, 10]) + run("a", "2026-09-13", 1520, [10, 10])   # a: +40 em 2 dias
             + run("b", "2026-09-13", 1500, [12, 12, 12, 12]))                                  # b: +48
        w = awards.weekly_winners(h, set(), TODAY)
        self.assertEqual([(x["start"], x["p"], x["gain"], x["n"]) for x in w], [("2026-09-07", "b", 48.0, 4)])

    def test_needs_the_minimum_number_of_matches(self):
        h = run("lucky", "2026-09-13", 1500, [40, 40, 40]) + run("steady", "2026-09-13", 1500, [10, 10, 10, 10])
        self.assertEqual(awards.weekly_winners(h, set(), TODAY)[0]["p"], "steady")   # 3 partidas < 4
        self.assertEqual(awards.weekly_winners(h, set(), TODAY, min_matches=3)[0]["p"], "lucky")

    def test_a_week_where_nobody_gains_elo_has_no_winner(self):
        h = run("a", "2026-09-13", 1500, [-10, -10, -10, -10]) + run("b", "2026-09-13", 1500, [-5, 5, -5, 5])
        self.assertEqual(awards.weekly_winners(h, set(), TODAY), [])

    def test_hidden_players_never_win(self):
        h = run("hidden", "2026-09-13", 1500, [30, 30, 30, 30]) + run("shown", "2026-09-13", 1500, [10, 10, 10, 10])
        self.assertEqual(awards.weekly_winners(h, {"hidden"}, TODAY)[0]["p"], "shown")

    def test_ties_go_to_more_matches_then_higher_elo(self):
        h = run("few", "2026-09-13", 1500, [10, 10, 10, 10]) + run("many", "2026-09-13", 1500, [8] * 5)
        self.assertEqual(awards.weekly_winners(h, set(), TODAY)[0]["p"], "many")       # 40 = 40, mais partidas
        h = run("low", "2026-09-13", 1400, [10] * 4) + run("high", "2026-09-13", 1600, [10] * 4)
        self.assertEqual(awards.weekly_winners(h, set(), TODAY)[0]["p"], "high")       # tudo igual: Elo mais alto

    def test_reports_elo_after_the_last_match_of_the_week(self):
        h = run("a", "2026-09-13", 1500, [10, -5, 20, 5])
        self.assertEqual(awards.weekly_winners(h, set(), TODAY)[0]["elo"], 1530.0)

    def test_the_current_week_is_provisional(self):
        h = run("a", "2026-09-13", 1500, [10] * 4) + run("b", "2026-09-21", 1500, [10] * 4)
        w = awards.weekly_winners(h, set(), date(2026, 9, 23))     # quarta da semana de b
        self.assertEqual([(x["p"], x["final"]) for x in w], [("a", True), ("b", False)])

    def test_a_week_closes_the_day_after_its_sunday(self):
        h = run("a", "2026-09-14", 1500, [10] * 4)
        self.assertFalse(awards.weekly_winners(h, set(), date(2026, 9, 20))[0]["final"])   # domingo ainda decorre
        self.assertTrue(awards.weekly_winners(h, set(), date(2026, 9, 21))[0]["final"])


class TitleTests(unittest.TestCase):
    def w(self, start, p, final=True):
        return {"start": start, "p": p, "final": final}

    def test_counts_titles_and_orders_by_titles_then_most_recent(self):
        weeks = [self.w("2026-08-03", "a"), self.w("2026-08-10", "b"), self.w("2026-08-17", "a"),
                 self.w("2026-08-24", "c"), self.w("2026-08-31", "b")]
        rows = awards.title_leaderboard(weeks)
        self.assertEqual([(r["p"], r["titles"], r["last"]) for r in rows],
                         [("b", 2, "2026-08-31"), ("a", 2, "2026-08-17"), ("c", 1, "2026-08-24")])

    def test_the_week_in_progress_does_not_count(self):
        rows = awards.title_leaderboard([self.w("2026-09-14", "a"), self.w("2026-09-21", "b", final=False)])
        self.assertEqual([r["p"] for r in rows], ["a"])

    def test_only_the_top_ten(self):
        weeks = [self.w(f"2026-01-{i + 1:02d}", f"p{i:02d}") for i in range(15)]
        self.assertEqual(len(awards.title_leaderboard(weeks)), 10)


SEASONS = [("2025-09-05", "Set 9"), ("2025-11-14", "Set 10"), ("2026-10-23", "Set 14")]


class SeasonFileTests(unittest.TestCase):
    def test_parses_sorts_and_skips_comments_and_bad_lines(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            p = Path(tmp) / "seasons.txt"
            p.write_text("# nota\n2025-11-14  Set 10 - Whispers  # fonte\nnot-a-date Lixo\n2025-09-05 Set 9\n2026-01-01\n",
                         encoding="utf-8")
            self.assertEqual(awards.load_seasons(str(p)),
                             [("2025-09-05", "Set 9"), ("2025-11-14", "Set 10 - Whispers"), ("2026-01-01", "2026-01-01")])

    def test_missing_file_means_no_seasons(self):
        self.assertEqual(awards.load_seasons("nao_existe.txt"), [])


class SeasonAwardTests(unittest.TestCase):
    def games(self, player, start_elo, day_events):
        """day_events: [(dia, evento, delta)] com uma partida cada."""
        rows, r = [], start_elo
        for day, ev, d in day_events:
            rows.append(hr(player, day, r, r + d, ev))
            r += d
        return rows

    def season(self, h, **kw):
        return awards.season_awards(h, SEASONS, set(), TODAY, min_matches=4, min_events=2, **kw)

    def test_winner_is_the_biggest_climb_within_the_season(self):
        h = (self.games("a", 1500, [("2025-09-10", "e1", 20), ("2025-09-11", "e1", 20), ("2025-09-20", "e2", 20),
                                    ("2025-09-21", "e2", 20)])
             + self.games("b", 1500, [("2025-09-10", "e1", 10), ("2025-09-11", "e1", 10), ("2025-09-20", "e2", 10),
                                      ("2025-09-21", "e2", 10)]))
        s = self.season(h)[0]
        self.assertEqual((s["name"], s["done"]), ("Set 9", True))
        self.assertEqual([(t["p"], t["gain"], t["from"], t["to"]) for t in s["top"]],
                         [("a", 80.0, 1500.0, 1580.0), ("b", 40.0, 1500.0, 1540.0)])

    def test_season_boundaries_use_the_release_day(self):
        # 2025-11-14 e o dia de lancamento do Set 10: essa partida ja e da epoca nova.
        h = self.games("a", 1500, [("2025-11-13", "e1", 10), ("2025-11-14", "e2", 10), ("2025-11-15", "e3", 10),
                                   ("2025-11-16", "e4", 10)])
        seasons = {s["name"]: s for s in awards.season_awards(h, SEASONS, set(), TODAY, min_matches=3, min_events=2)}
        self.assertEqual(seasons["Set 9"]["players"], 1)
        self.assertEqual(seasons["Set 10"]["players"], 1)
        self.assertEqual(seasons["Set 10"]["top"][0]["gain"], 30.0)    # so as 3 partidas a partir do dia 14 (Set 10)

    def test_minimums_for_matches_and_events_and_positive_gain(self):
        h = (self.games("few_matches", 1500, [("2025-09-10", "e1", 50), ("2025-09-11", "e2", 50)])
             + self.games("one_event", 1500, [("2025-09-10", "e1", 10)] * 5)
             + self.games("loser", 1500, [("2025-09-10", "e1", -10), ("2025-09-11", "e2", -10)] * 3)
             + self.games("ok", 1500, [("2025-09-10", "e1", 5), ("2025-09-11", "e2", 5)] * 2))
        self.assertEqual([t["p"] for t in self.season(h)[0]["top"]], ["ok"])

    def test_current_season_is_open_and_upcoming_seasons_are_skipped(self):
        h = self.games("a", 1500, [("2025-11-20", "e1", 10), ("2025-11-21", "e2", 10)] * 2)
        result = self.season(h)
        self.assertEqual([(s["name"], s["done"]) for s in result], [("Set 9", True), ("Set 10", False)])
        # Set 14 comeca depois de hoje
        self.assertEqual(len(awards.season_awards(h, SEASONS, set(), date(2026, 10, 23), 4, 2)), 3)

    def test_a_finished_season_reports_its_last_day_as_the_day_before_the_next_release(self):
        h = self.games("a", 1500, [("2025-11-20", "e1", 10), ("2025-11-21", "e2", 10)] * 2)
        by_name = {s["name"]: s for s in self.season(h)}
        self.assertEqual(by_name["Set 9"]["through"], "2025-11-13")
        self.assertIsNone(by_name["Set 10"]["through"])       # em curso: sem data de fim

    def test_a_season_closes_when_the_next_set_is_released(self):
        h = self.games("a", 1500, [("2025-11-20", "e1", 10), ("2025-11-21", "e2", 10)] * 2)
        before = awards.season_awards(h, SEASONS, set(), date(2026, 10, 22), 4, 2)
        after = awards.season_awards(h, SEASONS, set(), date(2026, 10, 23), 4, 2)
        self.assertFalse([s for s in before if s["name"] == "Set 10"][0]["done"])
        self.assertTrue([s for s in after if s["name"] == "Set 10"][0]["done"])

    def test_hidden_players_are_left_out(self):
        h = self.games("a", 1500, [("2025-09-10", "e1", 10), ("2025-09-11", "e2", 10)] * 2)
        self.assertEqual(awards.season_awards(h, SEASONS, {"a"}, TODAY, 4, 2)[0]["top"], [])


class ComputeAwardsTests(unittest.TestCase):
    def test_result_is_json_serialisable_and_carries_the_rules(self):
        h = run("a", "2026-09-13", 1500, [10] * 4, event="e1")
        result = awards.compute_awards(h, set(), TODAY, [("2025-09-05", "Set 9")])
        json.dumps(result)
        self.assertEqual(result["rules"], {"weekMin": 4, "seasonMinMatches": 15, "seasonMinEvents": 3})
        self.assertEqual(result["top"], [{"p": "a", "titles": 1, "last": "2026-09-07"}])


class BuildIntegrationTests(unittest.TestCase):
    def test_built_page_carries_weekly_and_season_awards(self):
        import contextlib
        import io
        from types import SimpleNamespace

        import build_web
        import db

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            d = Path(tmp)
            conn = db.connect(str(d / "t.db"))
            for i, day in enumerate(("2026-09-05", "2026-09-12", "2026-09-19")):      # tres sabados, um evento cada
                conn.execute("INSERT INTO events (id, name, date) VALUES (?, ?, ?)", (f"e{i}", f"Evento {i}", day))
            for pid in ("1", "2", "3"):
                conn.execute("INSERT INTO players (id, name) VALUES (?, ?)", (pid, f"Jogador {pid}"))
            for i in range(3):
                for rnd in range(1, 5):   # jogador 1 ganha sempre ao 2 e ao 3 alternadamente
                    conn.execute("INSERT INTO matches (event_id, round, player_a, player_b, score_a) VALUES (?, ?, ?, ?, 1)",
                                 (f"e{i}", rnd, "1", "2" if rnd % 2 else "3"))
            conn.commit()
            conn.close()
            (d / "seasons.txt").write_text("2026-09-01  Set A\n2026-10-01  Set B\n", encoding="utf-8")
            (d / "opt.txt").write_text("")
            args = SimpleNamespace(db=str(d / "t.db"), out=str(d / "index.html"), date_from="2025-09-05",
                                   date_to=None, min_games=1, min_events=1, exclude_events=str(d / "x.txt"),
                                   merges=str(d / "y.txt"), opt_out=str(d / "opt.txt"), elorcana=str(d / "none.json"),
                                   contact="", demo=False, seasons=str(d / "seasons.txt"), potw_min_matches=4,
                                   season_min_matches=8, season_min_events=2, today="2026-09-24")
            with contextlib.redirect_stdout(io.StringIO()):
                build_web.build(args)
            page = (d / "index.html").read_text(encoding="utf-8")
            data = json.JSONDecoder().raw_decode(page[page.index("var DATA = ") + len("var DATA = "):])[0]
            a = data["awards"]
            self.assertEqual([(w["start"], w["p"], w["final"]) for w in a["weeks"]],
                             [("2026-08-31", "1", True), ("2026-09-07", "1", True), ("2026-09-14", "1", True)])
            self.assertEqual(a["top"], [{"p": "1", "titles": 3, "last": "2026-09-14"}])
            self.assertEqual(a["seasons"][0]["name"], "Set A")
            self.assertFalse(a["seasons"][0]["done"])
            self.assertEqual(a["seasons"][0]["top"][0]["p"], "1")
            self.assertEqual(len(a["seasons"]), 1)                      # Set B ainda nao comecou


if __name__ == "__main__":
    unittest.main()
