import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import build_web
import curate
import db
from elo import Match


def m(i, event, a, b, rnd=1, score=1.0, date="2026-01-01"):
    return Match(i, event, date, rnd, a, b, score)


EVENTS = {
    "e1": {"name": "Saturday Constructed"},
    "e2": {"name": "Sunday Constructed"},
    "ink": {"name": "Inkado"},
    "crown1": {"name": "Crown of Ink Online"},
    "crown2": {"name": "Crown of ink - online"},
    "crown3": {"name": "Crown of Ink Finals"},   # presencial: nao e excluido
}


def players_of(ms):
    return {p for x in ms for p in (x.player_a, x.player_b)}


class NormTests(unittest.TestCase):
    def test_ignores_case_accents_and_punctuation(self):
        self.assertEqual(curate.norm("  Crown of ink - ONLINE! "), "crown of ink online")
        self.assertEqual(curate.norm("Fénix Negra"), "fenix negra")


class ExcludedEventsTests(unittest.TestCase):
    def test_events_are_excluded_by_name_however_they_are_spelled(self):
        ms = [m(1, "e1", "a", "b"), m(2, "ink", "a", "b"), m(3, "crown1", "a", "b"),
              m(4, "crown2", "a", "b"), m(5, "crown3", "a", "b")]
        kept, rep = curate.curate(ms, EVENTS, ["inkado", "crown of ink online"], min_events=1)
        self.assertEqual([x.id for x in kept], [1, 5])
        self.assertEqual((rep.excluded_events, rep.excluded_matches), (3, 3))

    def test_no_rules_keeps_everything(self):
        ms = [m(1, "ink", "a", "b")]
        self.assertEqual(curate.curate(ms, EVENTS, [], min_events=1)[0], ms)


