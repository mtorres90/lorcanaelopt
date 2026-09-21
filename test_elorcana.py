import contextlib
import io
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import build_web
import db
import fetch_elorcana as fe

RPH_MIMEZ = "e88f642a-abae-41cd-bce0-eb3aacdcc8c1"
MELEE_MIMEZ = "e39e9d48-767c-42c6-82a2-ebc36e378a48"


def profile(uuid, name, source, elo, rank):
    return {"id": uuid, "source": source, "username": name, "metafyId": None}, \
           {"elo": elo, "eloRank": rank, "peakElo": elo + 20}


# Uma base de dados minima do "elorcana": autocomplete por prefixo + perfil por uuid.
PLAYERS = [
    profile(RPH_MIMEZ, "Mimez", "RPH", 1482.34, 7434),
    profile(MELEE_MIMEZ, "Mimez", "MELEE", 1518.0, 4578),   # o duplicado do Melee
    profile("rph-alex-1", "Alex", "RPH", 1600.0, 100),
    profile("rph-alex-2", "Alex", "RPH", 1400.0, 900),        # nome repetido no Play Hub
    profile("melee-only", "Solo", "MELEE", 1700.0, 50),       # so existe no Melee
    profile("rph-forced", "Other Nick", "RPH", 1550.0, 300),
]


class Handler(BaseHTTPRequestHandler):
    hits: list = []
    down = False

    def log_message(self, *a):
        pass

    def _send(self, code, body=None):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if body is not None:
            self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        u = urlparse(self.path)
        Handler.hits.append(self.path)
        if Handler.down:
            return self._send(500)
        if u.path == "/players/autocompleteName":
            prefix = parse_qs(u.query)["prefix"][0].lower()
            return self._send(200, [p for p, _ in PLAYERS if prefix in p["username"].lower()])
        if u.path.startswith("/players/"):
            uuid = u.path.rsplit("/", 1)[1]
            for p, stats in PLAYERS:
                if p["id"] == uuid:
                    return self._send(200, {"player": p, "stats": stats, "tournamentHistory": []})
        return self._send(404)


def make_db(path, players, hidden_ok=True):
    conn = db.connect(path)
    conn.execute("INSERT INTO events (id, name, date) VALUES ('e1', 'Evento', '2025-10-01')")
    for pid, name in players:
        conn.execute("INSERT INTO players (id, name) VALUES (?, ?)", (pid, name))
    ids = [p for p, _ in players]
    for i in range(0, len(ids) - 1, 2):
        conn.execute("INSERT INTO matches (event_id, round, player_a, player_b, score_a) VALUES ('e1', 1, ?, ?, 1)",
                     (ids[i], ids[i + 1]))
    conn.commit()
    conn.close()


