import json
import re
import unittest
from itertools import count
from pathlib import Path

import achievements as ach
from elo import HistoryRow

_ids = count(1)
NO_SEASON = []


def hr(day="2026-01-01", ev="e1", rnd=1, opp="o", score=1.0, before=1500.0, after=None, opp_rating=1500.0,
       player="p"):
    if after is None:
        after = before + (10.0 if score == 1.0 else -10.0 if score == 0.0 else 0.0)
    return HistoryRow(player, next(_ids), day, ev, rnd, opp, score, before, after, opp_rating)


def days(n, start="2026-01-01"):
    """n datas seguidas a partir de `start` (dentro de Janeiro/Fevereiro)."""
    y, m, d = map(int, start.split("-"))
    from datetime import date, timedelta
    return [(date(y, m, d) + timedelta(days=i)).isoformat() for i in range(n)]


def run(rows, events=None, seasons=None, weeks=None, include=("p",)):
    out = ach.compute(rows, set(include), events or {}, seasons or [], weeks or [])
    return out["players"].get("p", {}), out


def evs(**kw):
    return {eid: {"store": s, "city": c, "players": n} for eid, (s, c, n) in kw.items()}


class RarityTests(unittest.TestCase):
    def test_thresholds(self):
        for pct, name in ((100, "common"), (40, "common"), (39.9, "uncommon"), (15, "uncommon"), (14.9, "rare"),
                          (5, "rare"), (4.9, "epic"), (1, "epic"), (0.9, "legendary"), (0, "legendary")):
            self.assertEqual(ach.rarity_of(pct), name, pct)


class LocationTests(unittest.TestCase):
    def test_different_stores_level_and_date(self):
        events = evs(e1=("A", "X", 10), e2=("B", "X", 10), e3=("A", "Y", 10), e4=("C", "Y", 10))
        rows = [hr("2026-01-01", "e1"), hr("2026-01-02", "e2"), hr("2026-01-03", "e3"), hr("2026-01-04", "e4")]
        res, _ = run(rows, events)
        self.assertEqual(res["stores"], [3, 1, "2026-01-04"])          # 3 lojas so no 4.o evento (A, B, C)

    def test_two_stores_are_not_enough(self):
        res, _ = run([hr("2026-01-01", "e1"), hr("2026-01-02", "e2")], evs(e1=("A", "X", 9), e2=("B", "X", 9)))
        self.assertEqual(res["stores"], [2, 0, None])

    def test_events_without_a_store_are_ignored(self):
        res, _ = run([hr("2026-01-01", "e1")], {"e1": {"store": None, "city": None, "players": 9}})
        self.assertNotIn("stores", res)

    def test_home_turf_counts_matches_at_the_same_store(self):
        events = evs(e1=("A", "X", 9))
        rows = [hr(d, "e1", opp=f"o{i}") for i, d in enumerate(days(20))]
        res, _ = run(rows, events)
        self.assertEqual(res["home"], [20, 1, "2026-01-20"])

    def test_cities(self):
        events = evs(e1=("A", "X", 9), e2=("B", "Y", 9), e3=("C", "Z", 9))
        res, _ = run([hr("2026-01-01", "e1"), hr("2026-01-02", "e2"), hr("2026-01-03", "e3")], events)
        self.assertEqual(res["cities"], [3, 1, "2026-01-03"])


class ParticipationTests(unittest.TestCase):
    def test_matches_events_and_wins(self):
        rows = [hr(d, f"e{i}", score=1.0 if i % 2 == 0 else 0.0, opp=f"o{i}") for i, d in enumerate(days(10))]
        res, _ = run(rows)
        self.assertEqual(res["matches"], [10, 1, "2026-01-10"])
        self.assertEqual(res["events"], [10, 2, "2026-01-10"])       # 10 eventos: niveis 5 e 10, o segundo no 10.o
        self.assertEqual(res["wins"], [5, 0, None])                  # 5 vitorias: o primeiro nivel e 10

    def test_nine_matches_is_progress_but_no_level(self):
        res, _ = run([hr(d, opp=f"o{i}") for i, d in enumerate(days(9))])
        self.assertEqual(res["matches"], [9, 0, None])


class StreakTests(unittest.TestCase):
    def rows(self, scores):
        return [hr(d, "e1", rnd=i + 1, score=s, opp=f"o{i}") for i, (d, s) in enumerate(zip(days(len(scores)), scores))]

    def test_three_wins_in_a_row(self):
        res, _ = run(self.rows([1, 1, 0, 1, 1, 1]))
        self.assertEqual(res["streak"], [3, 1, "2026-01-06"])

    def test_a_draw_or_loss_breaks_the_streak(self):
        res, _ = run(self.rows([1, 1, 0.5, 1, 1]))
        self.assertEqual(res["streak"][:2], [2, 0])