class MergeTests(unittest.TestCase):
    def test_merged_account_is_replaced_and_self_matches_disappear(self):
        ms = [m(1, "e1", "old", "x"), m(2, "e1", "keep", "y"), m(3, "e2", "old", "keep")]
        kept, rep = curate.curate(ms, EVENTS, merges={"old": "keep"}, min_events=1)
        self.assertEqual([(x.player_a, x.player_b) for x in kept], [("keep", "x"), ("keep", "y")])
        self.assertEqual(rep.merged, [("old", "keep")])

    def test_chained_merges_resolve_to_the_final_account(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            p = Path(tmp) / "merges.txt"
            p.write_text("# nota\n1 2\n2 3  # depois\n5 5\nlixo\n7 8 9\n", encoding="utf-8")
            self.assertEqual(curate.load_merges(str(p)), {"1": "3", "2": "3"})

    def test_a_merge_cycle_is_ignored_instead_of_looping(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            p = Path(tmp) / "merges.txt"
            p.write_text("1 2\n2 1\n", encoding="utf-8")
            curate.load_merges(str(p))   # nao pode ficar preso

    def test_missing_files_mean_no_rules(self):
        self.assertEqual(curate.load_merges("nao_existe.txt"), {})
        self.assertEqual(curate.load_excluded("nao_existe.txt"), [])


class MinEventsTests(unittest.TestCase):
    def test_one_event_players_and_their_matches_are_dropped(self):
        ms = [m(1, "e1", "a", "b"), m(2, "e2", "a", "b"),          # a e b: 2 eventos
              m(3, "e1", "a", "tourist")]                           # visitante: 1 evento
        kept, rep = curate.curate(ms, EVENTS, min_events=2)
        self.assertEqual([x.id for x in kept], [1, 2])
        self.assertEqual((rep.dropped_players, rep.dropped_matches), (1, 1))

    def test_excluded_events_do_not_count_towards_the_minimum(self):
        # v jogou um evento normal e um Inkado: depois de excluir o Inkado so tem 1.
        ms = [m(1, "e1", "v", "a"), m(2, "ink", "v", "a"), m(3, "e2", "a", "b"), m(4, "e1", "b", "c"),
              m(5, "e2", "c", "a"), m(6, "e1", "a", "b")]
        kept, _ = curate.curate(ms, EVENTS, ["inkado"], min_events=2)
        self.assertNotIn("v", players_of(kept))
        self.assertEqual(players_of(kept), {"a", "b", "c"})

    def test_merging_two_accounts_can_reach_the_minimum(self):
        ms = [m(1, "e1", "acc1", "a"), m(2, "e2", "acc2", "a"), m(3, "e1", "a", "b"), m(4, "e2", "a", "b")]
        kept, _ = curate.curate(ms, EVENTS, merges={"acc2": "acc1"}, min_events=2)
        self.assertIn("acc1", players_of(kept))
        self.assertNotIn("acc2", players_of(kept))

    def test_dropping_a_player_can_push_another_below_the_minimum(self):
        # b joga 2 eventos, mas no e2 so contra o visitante t (1 evento); sem t, b fica com 1 evento.
        ms = [m(1, "e1", "a", "b"), m(2, "e2", "b", "t"), m(3, "e1", "a", "c"), m(4, "e2", "a", "c")]
        kept, rep = curate.curate(ms, EVENTS, min_events=2)
        self.assertEqual(players_of(kept), {"a", "c"})
        self.assertEqual(rep.dropped_players, 2)

    def test_minimum_of_one_disables_the_rule(self):
        ms = [m(1, "e1", "a", "b")]
        self.assertEqual(curate.curate(ms, EVENTS, min_events=1)[0], ms)


class AutoMergeTests(unittest.TestCase):
    def dm(self, matches, names, **kw):
        return curate.curate(matches, EVENTS, names=names, min_events=1, **kw)

    def test_same_nickname_merges_into_the_account_with_the_most_recent_event(self):
        ms = [m(1, "e1", "old", "x", date="2026-01-01"), m(2, "e2", "new", "y", date="2026-05-01")]
        kept, rep = self.dm(ms, {"old": "Brudah", "new": "brudah", "x": "X", "y": "Y"})
        self.assertEqual(players_of(kept), {"new", "x", "y"})
        self.assertEqual(rep.auto_merged, [("brudah", "old", "new")])

    def test_matching_ignores_case_accents_and_punctuation(self):
        ms = [m(1, "e1", "a", "x", date="2026-01-01"), m(2, "e2", "b", "y", date="2026-02-01")]
        kept, _ = self.dm(ms, {"a": "João Silva", "b": "joao silva.", "x": "X", "y": "Y"})
        self.assertEqual(players_of(kept), {"b", "x", "y"})

    def test_accounts_that_played_the_same_event_are_different_people(self):
        ms = [m(1, "e1", "a", "x"), m(2, "e1", "b", "y"), m(3, "e2", "a", "y")]
        kept, rep = self.dm(ms, {"a": "Pedro", "b": "Pedro", "x": "X", "y": "Y"})
        self.assertEqual(players_of(kept), {"a", "b", "x", "y"})
        self.assertEqual(rep.auto_merged, [])
        self.assertEqual(rep.kept_separate[0][1:], (["a", "b"], "jogaram no mesmo evento"))

    def test_abbreviated_play_hub_names_are_not_merged(self):
        ms = [m(1, "e1", "a", "x", date="2026-01-01"), m(2, "e2", "b", "y", date="2026-02-01")]
        for names in ({"a": "Pedro R", "b": "Pedro R."}, {"a": "João M", "b": "Joao M"}):
            kept, rep = self.dm(ms, {**names, "x": "X", "y": "Y"})
            self.assertEqual(players_of(kept), {"a", "b", "x", "y"})
            self.assertEqual(rep.kept_separate[0][2], "nome abreviado do Play Hub")

    def test_keep_marks_an_account_as_never_merged(self):
        ms = [m(1, "e1", "a", "x", date="2026-01-01"), m(2, "e2", "b", "y", date="2026-02-01")]
        kept, rep = self.dm(ms, {"a": "Tadashi", "b": "Tadashi", "x": "X", "y": "Y"}, keep_separate={"a"})
        self.assertEqual(players_of(kept), {"a", "b", "x", "y"})
        self.assertEqual(rep.kept_separate[0][2], "marcada com keep")

    def test_three_accounts_merge_only_the_ones_that_never_shared_an_event(self):
        ms = [m(1, "e1", "a", "x", date="2026-01-01"), m(2, "e2", "b", "x", date="2026-03-01"),
              m(3, "e3", "c", "x", date="2026-05-01"), m(4, "e2", "c", "y", date="2026-03-01")]
        # c jogou o e2 tal como b => c e b sao pessoas diferentes; a nao partilha eventos com nenhum
        kept, rep = self.dm(ms, {"a": "Ana", "b": "Ana", "c": "Ana", "x": "X", "y": "Y"})
        ps = players_of(kept)
        self.assertIn("c", ps)
        self.assertEqual(len({"a", "b", "c"} & ps), 2)
        self.assertEqual(len(rep.auto_merged), 1)

    def test_tie_on_last_date_goes_to_the_account_with_more_events(self):
        ms = [m(1, "e1", "few", "x", date="2026-09-18"), m(2, "e2", "many", "x", date="2026-09-18"),
              m(3, "e3", "many", "y", date="2026-08-01")]
        kept, rep = self.dm(ms, {"few": "Pedro", "many": "Pedro", "x": "X", "y": "Y"})
        self.assertEqual(rep.auto_merged, [("Pedro", "few", "many")])

    def test_without_names_nothing_is_merged_automatically(self):
        ms = [m(1, "e1", "a", "x"), m(2, "e2", "b", "y")]
        self.assertEqual(curate.curate(ms, EVENTS, min_events=1)[0], ms)

    def test_merged_accounts_add_up_to_reach_the_minimum_events(self):
        ms = [m(1, "e1", "a", "p", date="2026-01-01"), m(2, "e2", "b", "p", date="2026-02-01"),
              m(3, "e1", "p", "q", date="2026-01-01"), m(4, "e2", "p", "q", date="2026-02-01"),
              m(5, "e1", "q", "r", date="2026-01-01"), m(6, "e2", "q", "r", date="2026-02-01")]
        names = {"a": "Bia", "b": "Bia", "p": "P", "q": "Q", "r": "R"}
        kept, _ = curate.curate(ms, EVENTS, names=names, min_events=2)
        self.assertIn("b", players_of(kept))
        self.assertNotIn("a", players_of(kept))

    def test_keep_and_merge_lines_are_read_from_the_same_file(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            p = Path(tmp) / "merges.txt"
            p.write_text("keep 7  # dois Pedros diferentes\n1 2\nkeep\n", encoding="utf-8")
            self.assertEqual(curate.load_keep_separate(str(p)), {"7"})
            self.assertEqual(curate.load_merges(str(p)), {"1": "2"})


class BuildIntegrationTests(unittest.TestCase):
    """O site inteiro respeita as regras: quem nao conta nao aparece."""

    def test_site_applies_exclusions_merges_and_minimum(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            d = Path(tmp)
            conn = db.connect(str(d / "t.db"))
            for eid, name, date in (("e1", "Saturday", "2026-01-03"), ("e2", "Sunday", "2026-01-04"),
                                    ("e3", "Friday", "2026-01-09"), ("ink", "Inkado", "2026-01-10")):
                conn.execute("INSERT INTO events (id, name, date) VALUES (?, ?, ?)", (eid, name, date))
            for pid, name in (("1", "Ana"), ("2", "Bruno"), ("3", "Brudah"), ("4", "Brudah II"),
                              ("5", "Tourist"), ("6", "OnlyInkado")):
                conn.execute("INSERT INTO players (id, name) VALUES (?, ?)", (pid, name))
            rows = [("e1", 1, "1", "2"), ("e2", 1, "1", "2"), ("e1", 2, "1", "3"), ("e2", 2, "2", "4"),
                    ("e3", 1, "1", "5"), ("ink", 1, "1", "6"), ("e3", 2, "2", "1")]
            for ev, rnd, a, b in rows:
                conn.execute("INSERT INTO matches (event_id, round, player_a, player_b, score_a) "
                             "VALUES (?, ?, ?, ?, 1)", (ev, rnd, a, b))
            conn.commit()
            conn.close()
            (d / "ex.txt").write_text("inkado\n")
            (d / "mg.txt").write_text("4 3\n")
            (d / "opt.txt").write_text("")
            args = SimpleNamespace(db=str(d / "t.db"), out=str(d / "index.html"), date_from="2025-09-05",
                                   date_to=None, min_games=1, min_events=2, exclude_events=str(d / "ex.txt"),
                                   merges=str(d / "mg.txt"), opt_out=str(d / "opt.txt"),
                                   elorcana=str(d / "none.json"), contact="", demo=False)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                build_web.build(args)
            page = (d / "index.html").read_text(encoding="utf-8")
            data = json.JSONDecoder().raw_decode(page[page.index("var DATA = ") + len("var DATA = "):])[0]
            by = {p["id"]: p for p in data["players"]}
            self.assertNotIn("4", by)                   # conta fundida em "3"
            self.assertEqual(by["3"]["games"], 2)       # as partidas das duas contas
            self.assertNotIn("5", by)                   # visitante: um so evento
            self.assertNotIn("6", by)                   # so jogou o Inkado
            self.assertNotIn("ink", data["events"])
            self.assertEqual(by["3"]["name"], "Brudah")
            self.assertIn("Curadoria:", out.getvalue())


if __name__ == "__main__":
    unittest.main()