class FetchTests(unittest.TestCase):
    def setUp(self):
        Handler.hits, Handler.down = [], False
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.dir = Path(self.tmp.name)
        self.db = str(self.dir / "t.db")
        make_db(self.db, [("100", "Mimez"), ("101", "Alex"), ("102", "Nobody"), ("103", "Solo"),
                          ("104", "Hidden Guy"), ("105", "Pick Me")])
        (self.dir / "opt.txt").write_text("104\n")
        self.out = self.dir / "elorcana.json"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def run_fetch(self, overrides="", min_events=1):
        ov = self.dir / "ov.txt"
        ov.write_text(overrides)
        args = SimpleNamespace(db=self.db, out=str(self.out), opt_out=str(self.dir / "opt.txt"),
                               overrides=str(ov), base=f"http://127.0.0.1:{self.server.server_port}", delay=0,
                               date_from="2025-09-05", min_events=min_events,
                               exclude_events=str(self.dir / "none.txt"), merges=str(self.dir / "none2.txt"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(fe.collect(args), 0)
        return json.loads(self.out.read_text(encoding="utf-8"))["players"]

    def test_picks_the_play_hub_profile_not_the_melee_duplicate(self):
        got = self.run_fetch()
        self.assertEqual(got["100"]["status"], "matched")
        self.assertEqual(got["100"]["id"], RPH_MIMEZ)
        self.assertEqual(got["100"]["elo"], 1482.3)
        self.assertEqual(got["100"]["rank"], 7434)

    def test_melee_only_and_unknown_players_get_nothing(self):
        got = self.run_fetch()
        self.assertEqual(got["103"]["status"], "none")   # so tem perfil no Melee
        self.assertEqual(got["102"]["status"], "none")
        self.assertNotIn("elo", got["103"])

    def test_two_play_hub_profiles_with_the_same_name_is_ambiguous_not_guessed(self):
        got = self.run_fetch()
        self.assertEqual(got["101"]["status"], "ambiguous")
        self.assertNotIn("elo", got["101"])

    def test_opted_out_players_are_never_looked_up(self):
        got = self.run_fetch()
        self.assertNotIn("104", got)
        self.assertFalse(any("Hidden" in h for h in Handler.hits))

    def test_overrides_can_force_or_suppress_a_match(self):
        got = self.run_fetch(f"105 rph-forced  # nome diferente no elorcana\n100 none\n101 rph-alex-2\n")
        self.assertEqual(got["105"]["status"], "matched")
        self.assertEqual(got["105"]["elo"], 1550.0)
        self.assertEqual(got["100"]["status"], "none")
        self.assertEqual(got["101"]["id"], "rph-alex-2")

    def test_an_override_pointing_at_a_melee_profile_is_rejected(self):
        got = self.run_fetch("103 melee-only\n")
        self.assertEqual(got["103"]["status"], "none")

    def test_second_run_only_refreshes_matches_and_skips_fresh_misses(self):
        self.run_fetch()
        Handler.hits.clear()
        self.run_fetch()
        # Mimez: so o perfil (sem nova pesquisa). Os "sem perfil"/"ambiguos" recentes nao voltam a ser pedidos.
        self.assertEqual(Handler.hits, [f"/players/{RPH_MIMEZ}"])

    def test_api_down_keeps_previous_data_and_does_not_fail(self):
        first = self.run_fetch()
        Handler.down = True
        again = self.run_fetch()
        self.assertEqual(again["100"], first["100"])

    def test_players_below_the_minimum_events_are_not_looked_up(self):
        got = self.run_fetch(min_events=2)   # todos so jogaram um evento
        self.assertEqual(got, {})
        self.assertEqual(Handler.hits, [])

    def test_renamed_player_is_looked_up_again(self):
        self.run_fetch()
        conn = db.connect(self.db)
        conn.execute("UPDATE players SET name = 'Someone Else' WHERE id = '100'")
        conn.commit()
        conn.close()
        got = self.run_fetch()
        self.assertEqual(got["100"]["status"], "none")


class BuildTests(unittest.TestCase):
    def test_site_data_carries_international_elo_only_for_matched_players(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            d = Path(tmp)
            make_db(str(d / "t.db"), [("100", "Mimez"), ("101", "Alex")])
            (d / "e.json").write_text(json.dumps({"updated": "2026-09-21", "players": {
                "100": {"status": "matched", "id": RPH_MIMEZ, "elo": 1482.3, "rank": 7434, "peak": 1502.3,
                        "name": "Mimez"},
                "101": {"status": "ambiguous", "name": "Alex"}}}), encoding="utf-8")
            (d / "opt.txt").write_text("")
            args = SimpleNamespace(db=str(d / "t.db"), out=str(d / "index.html"), date_from="2025-09-05",
                                   date_to=None, min_games=1, min_events=1, exclude_events=str(d / "x.txt"),
                                   merges=str(d / "y.txt"), opt_out=str(d / "opt.txt"),
                                   elorcana=str(d / "e.json"), contact="", demo=False)
            with contextlib.redirect_stdout(io.StringIO()):
                build_web.build(args)
            page = (d / "index.html").read_text(encoding="utf-8")
            data = json.JSONDecoder().raw_decode(page[page.index("var DATA = ") + len("var DATA = "):])[0]
            by = {p["id"]: p for p in data["players"]}
            self.assertEqual(by["100"]["intl"], {"id": RPH_MIMEZ, "elo": 1482.3, "rank": 7434, "peak": 1502.3})
            self.assertNotIn("intl", by["101"])
            self.assertEqual(data["meta"]["intl"], 1)
            self.assertEqual(data["meta"]["intlUpdated"], "21/09/2026")

    def test_site_builds_without_the_elorcana_file(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            d = Path(tmp)
            make_db(str(d / "t.db"), [("100", "Mimez"), ("101", "Alex")])
            (d / "opt.txt").write_text("")
            args = SimpleNamespace(db=str(d / "t.db"), out=str(d / "index.html"), date_from="2025-09-05",
                                   date_to=None, min_games=1, min_events=1, exclude_events=str(d / "x.txt"),
                                   merges=str(d / "y.txt"), opt_out=str(d / "opt.txt"),
                                   elorcana=str(d / "missing.json"), contact="", demo=False)
            with contextlib.redirect_stdout(io.StringIO()):
                build_web.build(args)
            self.assertTrue((d / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