class RivalryTests(unittest.TestCase):
    def test_unique_opponents_only_count_once(self):
        rows = [hr(d, opp=f"o{i % 4}") for i, d in enumerate(days(12))]
        res, _ = run(rows)
        self.assertEqual(res["opponents"][:2], [4, 0])
        rows = [hr(d, opp=f"o{i}") for i, d in enumerate(days(10))]
        res, _ = run(rows)
        self.assertEqual(res["opponents"], [10, 1, "2026-01-10"])

    def test_same_opponent_matches(self):
        res, _ = run([hr(d, "e1", rnd=i + 1, opp="rival") for i, d in enumerate(days(3))])
        self.assertEqual(res["rival"], [3, 1, "2026-01-03"])

    def test_heartbreaker_needs_three_wins_against_the_same_opponent(self):
        res, _ = run([hr(d, opp="x", score=1.0) for d in days(3)])
        self.assertEqual(res["heartbreaker"], [1, 1, "2026-01-03"])
        res, _ = run([hr("2026-01-01", opp="x"), hr("2026-01-02", opp="x"), hr("2026-01-03", opp="x", score=0.0)])
        self.assertNotIn("heartbreaker", res)

    def test_nemesis_slayer_needs_three_earlier_losses_to_that_opponent(self):
        rows = [hr(d, opp="x", score=0.0) for d in days(3)] + [hr("2026-02-01", opp="x", score=1.0)]
        res, _ = run(rows)
        self.assertEqual(res["slayer"], [1, 1, "2026-02-01"])
        rows = [hr(d, opp="x", score=0.0) for d in days(2)] + [hr("2026-02-01", opp="x", score=1.0)]
        res, _ = run(rows)
        self.assertNotIn("slayer", res)


class EloTests(unittest.TestCase):
    def test_peak_elo_is_dated_when_first_reached(self):
        rows = [hr("2026-01-01", before=1500, after=1545), hr("2026-01-02", before=1545, after=1552),
                hr("2026-01-03", before=1552, after=1530)]
        res, _ = run(rows)
        self.assertEqual(res["peak"], [1552, 1, "2026-01-02"])

    def test_season_climb_needs_the_minimum_matches_in_the_season(self):
        season = [{"start": "2026-01-01", "done": False, "top": [], "through": None, "name": "S"}]
        rows = [hr(d, opp=f"o{i}", before=1500 + 4 * i, after=1504 + 4 * i) for i, d in enumerate(days(15))]   # +60
        res, _ = run(rows, seasons=season)
        self.assertEqual(res["climb"], [60, 1, "2026-01-15"])
        res, _ = run(rows[:14], seasons=season)
        self.assertNotIn("climb", res)              # 14 partidas: nao chega

    def test_season_climb_restarts_in_a_new_season(self):
        seasons = [{"start": "2026-01-01", "done": True, "top": [], "through": "2026-01-19", "name": "A"},
                   {"start": "2026-01-20", "done": False, "top": [], "through": None, "name": "B"}]
        d = days(10) + days(10, "2026-01-20")                       # 10 partidas na epoca A e 10 na B
        rows = [hr(d[i], opp=f"o{i}", before=1500 + 8 * i, after=1508 + 8 * i) for i in range(20)]
        res, _ = run(rows, seasons=seasons)
        self.assertNotIn("climb", res)              # nenhuma epoca tem 15 partidas

    def test_david_vs_goliath_uses_the_biggest_win_against_a_higher_rated_opponent(self):
        res, _ = run([hr(before=1500, after=1520, opp_rating=1600)])
        self.assertEqual(res["goliath"], [100, 1, "2026-01-01"])
        res, _ = run([hr(before=1500, after=1520, opp_rating=1599)])
        self.assertEqual(res["goliath"][:2], [99, 0])                # progresso, mas ainda sem nivel
        res, _ = run([hr("2026-01-01", before=1500, after=1520, opp_rating=1600),
                      hr("2026-01-02", before=1520, after=1535, opp_rating=1725)])
        self.assertEqual(res["goliath"], [205, 2, "2026-01-02"])
        res, _ = run([hr(score=0.0, before=1500, after=1490, opp_rating=1700)])      # derrota nao conta
        self.assertNotIn("goliath", res)
        res, _ = run([hr(before=1600, after=1610, opp_rating=1500)])                 # ganhar a alguem abaixo tambem nao
        self.assertNotIn("goliath", res)


