#!/usr/bin/env python3
"""Gera o site estatico do ranking Elo de Lorcana em Portugal.

Le a base de dados, calcula o Elo e escreve HTML em --out.
Uso:
  python build_site.py --db data/lorcana.db --out site --from 2025-09-05
"""
from __future__ import annotations

import argparse
import html
import re
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

import db
from elo import (K_PROVISIONAL, K_STABLE, PROVISIONAL_GAMES, START_RATING,
                  compute, extra_stats, rival_labels)

esc = html.escape
ANON = "Anonymous player"
SITE_TITLE = "Lorcana Portugal Elo"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
STYLE_CSS = (ASSETS_DIR / "style.css").read_text(encoding="utf-8")
APP_JS = (ASSETS_DIR / "app.js").read_text(encoding="utf-8")


# ---------- utilitarios ----------

def slugify(pid: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", pid).strip("-") or "jogador"


def fold(text: str) -> str:
    """Minusculas e sem acentos, para a pesquisa."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def fmt_rating(x: float) -> str:
    return f"{x:.0f}"


def fmt_delta(x: float) -> str:
    if round(x) == 0:
        return "0"
    return f"{x:+.0f}".replace("-", "−")


def fmt_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"


def fmt_percent(x: float) -> str:
    return f"{x * 100:.0f} %"


def chip(score: float) -> str:
    if score == 1.0:
        return '<span class="chip chip-w" title="Win">W</span>'
    if score == 0.0:
        return '<span class="chip chip-l" title="Loss">L</span>'
    return '<span class="chip chip-d" title="Draw">D</span>'


def stat_tile(label: str, value, sub: str | None = None) -> str:
    sub_html = f'<span class="stat-sub">{sub}</span>' if sub else ""
    return (f'<div class="stat-tile"><span class="stat-label">{label}</span>'
            f'<span class="stat-value">{value}</span>{sub_html}</div>')


def stat_grid(s, extra: dict) -> str:
    fav_pct = f"{round(extra['fav_wins'] / extra['fav_games'] * 100)} %" if extra["fav_games"] else "–"
    dog_pct = f"{round(extra['dog_wins'] / extra['dog_games'] * 100)} %" if extra["dog_games"] else "–"
    tiles = "".join([
        stat_tile("Peak", fmt_rating(s.peak)),
        stat_tile("Low", fmt_rating(extra["low"])),
        stat_tile("Events", extra["events"]),
        stat_tile("Best win streak", extra["best_win_streak"]),
        stat_tile("Worst loss streak", extra["best_loss_streak"]),
        stat_tile("Biggest single-match gain", fmt_delta(extra["best_gain"])),
        stat_tile("Biggest single-match drop", fmt_delta(extra["worst_loss"])),
        stat_tile("As favorite", fav_pct, f"{extra['fav_games']} matches"),
        stat_tile("As underdog", dog_pct, f"{extra['dog_games']} matches"),
    ])
    return f'<div class="stat-grid">{tiles}</div>'


def event_url(eid: str) -> str:
    from urllib.parse import quote
    return f"https://tcg.ravensburgerplay.com/events/{quote(str(eid))}"


def event_link(eid: str, name: str) -> str:
    return f'<a href="{event_url(eid)}" target="_blank" rel="noopener noreferrer" title="{esc(name)}">{esc(name)}</a>'


def h2h_section(extra: dict, name_of, slugs: dict[str, str]) -> str:
    h2h = extra["h2h"]
    if not h2h:
        return ""
    rows = []
    for o in h2h:
        oid = o["id"]
        cell = (f'<a href="{slugs[oid]}.html">{esc(name_of(oid))}</a>'
                if oid in slugs else esc(name_of(oid)))
        pct = round((o["wins"] + 0.5 * o["draws"]) / o["games"] * 100)
        tag = ""
        if oid == extra["nemesis"]:
            tag = ' <span class="tag tag-l">toughest rival</span>'
        elif oid == extra["victim"]:
            tag = ' <span class="tag tag-w">favorable opponent</span>'
        rows.append(
            f'<tr><td>{cell}{tag}</td><td class="num">{o["games"]}</td>'
            f'<td class="num wide">{o["wins"]}–{o["draws"]}–{o["losses"]}</td>'
            f'<td class="num">{pct} %</td></tr>'
        )
    return f"""<h2>Head-to-head</h2>
<div class="tablewrap">
<table class="matches">
<thead><tr><th scope="col">Opponent</th><th class="num" scope="col">Matches</th>
<th class="num wide" scope="col">W–D–L</th><th class="num" scope="col">Win %</th></tr></thead>
<tbody>
{"".join(rows)}
</tbody>
</table>
</div>"""


def events_section(hist: list, events: dict) -> str:
    by_ev: dict[str, dict] = {}
    order: list[str] = []
    for h in hist:
        eid = h.event_id
        if eid not in by_ev:
            by_ev[eid] = {"date": h.date, "w": 0, "d": 0, "l": 0, "rounds": 0,
                          "start": h.rating_before, "end": h.rating_after}
            order.append(eid)
        e = by_ev[eid]
        e["rounds"] += 1
        e["end"] = h.rating_after
        if h.score == 1.0:
            e["w"] += 1
        elif h.score == 0.0:
            e["l"] += 1
        else:
            e["d"] += 1
    if not order:
        return ""
    rows = []
    for eid in reversed(order):
        e = by_ev[eid]
        ev_name = events.get(eid, {}).get("name") or eid
        rows.append(
            f'<tr><td>{fmt_date(e["date"])}</td><td>{event_link(eid, ev_name)}</td>'
            f'<td class="num">{e["rounds"]}</td><td class="num wide">{e["w"]}–{e["d"]}–{e["l"]}</td>'
            f'<td class="num">{fmt_delta(e["end"] - e["start"])}</td></tr>'
        )
    return f"""<h2>Events</h2>
<div class="tablewrap">
<table class="matches">
<thead><tr><th scope="col">Date</th><th scope="col">Event</th><th class="num" scope="col">Rounds</th>
<th class="num wide" scope="col">W–D–L</th><th class="num" scope="col">Change</th></tr></thead>
<tbody>
{"".join(rows)}
</tbody>
</table>
</div>"""


def ordinal(n: int) -> str:
    r = n % 100
    if 11 <= r <= 13:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def load_opt_out(path: str | None) -> set[str]:
    if not path or not Path(path).exists():
        return set()
    ids = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            ids.add(line)
    return ids


# ---------- estrutura comum ----------

def layout(title: str, body: str, *, root: str, active: str, updated: str, demo: bool) -> str:
    nav = [("index.html", "Ranking", "ranking"), ("events.html", "Events", "events"),
           ("about.html", "About", "about")]
    current = ' aria-current="page"'
    links = "".join(
        f'<a href="{root}{href}"{current if key == active else ""}>{label}</a>'
        for href, label, key in nav
    )
    banner = (
        '<p class="demo">Sample data: players and results are made up to test the site.</p>'
        if demo else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&amp;family=Public+Sans:wght@400;600&amp;display=swap">
<link rel="stylesheet" href="{root}style.css">
</head>
<body>
<div class="inkband" aria-hidden="true"></div>
{banner}<header class="wrap top">
<a class="brand" href="{root}index.html">{SITE_TITLE}</a>
<nav aria-label="Main">{links}</nav>
</header>
<main class="wrap">
{body}
</main>
<footer class="wrap foot">
<p>Fan project, not affiliated with Ravensburger or Disney. Disney Lorcana is a trademark of its respective owners.
Results sourced from the Ravensburger Play Hub. Updated on {updated}.</p>
</footer>
<script src="{root}app.js" defer></script>
</body>
</html>
"""


# ---------- paginas ----------

def rating_chart(name: str, ratings: list[float]) -> str:
    w, h = 640, 190
    pad_l, pad_r, pad_t, pad_b = 44, 14, 14, 16
    lo = min(ratings + [START_RATING]) - 10
    hi = max(ratings + [START_RATING]) + 10
    if hi - lo < 60:
        mid = (hi + lo) / 2
        lo, hi = mid - 30, mid + 30
    n = len(ratings)

    def x(i: int) -> float:
        return pad_l + (w - pad_l - pad_r) * (i / (n - 1) if n > 1 else 0.5)

    def y(v: float) -> float:
        return pad_t + (h - pad_t - pad_b) * (hi - v) / (hi - lo)

    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(ratings))
    base = y(START_RATING)

    def tick(v: float) -> str:
        # so mostra o extremo se nao colidir com a etiqueta da linha base
        if abs(y(v) - base) < 16:
            return ""
        return (f'<text class="chart-tick" x="{pad_l - 6}" y="{y(v) + 4:.1f}" '
                f'text-anchor="end">{fmt_rating(v)}</text>')

    label = f"Elo progression for {name}: from {fmt_rating(ratings[0])} to {fmt_rating(ratings[-1])}"
    return f"""<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">
<line class="chart-base" x1="{pad_l}" x2="{w - pad_r}" y1="{base:.1f}" y2="{base:.1f}"/>
<text class="chart-tick" x="{pad_l - 6}" y="{base + 4:.1f}" text-anchor="end">{fmt_rating(START_RATING)}</text>
{tick(hi)}{tick(lo)}
<polyline class="chart-line" points="{pts}"/>
<circle class="chart-dot" cx="{x(n - 1):.1f}" cy="{y(ratings[-1]):.1f}" r="4"/>
</svg>"""


