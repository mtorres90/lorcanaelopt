"""Testes da ingestao. A API e simulada com um servidor local: valida a mecanica
(paginacao, filtros, cache, CSV) e o parsing das formas de dados ASSUMIDAS.
Nao prova que a API real tenha estas formas: isso e o papel do modo --probe."""
import csv
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import ingest_playhub as ing


def rel(pid, name, won, uid=None):
    return {"id": pid * 10, "games_won": won,
            "player": {"id": pid, "user": {"id": uid or pid + 1000}, "best_identifier": name}}


EVENTS = [
    {"id": 1, "name": "Liga Core", "start_datetime": "2025-10-04T18:00:00Z",
     "store": {"name": "Loja PT", "city": "Lisboa", "full_address": "Rua X, Lisboa, 1000, PT"},
     "event_format": {"name": "Core Constructed"}},
    {"id": 2, "name": "Draft", "start_datetime": "2025-10-05T18:00:00Z",
     "store": {"name": "Loja PT", "city": "Lisboa", "full_address": "Rua X, Lisboa, 1000, PT"},
     "event_format": {"name": "Booster Draft"}},
    {"id": 3, "name": "Antes da rotacao", "start_datetime": "2025-08-01T18:00:00Z",
     "store": {"name": "Loja PT", "city": "Porto", "full_address": "Rua Y, Porto, 4000, PT"},
     "event_format": {"name": "Core Constructed"}},
    {"id": 4, "name": "Bern", "start_datetime": "2025-10-04T18:00:00Z",
     "store": {"name": "GoodGames", "city": "Bern", "full_address": "Laupenstrasse 4, Bern, 3008, CH"},
     "event_format": {"name": "Core Constructed"}},
]
DETAILS = {1: {"id": 1, "name": "Liga Core", "store": EVENTS[0]["store"],
               "tournament_phases": [{"rounds": [{"id": 101, "round_number": 1}, {"id": 102, "round_number": 2}]}]}}
MATCHES = {
    101: [
        {"player_match_relationships": [rel(1, "Ana", 2), rel(2, "Bruno", 0)], "winning_player": 1},
        {"player_match_relationships": [rel(3, "Carla", 1), rel(4, "Diogo", 1)], "match_is_intentional_draw": True},
    ],
    102: [
        {"player_match_relationships": [rel(1, "Ana", 0), rel(3, "Carla", 2)]},   # sem winning_player: usa games_won
        {"player_match_relationships": [rel(2, "Bruno", 0)], "match_is_bye": True},  # bye
    ],
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        url = urlparse(self.path)
        qs = parse_qs(url.query)
        page = int(qs.get("page", ["1"])[0])
        parts = [p for p in url.path.split("/") if p]
        if parts == ["events"]:
            size = 2
            chunk = EVENTS[(page - 1) * size: page * size]
            body = {"count": len(EVENTS), "results": chunk,
                    "next": "more" if page * size < len(EVENTS) else None}
            # so o 1.o centro devolve eventos; os outros devolvem vazio
            if float(qs["latitude"][0]) != 39.6:
                body = {"count": 0, "results": [], "next": None}
        elif len(parts) == 2 and parts[0] == "events":
            body = DETAILS[int(parts[1])]
        elif parts[0] == "tournament-rounds":
            body = {"results": MATCHES[int(parts[1])], "next": None}
        else:
            self.send_response(404)
            self.end_headers()
            return
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)


class ParsingTests(unittest.TestCase):
    def test_country(self):
        self.assertEqual(ing.country_of(EVENTS[0]), "PT")
        self.assertEqual(ing.country_of(EVENTS[3]), "CH")
        self.assertEqual(ing.country_of({"store": {"country": "Portugal"}}), "PT")

    def test_match_winner_draw_bye_and_fallback(self):
        ms = MATCHES[101] + MATCHES[102]
        self.assertEqual(ing.parse_match(ms[0])[4], "A")
        self.assertEqual(ing.parse_match(ms[1])[4], "D")
        self.assertEqual(ing.parse_match(ms[2])[4], "B")   # games_won 0 vs 2
        self.assertIsNone(ing.parse_match(ms[3]))          # bye

    def test_name_falls_back_to_first_name_and_initial(self):
        self.assertEqual(ing.player_name({"first_name": "Maria", "last_name": "Silva"}), "Maria S.")

    def test_player_key_prefers_user_id(self):
        self.assertEqual(ing.player_key({"id": 5, "user": {"id": 99}}), "99")

    def test_format_filter(self):
        self.assertTrue(ing.matches_format(EVENTS[0], ["core constructed"]))
        self.assertFalse(ing.matches_format(EVENTS[1], ["core constructed"]))

    def test_round_ids(self):
        self.assertEqual(ing.round_ids_of(DETAILS[1]), [(1, "101"), (2, "102")])


class PipelineTest(unittest.TestCase):
    def test_collect_filters_and_writes_csv(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                args = SimpleNamespace(
                    base=f"http://127.0.0.1:{server.server_port}", cache=str(Path(tmp) / "raw"),
                    delay=0, date_from="2025-09-05", date_to="2026-01-01", country="PT",
                    formats="core constructed", out=str(Path(tmp) / "m.csv"))
                self.assertEqual(ing.collect(args), 0)
                rows = list(csv.DictReader(open(args.out, encoding="utf-8")))
                self.assertEqual(len(rows), 3)  # 2 (ronda 1) + 1 (ronda 2); bye fora
                self.assertEqual({r["event_id"] for r in rows}, {"1"})
                self.assertEqual([r["result"] for r in rows], ["A", "D", "B"])
                # segunda corrida usa a cache dos detalhes/partidas (menos pedidos)
                self.assertEqual(ing.collect(args), 0)
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
