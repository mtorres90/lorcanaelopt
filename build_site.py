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
from elo import (K_PROVISIONAL, K_STABLE, PROVISIONAL_GAMES, START_RATING, compute)

esc = html.escape
ANON = "Jogador anónimo"
SITE_TITLE = "Elo Lorcana Portugal"
HERE = Path(__file__).parent


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
        return '<span class="chip chip-w" title="Vitória">V</span>'
    if score == 0.0:
        return '<span class="chip chip-l" title="Derrota">D</span>'
    return '<span class="chip chip-d" title="Empate">E</span>'


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
    nav = [("index.html", "Ranking", "ranking"), ("eventos.html", "Eventos", "eventos"),
           ("sobre.html", "Sobre", "sobre")]
    current = ' aria-current="page"'
    links = "".join(
        f'<a href="{root}{href}"{current if key == active else ""}>{label}</a>'
        for href, label, key in nav
    )
    banner = (
        '<p class="demo">Dados de exemplo: jogadores e resultados inventados para testar o site.</p>'
        if demo else ""
    )
    return f"""<!doctype html>
<html lang="pt-PT">
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
<nav aria-label="Principal">{links}</nav>
</header>
<main class="wrap">
{body}
</main>
<footer class="wrap foot">
<p>Projeto de fãs, sem ligação à Ravensburger nem à Disney. Disney Lorcana é marca dos respetivos titulares.
Resultados obtidos do Ravensburger Play Hub. Atualizado em {updated}.</p>
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

    label = f"Evolução do Elo de {name}: de {fmt_rating(ratings[0])} para {fmt_rating(ratings[-1])}"
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
    events = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM events")}

    def name_of(pid: str) -> str:
        return ANON if pid in hidden else raw_names.get(pid, pid)

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
    (out / "jogadores").mkdir(parents=True, exist_ok=True)
    (out / "style.css").write_text((HERE / "assets" / "style.css").read_text(encoding="utf-8"), encoding="utf-8")
    (out / "app.js").write_text((HERE / "assets" / "app.js").read_text(encoding="utf-8"), encoding="utf-8")

    updated = date.today().strftime("%d/%m/%Y")
    common = {"updated": updated, "demo": args.demo}
    since = fmt_date(args.date_from)

    # --- ranking ---
    def row(s, rank: int | None) -> str:
        hist = per_player[s.id]
        form = "".join(chip(h.score) for h in hist[-5:])
        pos = f"{rank}" if rank else "–"
        cls = "" if rank else ' class="prov"'
        return (
            f'<tr{cls} data-name="{esc(fold(name_of(s.id)))}">'
            f'<td class="num">{pos}</td>'
            f'<td><a href="jogadores/{slugs[s.id]}.html">{esc(name_of(s.id))}</a></td>'
            f'<td class="num elo">{fmt_rating(s.rating)}</td>'
            f'<td class="num">{s.games}</td>'
            f'<td class="num wide">{s.wins}–{s.draws}–{s.losses}</td>'
            f'<td class="wide form">{form}</td></tr>'
        )

    rows = "".join(row(s, rank_of[s.id]) for s in ranked) + "".join(row(s, None) for s in provisional)
    n_events = len({m.event_id for m in matches})
    prov_note = (
        f" Quem tem menos de {args.min_games} partidas aparece no fim, sem posição."
        if provisional else ""
    )
    body = f"""<h1>Ranking Elo de Lorcana em Portugal</h1>
<p class="lead">{len(visible)} jogadores, {len(matches)} partidas e {n_events} eventos desde {since}.{prov_note}</p>
<div class="search">
<label class="sr-only" for="q">Procurar jogador</label>
<input id="q" type="search" placeholder="Procura um jogador" autocomplete="off">
</div>
<div class="tablewrap">
<table class="ranking">
<caption class="sr-only">Classificação por Elo</caption>
<thead><tr><th class="num" scope="col">Pos.</th><th scope="col">Jogador</th><th class="num" scope="col">Elo</th>
<th class="num" scope="col">Jogos</th><th class="num wide" scope="col">V–E–D</th><th class="wide" scope="col">Últimos 5</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</div>
<p id="empty" class="empty" hidden>Nenhum jogador encontrado. Confirma a grafia do nome.</p>"""
    (out / "index.html").write_text(
        layout(f"Ranking · {SITE_TITLE}", body, root="", active="ranking", **common), encoding="utf-8")

    # --- jogadores ---
    for s in visible:
        nm = name_of(s.id)
        hist = per_player[s.id]
        series = [START_RATING] + [h.rating_after for h in hist]
        rank = rank_of.get(s.id)
        if rank:
            standing = f"{rank}.º entre {len(ranked)} jogadores classificados."
        else:
            standing = (f"Ainda sem posição: precisa de {args.min_games} partidas "
                        f"e tem {s.games}.")
        rows_m = []
        for h in reversed(hist):
            ev = events.get(h.event_id, {})
            opp = h.opponent
            opp_cell = (esc(ANON) if opp in hidden or opp not in slugs else
                        f'<a href="{slugs[opp]}.html">{esc(name_of(opp))}</a>')
            rows_m.append(
                f'<tr><td>{fmt_date(h.date)}</td><td>{esc(ev.get("name") or h.event_id)}</td>'
                f'<td class="num">{h.round}</td><td>{opp_cell}</td><td>{chip(h.score)}</td>'
                f'<td class="num">{fmt_rating(h.rating_after)} <span class="delta">({fmt_delta(h.delta)})</span></td></tr>'
            )
        body = f"""<p class="crumb"><a href="../index.html">Ranking</a></p>
