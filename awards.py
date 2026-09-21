"""Premios: jogador da semana e jogador que mais evoluiu por epoca.

Tudo sai do historico de Elo (elo.HistoryRow), por isso segue as mesmas regras do ranking
(curate.py) e usa o Elo real de cada partida.

Jogador da semana
- Semana = segunda a domingo. Ganha quem mais Elo somou nessa semana (soma das variacoes).
- Tem de ter jogado pelo menos WEEK_MIN_MATCHES partidas nessa semana e ter ganho Elo (> 0).
  Semanas em que ninguem cumpre isto ficam sem jogador da semana.
- Desempate: mais partidas, depois Elo mais alto no fim da semana.
- A semana em curso aparece como provisoria (final = False) e nao conta para os titulos.

Jogador que mais evoluiu (por epoca)
- Uma epoca comeca no dia de lancamento de cada set (seasons.txt) e dura ate ao lancamento do
  seguinte. Quando o set seguinte sai, a epoca fecha e o premio e atribuido.
- Evolucao = Elo no fim da epoca menos o Elo antes da primeira partida da epoca. Quem entra a meio
  da epoca parte do Elo inicial. Tem de ter SEASON_MIN_MATCHES partidas e SEASON_MIN_EVENTS eventos
  na epoca e ter ganho Elo. A epoca em curso mostra quem vai na frente, sem premio ainda.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

WEEK_MIN_MATCHES = 4
SEASON_MIN_MATCHES = 15
SEASON_MIN_EVENTS = 3
SEASONS_FILE = "seasons.txt"
TOP_TITLES = 10
PODIUM = 3


def _d(iso: str) -> date:
    y, m, d = iso.split("-")
    return date(int(y), int(m), int(d))


def week_start(iso: str) -> str:
    d = _d(iso)
    return (d - timedelta(days=d.weekday())).isoformat()


def week_end(start_iso: str) -> str:
    return (_d(start_iso) + timedelta(days=6)).isoformat()


def _best(rows_by_player: dict[str, list], min_matches: int, min_events: int = 0):
    """Ordena candidatos por (ganho, partidas, Elo final, id), do melhor para o pior."""
    out = []
    for pid, rows in rows_by_player.items():
        rows = sorted(rows, key=lambda r: r.date)      # estavel: mantem a ordem dentro do dia
        events = {r.event_id for r in rows}
        gain = sum(r.rating_after - r.rating_before for r in rows)
        if len(rows) < min_matches or len(events) < min_events or gain <= 0:
            continue
        out.append({"p": pid, "gain": round(gain, 1), "n": len(rows), "ev": len(events),
                    "from": round(rows[0].rating_before, 1), "to": round(rows[-1].rating_after, 1),
                    "_key": (round(gain, 6), len(rows), rows[-1].rating_after, pid)})
    out.sort(key=lambda c: c["_key"], reverse=True)
    for c in out:
        del c["_key"]
    return out


def weekly_winners(history, exclude: set[str], today: date, min_matches: int = WEEK_MIN_MATCHES) -> list[dict]:
    """Um dicionario por semana com jogador da semana, da mais antiga para a mais recente."""
    weeks: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for h in history:
        if h.player not in exclude:
            weeks[week_start(h.date)][h.player].append(h)
    out = []
    for start in sorted(weeks):
        cands = _best(weeks[start], min_matches)
        if not cands:
            continue
        w = cands[0]
        end = week_end(start)
        out.append({"start": start, "end": end, "p": w["p"], "gain": w["gain"], "n": w["n"], "ev": w["ev"],
                    "elo": w["to"], "final": _d(end) < today})
    return out


def title_leaderboard(weeks: list[dict], limit: int = TOP_TITLES) -> list[dict]:
    """Quem mais vezes foi jogador da semana (so semanas fechadas)."""
    titles: dict[str, list[str]] = defaultdict(list)
    for w in weeks:
        if w["final"]:
            titles[w["p"]].append(w["start"])
    rows = [{"p": p, "titles": len(s), "last": max(s)} for p, s in titles.items()]
    rows.sort(key=lambda r: (r["titles"], r["last"], r["p"]), reverse=True)
    return rows[:limit]


def load_seasons(path: str | None) -> list[tuple[str, str]]:
    """[(data de inicio, nome)] ordenado. Linhas: `AAAA-MM-DD  Nome do set`."""
    out: list[tuple[str, str]] = []
    if not path or not Path(path).exists():
        return out
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        start, _, name = line.partition(" ")
        try:
            _d(start)
        except ValueError:
            continue
        out.append((start, name.strip() or start))
    return sorted(out)


def season_awards(history, seasons: list[tuple[str, str]], exclude: set[str], today: date,
                  min_matches: int = SEASON_MIN_MATCHES, min_events: int = SEASON_MIN_EVENTS) -> list[dict]:
    """Uma entrada por epoca ja comecada, da mais antiga para a mais recente."""
    out = []
    for i, (start, name) in enumerate(seasons):
        if _d(start) > today:
            continue
        end = seasons[i + 1][0] if i + 1 < len(seasons) else None
        rows: dict[str, list] = defaultdict(list)
        for h in history:
            if h.player not in exclude and h.date >= start and (end is None or h.date < end):
                rows[h.player].append(h)
        cands = _best(rows, min_matches, min_events)
        done = end is not None and _d(end) <= today
        through = (_d(end) - timedelta(days=1)).isoformat() if done else None   # ultimo dia da epoca
        out.append({"start": start, "end": end, "through": through, "name": name, "done": done,
                    "top": cands[:PODIUM], "players": len(rows)})
    return out


def compute_awards(history, exclude: set[str], today: date, seasons: list[tuple[str, str]],
                   week_min: int = WEEK_MIN_MATCHES, season_min_matches: int = SEASON_MIN_MATCHES,
                   season_min_events: int = SEASON_MIN_EVENTS) -> dict:
    weeks = weekly_winners(history, exclude, today, week_min)
    return {
        "weeks": weeks,
        "top": title_leaderboard(weeks),
        "seasons": season_awards(history, seasons, exclude, today, season_min_matches, season_min_events),
        "rules": {"weekMin": week_min, "seasonMinMatches": season_min_matches,
                  "seasonMinEvents": season_min_events},
    }
