"""Testes da ingestao. A API e simulada com um servidor local, usando a FORMA REAL dos
dados observada na sondagem do Play Hub (campos e tipos). Validam a mecanica
(paginacao, filtros, fases, cache, CSV) e o parsing; nao validam valores reais."""
import contextlib
import csv
import io
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import ingest_playhub as ing


def rel(pid, name, first=None, last=None):
    player = {"id": pid, "pronouns": "", "country_code": None, "best_identifier": name}
    if first is not None:
        player["first_name"] = first
    if last is not None:
        player["last_name"] = last
    return {"id": pid * 10, "player_order": 1, "player": player,
            "user_event_status": {"id": pid * 100, "best_identifier": name, "user": {"id": pid + 5000}}}


def match(a, b, winner=None, **flags):
    base = {"player_match_relationships": [a, b], "winning_player": winner, "match_is_bye": False,
            "match_is_intentional_draw": False, "match_is_unintentional_draw": False,
            "match_is_loss": False}
    base.update(flags)
    return base


def store(city, country="PT"):
    return {"id": 1, "name": "Loja", "city": city, "country": country, "full_address": f"Rua, {city}, {country}"}


def ev(eid, name, day, fmt, st):
    return {"id": eid, "name": name, "start_datetime": f"{day}T18:00:00Z", "store": st,
            "event_format": "constructed", "gameplay_format": {"id": "g", "name": fmt},
            "is_test_event": False, "is_template": False}


ANA = rel(1, "Ana P", first="Ana", last="Pereira")  # tem nickname E nome completo separados
BRUNO, CARLA, DIOGO = rel(2, "Bruno M"), rel(3, "Carla S"), rel(4, "Diogo L")

EVENTS = [
    ev(1, "Liga Core", "2025-10-04", "Core Constructed", store("Lisboa")),
    ev(2, "Draft", "2025-10-05", "Booster Draft", store("Lisboa")),
    ev(3, "Antes da rotacao", "2025-08-01", "Core Constructed", store("Porto")),
    ev(4, "Bern", "2025-10-04", "Core Constructed", store("Bern", "CH")),
    dict(ev(5, "Teste", "2025-10-06", "Core Constructed", store("Lisboa")), is_test_event=True),
    ev(6, "Detalhe desaparecido", "2025-10-07", "Core Constructed", store("Lisboa")),
]
DETAILS = {1: {"id": 1, "name": "Liga Core", "store": {"name": "Loja", "country": "PT", "full_address": "Rua, Lisboa, PT"},
               "tournament_phases": [
                   # fase 2 listada primeiro de proposito: a ordem vem de order_in_phases
                   {"order_in_phases": 2, "rounds": [{"id": 103, "round_number": 1}]},
                   {"order_in_phases": 1, "rounds": [{"id": 102, "round_number": 2}, {"id": 101, "round_number": 1},
                                                     {"id": 999, "round_number": 3}]},  # ronda sem partidas na API (404)
               ]}}
