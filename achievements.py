"""Conquistas de cada jogador (mostradas na pagina do jogador).

Sai tudo do historico de Elo (elo.HistoryRow) e dos premios (awards.py), por isso segue as mesmas
regras do ranking (curate.py). Cada jogador e percorrido uma vez, por ordem cronologica, o que
da tambem a data em que cada nivel foi conseguido.

Ha conquistas com niveis (ex.: jogar em 3 / 5 / 10 / 15 lojas) e conquistas de nivel unico.
Uma conquista, uma vez conseguida, fica para sempre.

Raridade: automatica, pela percentagem de jogadores que tem esse nivel (como no EloShowdown).
    >= 40 % comum, >= 15 % incomum, >= 5 % rara, >= 1 % epica, abaixo disso lendaria.

Os textos (nomes e descricoes, em portugues e ingles) estao em assets/web_app.js, com a chave
`ach_<id>_n` (nome) e `ach_<id>_d` (descricao, com {n} = o valor do nivel).
"""
from __future__ import annotations

import math
from collections import defaultdict

from elo import START_RATING

CATEGORIES = ["location", "participation", "streak", "rivalry", "elo", "events", "awards", "loyalty"]

_R = int(START_RATING)
DEFS: list[dict] = [
    {"id": "stores", "cat": "location", "levels": [3, 5, 10, 15]},              # lojas diferentes
    {"id": "home", "cat": "location", "levels": [20, 40]},                       # partidas na mesma loja
    {"id": "cities", "cat": "location", "levels": [3, 5, 8]},                    # cidades diferentes
    {"id": "matches", "cat": "participation", "levels": [10, 25, 50, 100, 200]},
    {"id": "events", "cat": "participation", "levels": [5, 10, 20, 30, 50]},
    {"id": "wins", "cat": "participation", "levels": [10, 25, 50, 100]},
    {"id": "streak", "cat": "streak", "levels": [3, 5, 8, 10]},                  # vitorias seguidas
    {"id": "opponents", "cat": "rivalry", "levels": [10, 25, 50]},               # adversarios diferentes
    {"id": "rival", "cat": "rivalry", "levels": [3, 5, 8]},                      # partidas contra o mesmo
    {"id": "heartbreaker", "cat": "rivalry", "levels": [1]},                     # ganhar 3x ao mesmo
    {"id": "slayer", "cat": "rivalry", "levels": [1]},                           # ganhar a quem te ganhou 3x
    {"id": "peak", "cat": "elo", "levels": [_R + 50, _R + 100, _R + 150, _R + 200, _R + 250], "base": _R},
    {"id": "climb", "cat": "elo", "levels": [50, 100, 150]},                     # Elo ganho numa epoca
    {"id": "goliath", "cat": "elo", "levels": [100, 200, 300]},                  # vencer alguem tantos pontos acima
    {"id": "undefeated", "cat": "events", "levels": [1, 3]},                     # eventos sem perder
    {"id": "debut", "cat": "events", "levels": [1]},                             # primeiro evento sem perder
    {"id": "bigroom", "cat": "events", "levels": [1]},                           # evento com 32+ jogadores
    {"id": "comeback", "cat": "events", "levels": [1]},                          # ganhar depois de 3 derrotas
    {"id": "rubber", "cat": "events", "levels": [1]},                            # ganhar na ultima ronda
    {"id": "potw", "cat": "awards", "levels": [1, 2, 4]},
    {"id": "improved", "cat": "awards", "levels": [1]},
    {"id": "podium", "cat": "awards", "levels": [1]},
    {"id": "founder", "cat": "loyalty", "levels": [1]},                          # jogou a primeira epoca
    {"id": "seasons", "cat": "loyalty", "levels": [3, 5]},                       # epocas diferentes
]
LEVELS = {d["id"]: d["levels"] for d in DEFS}

BIG_EVENT_PLAYERS = 32
UNDEFEATED_MIN_MATCHES = 3   # eventos com menos partidas nao contam como "sem perder"
CLIMB_MIN_MATCHES = 15       # partidas na epoca para o Elo ganho contar
COMEBACK_LOSSES = 3
GRUDGE_LOSSES = 3            # derrotas anteriores para o "ganhar a quem te ganhou"
HEARTBREAKER_WINS = 3

RARITY = [(40.0, "common"), (15.0, "uncommon"), (5.0, "rare"), (1.0, "epic"), (0.0, "legendary")]


def rarity_of(pct: float) -> str:
    for floor, name in RARITY:
        if pct >= floor:
            return name
    return "legendary"


def season_index(date: str, starts: list[str]) -> int | None:
    idx = None
    for i, s in enumerate(starts):
        if date >= s:
            idx = i
    return idx


class _Progress:
    """Valor actual e data de cada nivel, por conquista."""

    def __init__(self) -> None:
        self.value = {aid: 0 for aid in LEVELS}
        self.dates: dict[str, list[str | None]] = {aid: [None] * len(lv) for aid, lv in LEVELS.items()}

    def bump(self, aid: str, value: float, date: str) -> None:
        if value > self.value[aid]:
            self.value[aid] = value
        for i, threshold in enumerate(LEVELS[aid]):
            if self.value[aid] >= threshold and self.dates[aid][i] is None:
                self.dates[aid][i] = date

    def result(self) -> dict[str, list]:
        out = {}
        for aid in LEVELS:
            earned = [d for d in self.dates[aid] if d]
            if self.value[aid] > 0 or earned:
                out[aid] = [self.value[aid], len(earned), earned[-1] if earned else None]
        return out