def build(args: argparse.Namespace) -> None:
    conn = db.connect(args.db)
    matches = db.load_matches(conn, args.date_from, args.date_to)
    stats, history = compute(matches)
    if not stats:
        raise SystemExit("Sem partidas no período indicado. Importa dados primeiro (import_matches.py).")

    hidden = load_opt_out(args.opt_out)
    raw_names = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM players")}
    raw_real_names = {r["id"]: r["real_name"] for r in conn.execute("SELECT id, real_name FROM players")
                       if r["real_name"]}
    events = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM events")}

    def name_of(pid: str) -> str:
        return ANON if pid in hidden else raw_names.get(pid, pid)

    def real_name_of(pid: str) -> str | None:
        if pid in hidden:
            return None
        rn = raw_real_names.get(pid)
        return rn if rn and fold(rn) != fold(raw_names.get(pid, "")) else None

    visible = [s for s in stats.values() if s.id not in hidden]
    ranked = sorted((s for s in visible if s.games >= args.min_games),
                    key=lambda s: (-s.rating, -s.games, fold(name_of(s.id))))
    provisional = sorted((s for s in visible if s.games < args.min_games),
                         key=lambda s: (-s.games, fold(name_of(s.id))))
    rank_of = {s.id: i + 1 for i, s in enumerate(ranked)}

    slugs: dict[str, str] = {}
    used: set[str] = set()
    for s in sorted(visible, key=lambda s: s.id):
        base = slugify(s.id)
        slug, i = base, 2
        while slug in used:
            slug, i = f"{base}-{i}", i + 1
        used.add(slug)
        slugs[s.id] = slug

    per_player = defaultdict(list)
    for h in history:
        per_player[h.player].append(h)

    out = Path(args.out)
    (out / "players").mkdir(parents=True, exist_ok=True)
    (out / "style.css").write_text(STYLE_CSS, encoding="utf-8")
    (out / "app.js").write_text(APP_JS, encoding="utf-8")

    updated = date.today().strftime("%d/%m/%Y")
    common = {"updated": updated, "demo": args.demo}
    since = fmt_date(args.date_from)

    # --- ranking ---
    def row(s, rank: int | None) -> str:
        hist = per_player[s.id]
        form = "".join(chip(h.score) for h in hist[-5:])
        pos = f"{rank}" if rank else "–"
        cls = "" if rank else ' class="prov"'
        rn = real_name_of(s.id)
        title_attr = f' title="{esc(rn)}"' if rn else ""
        return (
            f'<tr{cls} data-name="{esc(fold(name_of(s.id)))}">'
            f'<td class="num">{pos}</td>'
            f'<td><a href="players/{slugs[s.id]}.html"{title_attr}>{esc(name_of(s.id))}</a></td>'
            f'<td class="num elo">{fmt_rating(s.rating)}</td>'
            f'<td class="num">{s.games}</td>'
            f'<td class="num wide">{s.wins}–{s.draws}–{s.losses}</td>'
            f'<td class="wide form">{form}</td></tr>'
        )

    rows = "".join(row(s, rank_of[s.id]) for s in ranked) + "".join(row(s, None) for s in provisional)
    n_events = len({m.event_id for m in matches})
    prov_note = (
        f" Players with fewer than {args.min_games} matches appear at the bottom, unranked."
        if provisional else ""
    )
    body = f"""<h1>Lorcana Portugal Elo Ranking</h1>
<p class="lead">{len(visible)} players, {len(matches)} matches and {n_events} events since {since}.{prov_note}</p>
<div class="search">
<label class="sr-only" for="q">Search for a player</label>
<input id="q" type="search" placeholder="Search for a player" autocomplete="off">
</div>
<div class="tablewrap">
<table class="ranking">
<caption class="sr-only">Elo ranking</caption>
<thead><tr><th class="num" scope="col">Rank</th><th scope="col">Player</th><th class="num" scope="col">Elo</th>
<th class="num" scope="col">Matches</th><th class="num wide" scope="col">W–D–L</th><th class="wide" scope="col">Last 5</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</div>
<p id="empty" class="empty" hidden>No player found. Check the spelling of the name.</p>
<nav id="pager" class="pager" aria-label="Ranking pages"></nav>"""
    (out / "index.html").write_text(
        layout(f"Ranking · {SITE_TITLE}", body, root="", active="ranking", **common), encoding="utf-8")

    # --- players ---
    for s in visible:
        nm = name_of(s.id)
        hist = per_player[s.id]
        series = [START_RATING] + [h.rating_after for h in hist]
        rank = rank_of.get(s.id)
        if rank:
            standing = f"{ordinal(rank)} out of {len(ranked)} ranked players."
        else:
            standing = (f"Not yet ranked: needs {args.min_games} matches, "
                        f"has {s.games}.")
        rows_m = []
        for h in reversed(hist):
            ev = events.get(h.event_id, {})
            opp = h.opponent
            opp_cell = (esc(ANON) if opp in hidden or opp not in slugs else
                        f'<a href="{slugs[opp]}.html">{esc(name_of(opp))}</a>')
            ev_name = ev.get("name") or h.event_id
            rows_m.append(
                f'<tr><td>{fmt_date(h.date)}</td><td>{event_link(h.event_id, ev_name)}</td>'
                f'<td class="num">{h.round}</td><td>{opp_cell}</td><td>{chip(h.score)}</td>'
                f'<td class="num">{fmt_rating(h.rating_after)} <span class="delta">({fmt_delta(h.delta)})</span></td></tr>'
            )
        extra = extra_stats(hist, hidden)
        extra["nemesis"], extra["victim"] = rival_labels(extra["h2h"])
        rn = real_name_of(s.id)
        real_name_line = f'<p class="crumb-sub">{esc(rn)}</p>' if rn else ""
        body = f"""<p class="crumb"><a href="../index.html">Ranking</a></p>
<h1>{esc(nm)}</h1>
{real_name_line}
<div class="hero">
<p class="bignum" aria-label="Current Elo">{fmt_rating(s.rating)}</p>
<p class="hero-text">{standing}<br>
Peak of {fmt_rating(s.peak)}. {s.wins} wins, {s.draws} draws and {s.losses} losses ({fmt_percent(s.win_rate)} win rate).</p>
</div>
<h2>Elo progression</h2>
{rating_chart(nm, series)}
{stat_grid(s, extra)}
{h2h_section(extra, name_of, slugs)}
{events_section(hist, events)}
<h2>Matches</h2>
<div class="tablewrap">
<table class="matches">
<thead><tr><th scope="col">Date</th><th scope="col">Event</th><th class="num" scope="col">Round</th>
<th scope="col">Opponent</th><th scope="col">Result</th><th class="num" scope="col">Elo after</th></tr></thead>
<tbody>
{"".join(rows_m)}
</tbody>
</table>
</div>"""
        (out / "players" / f"{slugs[s.id]}.html").write_text(
            layout(f"{nm} · {SITE_TITLE}", body, root="../", active="ranking", **common), encoding="utf-8")

    # --- events ---
    ev_matches = defaultdict(list)
    for m in matches:
        ev_matches[m.event_id].append(m)
    ev_rows = []
    for eid, ms in sorted(ev_matches.items(), key=lambda kv: events[kv[0]]["date"], reverse=True):
        ev = events[eid]
        players = {p for m in ms for p in (m.player_a, m.player_b)}
        where = ", ".join(x for x in (ev.get("store"), ev.get("city")) if x)
        ev_name = ev.get("name") or eid
        ev_rows.append(
            f'<tr><td>{fmt_date(ev["date"])}</td><td>{event_link(eid, ev_name)}</td>'
            f'<td>{esc(where)}</td><td class="num">{len(players)}</td><td class="num">{len(ms)}</td></tr>'
        )
    body = f"""<h1>Events</h1>
<p class="lead">Events at Portuguese stores with results recorded since {since}.</p>
<div class="tablewrap">
<table class="matches">
<thead><tr><th scope="col">Date</th><th scope="col">Event</th><th scope="col">Store</th>
<th class="num" scope="col">Players</th><th class="num" scope="col">Matches</th></tr></thead>
<tbody>
{"".join(ev_rows)}
</tbody>
</table>
</div>"""
    (out / "events.html").write_text(
        layout(f"Events · {SITE_TITLE}", body, root="", active="events", **common), encoding="utf-8")

    # --- about ---
    contact = (f'<a href="mailto:{esc(args.contact)}">{esc(args.contact)}</a>'
               if args.contact else "the site contact (to be set)")
    body = f"""<h1>About the ranking</h1>
<h2>What this is</h2>
<p>An Elo ranking of Disney Lorcana players in Portugal, calculated from tournament and league results
recorded on the Ravensburger Play Hub. Only events at Portuguese stores count, held since {since}.</p>
<h2>How Elo works</h2>
<p>Everyone starts with {fmt_rating(START_RATING)} points. After each match, the winner gains points
and the loser loses them. Beating a higher-rated opponent is worth more than beating a lower-rated one.
A draw counts as half a win.</p>
<p>In the first {PROVISIONAL_GAMES} matches, swings are bigger (K = {K_PROVISIONAL:.0f}),
so Elo reaches the right level quickly. After that it switches to K = {K_STABLE:.0f}.
Matches within the same round are calculated using each player's Elo from before that round.
Byes don't count.</p>
<p>Bigger events also count for more: matches at an event with 17–32 players move rating 1.25×
as much as usual, and events with 33 or more players move it 1.5×. Smaller events use the normal rate.</p>
<h2>Who gets a rank</h2>
<p>Players with at least {args.min_games} matches. Others appear at the bottom of the table, unranked.</p>
<h2>Privacy</h2>
<p>We only show the name that the Play Hub makes publicly available. If you'd rather not appear,
contact {contact} and your profile will stop being shown. Your matches still count toward your
opponents' Elo, but your name is replaced with "{ANON}".</p>"""
    (out / "about.html").write_text(
        layout(f"About · {SITE_TITLE}", body, root="", active="about", **common), encoding="utf-8")

    print(f"Site gerado em {out}/: {len(visible)} jogadores, {len(matches)} partidas, {n_events} eventos.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/lorcana.db")
    ap.add_argument("--out", default="site")
    ap.add_argument("--from", dest="date_from", default="2025-09-05")
    ap.add_argument("--to", dest="date_to", default=None)
    ap.add_argument("--min-games", type=int, default=5, help="partidas mínimas para ter posição")
    ap.add_argument("--opt-out", default="opt_out.txt",
                    help="ficheiro com ids de jogadores a ocultar (um por linha)")
    ap.add_argument("--contact", default="", help="email para pedidos de remoção")
    ap.add_argument("--demo", action="store_true", help="mostra aviso de dados de exemplo")
    build(ap.parse_args())


if __name__ == "__main__":
    main()
