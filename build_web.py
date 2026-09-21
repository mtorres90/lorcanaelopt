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

import achievements
import awards
import curate
import db
from build_site import ASSETS_DIR, STYLE_CSS, fold, fmt_date, load_opt_out
from elo import (K_PROVISIONAL, K_STABLE, PROVISIONAL_GAMES, START_RATING,
                  compute, extra_stats, rival_labels)

WEB_APP_JS = (ASSETS_DIR / "web_app.js").read_text(encoding="utf-8")

SHELL = """<!doctype html>
<html lang="pt-PT">
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
<div class="top-right">
<nav aria-label="Principal" data-i18n-aria="navMain">
<a href="#/" data-key="ranking" data-i18n="navRanking">Ranking</a>
<a href="#/international" data-key="international" data-i18n="navIntl">Internacional</a>
<a href="#/awards" data-key="awards" data-i18n="navAwards">Jogador da semana</a>
<a href="#/events" data-key="events" data-i18n="navEvents">Eventos</a>
<a href="#/about" data-key="about" data-i18n="navAbout">Sobre</a>
</nav>
<div class="lang" role="group" aria-label="Language / Idioma">
<button type="button" class="lang-btn" data-lang="pt" aria-label="Portugu&ecirc;s" title="Portugu&ecirc;s" aria-pressed="true">
<svg viewBox="0 0 30 20" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
<rect width="30" height="20" fill="#f00"/>
<rect width="12" height="20" fill="#060"/>
<circle cx="12" cy="10" r="4.2" fill="#fc0"/>
<rect x="10.3" y="8.3" width="3.4" height="3.4" fill="#fff"/>
</svg></button>
<button type="button" class="lang-btn" data-lang="en" aria-label="English" title="English" aria-pressed="false">
<svg viewBox="0 0 60 30" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
<clipPath id="uk-clip"><path d="M30,15 h30 v15 z v15 h-30 z h-30 v-15 z v-15 h30 z"/></clipPath>
<path d="M0,0 v30 h60 v-30 z" fill="#012169"/>
<path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/>
<path d="M0,0 L60,30 M60,0 L0,30" clip-path="url(#uk-clip)" stroke="#c8102e" stroke-width="4"/>
<path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/>
<path d="M30,0 v30 M0,15 h60" stroke="#c8102e" stroke-width="6"/>
</svg></button>
</div>
</div>
</header>
<main class="wrap" id="app"></main>
<footer class="wrap foot">
<p id="foot" data-updated="__UPDATED__">Projeto de fãs, sem afiliação à Ravensburger ou à Disney. Disney Lorcana é uma marca registada dos respetivos proprietários.
Resultados obtidos do Ravensburger Play Hub. Atualizado em __UPDATED__.</p>
</footer>
<script>
var DATA = __DATA__;
__JS__
</script>
</body>
</html>
"""


def load_intl(path: str | None) -> tuple[dict[str, dict], str | None]:
    """Elo internacional (elorcana) por id do Play Hub. Ficheiro opcional, criado por
    fetch_elorcana.py; sem ele o site funciona na mesma, so sem Elo internacional."""
    if not path or not Path(path).exists():
        return {}, None
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, None
    out = {pid: {"id": e["id"], "elo": e["elo"], "rank": e.get("rank"), "peak": e.get("peak")}
           for pid, e in raw.get("players", {}).items()
           if e.get("status") == "matched" and e.get("id") and e.get("elo") is not None}
    return out, raw.get("updated")


def build(args: argparse.Namespace) -> None:
    conn = db.connect(args.db)
    ev_rows = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM events")}
    matches, rep = curate.load_curated(conn, args, args.date_from, args.date_to)
    for line in rep.lines(args.min_events):
        print(line)
    stats, history = compute(matches)
    if not stats:
        raise SystemExit("Sem partidas no período indicado. Importa dados primeiro (import_matches.py).")

    hidden = load_opt_out(args.opt_out)
    intl, intl_updated = load_intl(args.elorcana)
    names = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM players")}
    real_names = {r["id"]: r["real_name"] for r in conn.execute("SELECT id, real_name FROM players")
                  if r["real_name"]}

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
        **({"intl": intl[s.id]} if s.id in intl else {}),
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

    today = date.fromisoformat(args.today) if getattr(args, "today", None) else date.today()
    awards_data = awards.compute_awards(
        history, hidden, today, awards.load_seasons(getattr(args, "seasons", awards.SEASONS_FILE)),
        getattr(args, "potw_min_matches", awards.WEEK_MIN_MATCHES),
        getattr(args, "season_min_matches", awards.SEASON_MIN_MATCHES),
        getattr(args, "season_min_events", awards.SEASON_MIN_EVENTS))

    ach = achievements.compute(history, {p["id"] for p in players}, events,
                               awards_data["seasons"], awards_data["weeks"])
    for p in players:
        if p["id"] in ach["players"]:
            p["ach"] = ach["players"][p["id"]]

    data = {
        "meta": {"since": fmt_date(args.date_from), "matches": len(matches), "events": len(events),
                 "minGames": args.min_games, "ranked": len(ranked), "contact": args.contact,
                 "intl": sum(1 for p in players if "intl" in p),
                 "intlUpdated": fmt_date(intl_updated) if intl_updated else None},
        "consts": {"start": int(START_RATING), "k1": int(K_PROVISIONAL), "k2": int(K_STABLE),
                   "prov": PROVISIONAL_GAMES},
        "players": players,
        "events": events,
        "awards": awards_data,
        "achievements": {k: ach[k] for k in ("cats", "defs", "holders", "rarity", "total")},
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    demo = ('<p class="demo" data-i18n="demo">Dados de exemplo: os jogadores e os resultados são inventados para testar o site.</p>'
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
    curate.add_arguments(ap)   # regras de curate.py
    ap.add_argument("--opt-out", default="opt_out.txt")
    ap.add_argument("--elorcana", default="raw/elorcana.json",
                    help="Elo internacional obtido por fetch_elorcana.py (opcional)")
    ap.add_argument("--seasons", default=awards.SEASONS_FILE, help="datas de lancamento dos sets (epocas)")
    ap.add_argument("--potw-min-matches", type=int, default=awards.WEEK_MIN_MATCHES,
                    help="partidas minimas numa semana para ser jogador da semana")
    ap.add_argument("--season-min-matches", type=int, default=awards.SEASON_MIN_MATCHES,
                    help="partidas minimas numa epoca para o premio de quem mais evoluiu")
    ap.add_argument("--season-min-events", type=int, default=awards.SEASON_MIN_EVENTS,
                    help="eventos minimos numa epoca para o premio de quem mais evoluiu")
    ap.add_argument("--today", default=None, help=argparse.SUPPRESS)  # so para testes: data de hoje AAAA-MM-DD
    ap.add_argument("--contact", default="")
    ap.add_argument("--demo", action="store_true")
    build(ap.parse_args())


if __name__ == "__main__":
    main()