class EventTests(unittest.TestCase):
    def event(self, ev, day, scores):
        return [hr(day, ev, rnd=i + 1, score=s, opp=f"{ev}-o{i}") for i, s in enumerate(scores)]

    def test_undefeated_events_and_flawless_debut(self):
        rows = (self.event("e1", "2026-01-01", [1, 1, 1]) + self.event("e2", "2026-01-08", [1, 1]) +
                self.event("e3", "2026-01-15", [1, 1, 1, 1]) + self.event("e4", "2026-01-22", [1, 1, 1]))
        res, _ = run(rows)
        self.assertEqual(res["undefeated"], [3, 2, "2026-01-22"])      # e2 tem so 2 partidas
        self.assertEqual(res["debut"], [1, 1, "2026-01-01"])

    def test_a_loss_or_a_draw_spoils_it_and_only_the_first_event_is_a_debut(self):
        rows = self.event("e1", "2026-01-01", [1, 1, 0]) + self.event("e2", "2026-01-08", [1, 1, 1])
        res, _ = run(rows)
        self.assertEqual(res["undefeated"][:2], [1, 1])
        self.assertNotIn("debut", res)                                  # o primeiro evento teve derrota
        res, _ = run(self.event("e1", "2026-01-01", [1, 1, 0.5]))
        self.assertNotIn("undefeated", res)

    def test_big_room(self):
        res, _ = run([hr("2026-01-05", "e1")], evs(e1=("A", "X", 32)))
        self.assertEqual(res["bigroom"], [1, 1, "2026-01-05"])
        res, _ = run([hr("2026-01-05", "e1")], evs(e1=("A", "X", 31)))
        self.assertNotIn("bigroom", res)

    def test_comeback_after_three_losses_in_a_row(self):
        rows = [hr(d, opp=f"o{i}", score=s) for i, (d, s) in enumerate(zip(days(5), [0, 0, 0, 1, 1]))]
        res, _ = run(rows)
        self.assertEqual(res["comeback"], [1, 1, "2026-01-04"])
        rows = [hr(d, opp=f"o{i}", score=s) for i, (d, s) in enumerate(zip(days(5), [0, 0, 0.5, 0, 1]))]
        res, _ = run(rows)
        self.assertNotIn("comeback", res)                               # o empate quebra a sequencia

    def test_rubber_match_is_a_win_in_the_final_round_of_an_event_with_3_or_more_rounds(self):
        # o adversario (outro jogador) tambem tem linhas no historico: e delas que se sabe a ultima ronda
        rows = [hr("2026-01-01", "e1", rnd=3, score=1.0), hr("2026-01-01", "e1", rnd=3, score=0.0, player="q")]
        self.assertEqual(run(rows)[0]["rubber"][:2], [1, 1])
        rows = [hr("2026-01-01", "e1", rnd=2, score=1.0), hr("2026-01-01", "e1", rnd=3, score=0.0, player="q")]
        self.assertNotIn("rubber", run(rows)[0])                         # ganhou a ronda 2, a final foi a 3
        rows = [hr("2026-01-01", "e1", rnd=2, score=1.0)]
        self.assertNotIn("rubber", run(rows)[0])                         # evento so com 2 rondas


class AwardTests(unittest.TestCase):
    WEEKS = [{"p": "p", "end": "2026-02-01", "final": True}, {"p": "x", "end": "2026-02-08", "final": True},
             {"p": "p", "end": "2026-02-15", "final": True}, {"p": "p", "end": "2026-02-22", "final": False}]
    SEASONS = [{"start": "2025-09-05", "done": True, "through": "2025-11-13", "name": "A",
                "top": [{"p": "p"}, {"p": "x"}, {"p": "y"}]},
               {"start": "2025-11-14", "done": True, "through": "2026-02-19", "name": "B",
                "top": [{"p": "x"}, {"p": "y"}, {"p": "p"}]},
               {"start": "2026-02-20", "done": False, "through": None, "name": "C", "top": [{"p": "p"}]}]

    def test_player_of_the_week_counts_only_finished_weeks(self):
        res, _ = run([hr("2026-01-01")], weeks=self.WEEKS)
        self.assertEqual(res["potw"], [2, 2, "2026-02-15"])              # a semana em curso nao conta

    def test_most_improved_winner_and_podium_only_for_finished_seasons(self):
        res, _ = run([hr("2026-01-01")], seasons=self.SEASONS)
        self.assertEqual(res["improved"], [1, 1, "2025-11-13"])
        self.assertEqual(res["podium"], [1, 1, "2025-11-13"])            # 1.o na epoca A, 3.o na B; a C ainda decorre

    def test_a_player_who_never_won_has_no_award_achievements(self):
        out = ach.compute([hr("2026-01-01", player="z")], {"z"}, {}, self.SEASONS, self.WEEKS)["players"]["z"]
        for k in ("potw", "improved", "podium"):
            self.assertNotIn(k, out)