<h1>{esc(nm)}</h1>
<div class="hero">
<p class="bignum" aria-label="Elo atual">{fmt_rating(s.rating)}</p>
<p class="hero-text">{standing}<br>
Máximo de {fmt_rating(s.peak)}. {s.wins} vitórias, {s.draws} empates e {s.losses} derrotas ({fmt_percent(s.win_rate)} de aproveitamento).</p>
</div>
<h2>Evolução do Elo</h2>
{rating_chart(nm, series)}
<h2>Partidas</h2>
<div class="tablewrap">
<table class="matches">
<thead><tr><th scope="col">Data</th><th scope="col">Evento</th><th class="num" scope="col">Ronda</th>
<th scope="col">Adversário</th><th scope="col">Resultado</th><th class="num" scope="col">Elo depois</th></tr></thead>
<tbody>
{"".join(rows_m)}
</tbody>
</table>
</div>"""
        (out / "jogadores" / f"{slugs[s.id]}.html").write_text(
            layout(f"{nm} · {SITE_TITLE}", body, root="../", active="ranking", **common), encoding="utf-8")

    # --- eventos ---
    ev_matches = defaultdict(list)
    for m in matches:
        ev_matches[m.event_id].append(m)
    ev_rows = []
    for eid, ms in sorted(ev_matches.items(), key=lambda kv: events[kv[0]]["date"], reverse=True):
        ev = events[eid]
        players = {p for m in ms for p in (m.player_a, m.player_b)}
        where = ", ".join(x for x in (ev.get("store"), ev.get("city")) if x)
        ev_rows.append(
            f'<tr><td>{fmt_date(ev["date"])}</td><td>{esc(ev.get("name") or eid)}</td>'
            f'<td>{esc(where)}</td><td class="num">{len(players)}</td><td class="num">{len(ms)}</td></tr>'
        )
    body = f"""<h1>Eventos</h1>
<p class="lead">Eventos em lojas portuguesas com resultados registados desde {since}.</p>
<div class="tablewrap">
<table class="matches">
<thead><tr><th scope="col">Data</th><th scope="col">Evento</th><th scope="col">Loja</th>
<th class="num" scope="col">Jogadores</th><th class="num" scope="col">Partidas</th></tr></thead>
<tbody>
{"".join(ev_rows)}
</tbody>
</table>
</div>"""
    (out / "eventos.html").write_text(
        layout(f"Eventos · {SITE_TITLE}", body, root="", active="eventos", **common), encoding="utf-8")

    # --- sobre ---
    contact = (f'<a href="mailto:{esc(args.contact)}">{esc(args.contact)}</a>'
               if args.contact else "o contacto do responsável (por definir)")
    body = f"""<h1>Sobre o ranking</h1>
<h2>O que é</h2>
<p>Uma classificação Elo dos jogadores de Disney Lorcana em Portugal, calculada a partir dos resultados
de torneios e ligas registados no Ravensburger Play Hub. Só contam eventos em lojas portuguesas,
realizados desde {since}.</p>
<h2>Como o Elo funciona</h2>
<p>Todos começam com {fmt_rating(START_RATING)} pontos. Depois de cada partida, quem ganha recebe pontos
e quem perde cede-os. Ganhar a um adversário com Elo mais alto vale mais do que ganhar a um mais baixo.
Um empate conta como meia vitória.</p>
<p>Nas primeiras {PROVISIONAL_GAMES} partidas as variações são maiores (K = {K_PROVISIONAL:.0f}),
para o Elo chegar depressa ao nível certo. Depois passa a K = {K_STABLE:.0f}.
As partidas de uma mesma ronda são calculadas com o Elo que cada jogador tinha antes dessa ronda.
Byes não contam.</p>
<h2>Quem aparece com posição</h2>
<p>Jogadores com pelo menos {args.min_games} partidas. Os outros aparecem no fim da tabela, sem posição.</p>
<h2>Privacidade</h2>
<p>Mostramos apenas o nome que o Play Hub disponibiliza publicamente. Se preferires não aparecer,
contacta {contact} e o teu perfil deixa de ser mostrado. As tuas partidas continuam a contar para o Elo
dos adversários, mas o teu nome é substituído por “{ANON}”.</p>"""
    (out / "sobre.html").write_text(
        layout(f"Sobre · {SITE_TITLE}", body, root="", active="sobre", **common), encoding="utf-8")

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