def _walk(rows, events: dict, event_max: dict, starts: list[str], pr: _Progress) -> None:
    """Percorre as partidas de um jogador por ordem cronologica."""
    stores, cities, evs, seasons_seen = set(), set(), set(), set()
    store_n: dict[str, int] = defaultdict(int)
    opp_n: dict[str, int] = defaultdict(int)
    opp_w: dict[str, int] = defaultdict(int)
    opp_l: dict[str, int] = defaultdict(int)
    played = wins = streak = loss_run = undefeated = 0
    cur_event, ev_rows = None, []
    first_event = rows[0].event_id if rows else None
    cur_season, net, in_season, best_net = None, 0.0, 0, 0.0

    def finish_event() -> None:
        nonlocal undefeated
        if len(ev_rows) >= UNDEFEATED_MIN_MATCHES and all(r.score == 1.0 for r in ev_rows):
            undefeated += 1
            pr.bump("undefeated", undefeated, ev_rows[-1].date)
            if ev_rows[0].event_id == first_event:
                pr.bump("debut", 1, ev_rows[-1].date)

    for r in rows:
        if r.event_id != cur_event:
            if ev_rows:
                finish_event()
            cur_event, ev_rows = r.event_id, []
        ev_rows.append(r)
        ev = events.get(r.event_id) or {}
        won = r.score == 1.0

        played += 1
        pr.bump("matches", played, r.date)
        evs.add(r.event_id)
        pr.bump("events", len(evs), r.date)
        if won:
            wins += 1
            pr.bump("wins", wins, r.date)

        store, city = ev.get("store"), ev.get("city")
        if store:
            stores.add(store)
            store_n[store] += 1
            pr.bump("stores", len(stores), r.date)
            pr.bump("home", store_n[store], r.date)
        if city:
            cities.add(city)
            pr.bump("cities", len(cities), r.date)
        if (ev.get("players") or 0) >= BIG_EVENT_PLAYERS:
            pr.bump("bigroom", 1, r.date)

        streak = streak + 1 if won else 0
        pr.bump("streak", streak, r.date)
        if won and loss_run >= COMEBACK_LOSSES:
            pr.bump("comeback", 1, r.date)
        loss_run = loss_run + 1 if r.score == 0.0 else 0

        if r.opponent:
            opp_n[r.opponent] += 1
            pr.bump("opponents", len(opp_n), r.date)
            pr.bump("rival", opp_n[r.opponent], r.date)
            if won:
                if opp_l[r.opponent] >= GRUDGE_LOSSES:
                    pr.bump("slayer", 1, r.date)
                opp_w[r.opponent] += 1
                if opp_w[r.opponent] >= HEARTBREAKER_WINS:
                    pr.bump("heartbreaker", 1, r.date)
            elif r.score == 0.0:
                opp_l[r.opponent] += 1
        if won and r.opponent_rating > r.rating_before:      # a maior vitoria contra alguem acima (Elo no momento)
            pr.bump("goliath", math.floor(r.opponent_rating - r.rating_before), r.date)
        if won and event_max.get(r.event_id, 0) >= 3 and r.round == event_max[r.event_id]:
            pr.bump("rubber", 1, r.date)

        pr.bump("peak", math.floor(r.rating_after), r.date)

        s = season_index(r.date, starts)
        if s != cur_season:
            cur_season, net, in_season = s, 0.0, 0
        if s is not None:
            net += r.rating_after - r.rating_before
            in_season += 1
            if in_season >= CLIMB_MIN_MATCHES:
                best_net = max(best_net, net)
                pr.bump("climb", math.floor(best_net), r.date)
            seasons_seen.add(s)
            pr.bump("seasons", len(seasons_seen), r.date)
            if s == 0:
                pr.bump("founder", 1, r.date)
    if ev_rows:
        finish_event()


def _award_progress(pid: str, weeks: list[dict], seasons: list[dict], pr: _Progress) -> None:
    for k, day in enumerate(sorted(w["end"] for w in weeks if w["final"] and w["p"] == pid), 1):
        pr.bump("potw", k, day)
    for s in seasons:
        if not (s["done"] and s["top"]):
            continue
        if s["top"][0]["p"] == pid:
            pr.bump("improved", 1, s["through"])
        if any(t["p"] == pid for t in s["top"][:3]):
            pr.bump("podium", 1, s["through"])


def compute(history, include: set[str], events: dict, seasons: list[dict], weeks: list[dict]) -> dict:
    """history: HistoryRow (regras do ranking); include: jogadores visiveis; events: {id: store, city, players};
    seasons / weeks: as listas de awards.compute_awards."""
    event_max: dict[str, int] = {}
    rows_by: dict[str, list] = defaultdict(list)
    for h in history:
        if h.round > event_max.get(h.event_id, 0):
            event_max[h.event_id] = h.round
        if h.player in include:
            rows_by[h.player].append(h)
    starts = sorted(s["start"] for s in seasons)

    players: dict[str, dict] = {}
    for pid in include:
        pr = _Progress()
        _walk(rows_by.get(pid, []), events, event_max, starts, pr)
        _award_progress(pid, weeks, seasons, pr)
        res = pr.result()
        if res:
            players[pid] = res

    total = len(include)
    holders = {aid: [sum(1 for e in players.values() if aid in e and e[aid][1] > i) for i in range(len(lv))]
               for aid, lv in LEVELS.items()}
    rarity = {aid: [rarity_of(n / total * 100 if total else 0.0) for n in counts] for aid, counts in holders.items()}
    return {"cats": CATEGORIES, "defs": DEFS, "players": players, "holders": holders, "rarity": rarity, "total": total}