class LoyaltyTests(unittest.TestCase):
    SEASONS = [{"start": "2026-01-01", "done": True, "through": "2026-01-31", "name": "A", "top": []},
               {"start": "2026-02-01", "done": True, "through": "2026-02-28", "name": "B", "top": []},
               {"start": "2026-03-01", "done": False, "through": None, "name": "C", "top": []}]

    def test_founding_member_and_season_veteran(self):
        rows = [hr("2026-01-10"), hr("2026-02-10"), hr("2026-03-10")]
        res, _ = run(rows, seasons=self.SEASONS)
        self.assertEqual(res["founder"], [1, 1, "2026-01-10"])
        self.assertEqual(res["seasons"], [3, 1, "2026-03-10"])

    def test_joining_after_the_first_season_is_not_a_founder(self):
        res, _ = run([hr("2026-02-10")], seasons=self.SEASONS)
        self.assertNotIn("founder", res)
        self.assertEqual(res["seasons"][:2], [1, 0])

    def test_matches_before_the_first_season_do_not_count_as_a_season(self):
        res, _ = run([hr("2025-12-31")], seasons=self.SEASONS)
        self.assertNotIn("seasons", res)


class OutputTests(unittest.TestCase):
    def test_excluded_players_are_left_out_of_everything(self):
        rows = [hr(d, opp=f"o{i}") for i, d in enumerate(days(10))] + \
               [hr(d, opp=f"o{i}", player="hidden") for i, d in enumerate(days(10))]
        _, out = run(rows, include=("p",))
        self.assertEqual(set(out["players"]), {"p"})
        self.assertEqual(out["total"], 1)
        self.assertEqual(out["holders"]["matches"], [1, 0, 0, 0, 0])

    def test_holders_and_rarity_follow_the_share_of_players(self):
        rows = []
        for i in range(10):                  # 10 jogadores; so o p tem 10 partidas (10%: rara)
            rows += [hr(d, opp=f"o{j}", player=f"q{i}") for j, d in enumerate(days(3))]
        rows += [hr(d, opp=f"o{j}") for j, d in enumerate(days(10))]
        _, out = run(rows, include=tuple(["p"] + [f"q{i}" for i in range(10)]))
        self.assertEqual(out["total"], 11)
        self.assertEqual(out["holders"]["matches"][0], 1)
        self.assertEqual(out["rarity"]["matches"][0], "rare")              # 1/11 = 9.1 %
        self.assertEqual(out["rarity"]["matches"][4], "legendary")         # ninguem

    def test_the_result_is_json_serialisable(self):
        _, out = run([hr(d, opp=f"o{i}") for i, d in enumerate(days(12))])
        json.dumps(out)

    def test_every_definition_is_well_formed(self):
        ids = [d["id"] for d in ach.DEFS]
        self.assertEqual(len(ids), len(set(ids)))
        for d in ach.DEFS:
            self.assertIn(d["cat"], ach.CATEGORIES)
            self.assertEqual(d["levels"], sorted(d["levels"]))
            self.assertTrue(d["levels"])


class TextsTests(unittest.TestCase):
    """Todas as conquistas e categorias tem texto em portugues E em ingles no site."""

    JS = (Path(__file__).parent / "assets" / "web_app.js").read_text(encoding="utf-8")

    def test_names_and_descriptions_exist_in_both_languages(self):
        for d in ach.DEFS:
            for suffix in ("n", "d"):
                key = f"ach_{d['id']}_{suffix}:"
                self.assertEqual(self.JS.count(key), 2, key)

    def test_categories_exist_in_both_languages(self):
        for c in ach.CATEGORIES:
            self.assertEqual(self.JS.count(f"achCat_{c}:"), 2, c)

    def test_rarity_names_exist_in_both_languages(self):
        for _, name in ach.RARITY:
            self.assertEqual(len(re.findall(rf"\brar_{name}:", self.JS)), 2, name)


if __name__ == "__main__":
    unittest.main()
