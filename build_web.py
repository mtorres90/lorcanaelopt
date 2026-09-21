#!/usr/bin/env python3
"""Gera a versao web de UMA so pagina (web/index.html), pronta a alojar ou publicar.

Calcula o Elo, embebe os resultados na pagina e junta CSS e JavaScript no mesmo ficheiro.
Uso:
  python build_web.py --db data/lorcana.db --out web/index.html
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import db
from build_site import ASSETS_DIR, STYLE_CSS, fold, fmt_date, load_opt_out
from elo import (K_PROVISIONAL, K_STABLE, PROVISIONAL_GAMES, START_RATING,
                  compute, extra_stats, rival_labels)

WEB_APP_JS = (ASSETS_DIR / "web_app.js").read_text(encoding="utf-8")

SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Lorcana Portugal Elo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&amp;family=Public+Sans:wght@400;600&amp;display=swap">
<style>
__CSS__
:root { padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }
html { scroll-padding-top: env(safe-area-inset-top, 0px); }
</style>
</head>
<body>
<div class="inkband" aria-hidden="true"></div>
__DEMO__
<header class="wrap top">
<a class="brand" href="#/">Lorcana Portugal Elo</a>
<nav aria-label="Main">
<a href="#/" data-key="ranking">Ranking</a>
<a href="#/events" data-key="events">Events</a>
<a href="#/about" data-key="about">About</a>
</nav>
</header>
<main class="wrap" id="app"></main>
<footer class="wrap foot">
<p>Fan project, not affiliated with Ravensburger or Disney. Disney Lorcana is a trademark of its respective owners.
Results sourced from the Ravensburger Play Hub. Updated on __UPDATED__.</p>
</footer>
<script>
var DATA = __DATA__;
__JS__
</script>
</body>
</html>
"""


def build(args: argparse.Namespace) -> None:
    conn = db.connect(args.db)
    matches = db.load_matches(conn, args.date_from, args.date_to)
    stats, history = compute(matches)
    if not stats:
        raise SystemExit("Sem partidas no período indicado. Importa dados primeiro (import_matches.py).")

    hidden = load_opt_out(args.opt_out)
    names = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM players")}
    real_names = {r["id"]: r["real_name"] for r in conn.execute("SELECT id, real_name FROM players")
                  if r["real_name"]}
    ev_rows = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM events")}

    visible = [s for s in stats.values() if s.id not in hidden]
    ranked = sorted((s for s in visible if s.games >= args.min_games),
                    key=lambda s: (-s.rating, -s.games, fold(names.get(s.id, s.id))))
    provisional = sorted((s for s in visible if s.games < args.min_games),
                         key=lambda s: (-s.games, fold(names.get(s.id, s.id))))
    rank_of = {s.id: i + 1 for i, s in enumerate(ranked)}

    hist_by_player: dict[str, list] = defaultdict(list)
    for h in history:
        hist_by_player[h.player].append(h)

    per_player: dict[str, list] = {}
    for h in history:
        opp = None if h.opponent in hidden else h.opponent
        per_player.setdefault(h.player, []).append(
            [h.date, h.event_id, h.round, opp, h.score, round(h.rating_after, 1), round(h.delta, 1)])

    def extra_of(pid: str) -> dict:
        rows = hist_by_player.get(pid, [])
        extra = extra_stats(rows, hidden)
        nemesis, victim = rival_labels(extra["h2h"])
        extra["nemesis"], extra["victim"] = nemesis, victim
        extra["low"] = round(extra["low"], 1)
        extra["best_gain"] = round(extra["best_gain"], 1)
        extra["worst_loss"] = round(extra["worst_loss"], 1)
        return extra

    def real_name_of(pid: str) -> str | None:
        rn = real_names.get(pid)
        return rn if rn and fold(rn) != fold(names.get(pid, "")) else None

    players = [{
        "id": s.id, "name": names.get(s.id, s.id), "realName": real_name_of(s.id),
        "rating": round(s.rating, 1),
        "peak": round(s.peak, 1), "games": s.games, "wins": s.wins, "draws": s.draws,
        "losses": s.losses, "rank": rank_of.get(s.id), "h": per_player.get(s.id, []),
        "extra": extra_of(s.id),
    } for s in ranked + provisional]

    by_event: dict[str, list] = {}
    for m in matches:
        by_event.setdefault(m.event_id, []).append(m)
    events = {}
    for eid, ms in by_event.items():
        ev = ev_rows[eid]
        events[eid] = {
            "id": eid, "name": ev.get("name"), "date": ev["date"], "store": ev.get("store"),
            "city": ev.get("city"), "players": len({p for m in ms for p in (m.player_a, m.player_b)}),
            "matches": len(ms),
        }

    data = {
        "meta": {"since": fmt_date(args.date_from), "matches": len(matches), "events": len(events),
                 "minGames": args.min_games, "ranked": len(ranked), "contact": args.contact},
        "consts": {"start": int(START_RATING), "k1": int(K_PROVISIONAL), "k2": int(K_STABLE),
                   "prov": PROVISIONAL_GAMES},
        "players": players,
        "events": events,
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    demo = ('<p class="demo">Sample data: players and results are made up to test the site.</p>'
            if args.demo else "")
    page = (SHELL
            .replace("__CSS__", STYLE_CSS)
            .replace("__JS__", WEB_APP_JS)
            .replace("__DEMO__", demo)
            .replace("__UPDATED__", date.today().strftime("%d/%m/%Y"))
            .replace("__DATA__", payload))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"Página gerada em {out} ({out.stat().st_size // 1024} kB): "
          f"{len(players)} jogadores, {len(matches)} partidas, {len(events)} eventos.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/lorcana.db")
    ap.add_argument("--out", default="web/index.html")
    ap.add_argument("--from", dest="date_from", default="2025-09-05")
    ap.add_argument("--to", dest="date_to", default=None)
    ap.add_argument("--min-games", type=int, default=5)
    ap.add_argument("--opt-out", default="opt_out.txt")
    ap.add_argument("--contact", default="")
    ap.add_argument("--demo", action="store_true")
    build(ap.parse_args())


if __name__ == "__main__":
    main()