# evento 6 nao tem entrada em DETAILS -> o Handler responde 404 ao pedido de detalhe
MATCHES = {
    101: [match(ANA, BRUNO, winner=1), match(CARLA, DIOGO, match_is_intentional_draw=True)],
    102: [match(ANA, CARLA, winner=3), match(BRUNO, DIOGO, match_is_bye=True)],
    103: [match(CARLA, ANA, winner=1),
          match(BRUNO, DIOGO),                        # sem resultado registado
          match(ANA, BRUNO, match_is_loss=True)],     # perda dupla
    # 999 fica de fora de proposito: simula uma ronda que a API ja nao consegue servir
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
            if float(qs["latitude"][0]) != 39.6:   # so o 1.o centro devolve eventos
                body = {"count": 0, "results": [], "next": None}
        elif len(parts) == 2 and parts[0] == "events":
            body = DETAILS.get(int(parts[1]))
            if body is None:   # simula um evento cujo detalhe ja nao existe na API
                self.send_response(404)
                self.end_headers()
                return
        elif parts[0] == "tournament-rounds":
            matches = MATCHES.get(int(parts[1]))
            if matches is None:   # simula uma ronda cujas partidas ja nao existem na API
                self.send_response(404)
                self.end_headers()
                return
            body = {"results": matches, "next": None}
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

    def test_winner_uses_player_id(self):
        self.assertEqual(ing.parse_match(MATCHES[101][0]),
                          ("1", "Ana P", "Ana Pereira", "2", "Bruno M", "", "A"))
        self.assertEqual(ing.parse_match(MATCHES[102][0])[6], "B")

    def test_draw_flags(self):
        self.assertEqual(ing.parse_match(MATCHES[101][1])[6], "D")
        m = match(ANA, BRUNO, match_is_unintentional_draw=True)
        self.assertEqual(ing.parse_match(m)[6], "D")

    def test_bye_unreported_and_double_loss_are_skipped(self):
        self.assertIsNone(ing.parse_match(MATCHES[102][1]))
        self.assertIsNone(ing.parse_match(MATCHES[103][1]))
        self.assertIsNone(ing.parse_match(MATCHES[103][2]))

    def test_winner_with_loss_flag_still_counts(self):
        self.assertEqual(ing.parse_match(match(ANA, BRUNO, winner=1, match_is_loss=True))[6], "A")

    def test_name_falls_back_to_first_name_and_initial(self):
        self.assertEqual(ing.player_name({"first_name": "Maria", "last_name": "Silva"}), "Maria S.")

    def test_real_name_needs_both_first_and_last(self):
        self.assertEqual(ing.player_real_name({"first_name": "Maria", "last_name": "Silva"}), "Maria Silva")
        self.assertEqual(ing.player_real_name({"first_name": "Maria"}), "")
        self.assertEqual(ing.player_real_name({}), "")

    def test_format_filter_uses_gameplay_format_name(self):
        self.assertTrue(ing.matches_format(EVENTS[0], ["core constructed"]))
        self.assertFalse(ing.matches_format(EVENTS[1], ["core constructed"]))

    def test_rounds_are_numbered_continuously_across_phases(self):
        self.assertEqual(ing.round_ids_of(DETAILS[1]),
                         [(1, "101"), (2, "102"), (3, "999"), (4, "103")])


class NotFoundHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/ok/"):
            body = json.dumps({"fine": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


class ClientNotFoundTests(unittest.TestCase):
    """O bug real: um 404 isolado (uma ronda invulgar, um evento apagado) nao pode
    derrubar uma recolha que demora horas. ignore_404 e o que evita isso."""

    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), NotFoundHandler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.tmp = tempfile.TemporaryDirectory()
        self.client = ing.Client(f"http://127.0.0.1:{self.server.server_port}",
                                 Path(self.tmp.name), delay=0)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def test_ignore_404_returns_none_instead_of_raising(self):
        self.assertIsNone(self.client.get("missing/", ignore_404=True))

    def test_without_ignore_404_still_raises(self):
        with self.assertRaises(RuntimeError):
            self.client.get("missing/")

    def test_404_is_cached_so_it_is_not_refetched(self):
        self.assertIsNone(self.client.get("missing/", ignore_404=True))
        before = self.client.requests
        self.assertIsNone(self.client.get("missing/", ignore_404=True))
        self.assertEqual(self.client.requests, before)

    def test_ok_path_unaffected(self):
        self.assertEqual(self.client.get("ok/x"), {"fine": True})


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
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    self.assertEqual(ing.collect(args), 0)
                with open(args.out, encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                self.assertEqual({r["event_id"] for r in rows}, {"1"})
                # ronda 999 (404) fica de fora sem travar a recolha; a ronda 103 passa a numero 4
                self.assertEqual([(r["round"], r["result"]) for r in rows],
                                 [("1", "A"), ("1", "D"), ("2", "B"), ("4", "B")])
                self.assertEqual(rows[0]["city"], "Lisboa")
                self.assertEqual(rows[0]["player_a_real_name"], "Ana Pereira")
                self.assertEqual(rows[0]["player_b_real_name"], "")
                self.assertIn("evento_404=1", buf.getvalue())    # evento 6: detalhe 404
                self.assertIn("ronda_404=1", buf.getvalue())     # ronda 999: partidas 404
                self.assertIn("evento_com_erro=0", buf.getvalue())
                self.assertEqual(ing.collect(args), 0)   # 2.a corrida usa a cache
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
