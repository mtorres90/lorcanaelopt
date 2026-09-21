"""Regras de curadoria aplicadas as partidas ANTES de calcular o Elo.

A base de dados guarda tudo o que o Play Hub devolve; estas regras decidem o que conta.
Sao usadas pelo site (build_web.py) e pelo Elo internacional (fetch_elorcana.py), para os
dois concordarem sempre sobre quem e quem.

Ordem (importa: cada passo ve o resultado do anterior):
1. Eventos excluidos: partidas de eventos cujo NOME contem um dos textos de excluded_events.txt
   (sem maiusculas, acentos nem pontuacao: "Crown of ink - online" = "crown of ink online").
   Compara-se so o nome do evento, nao a loja: a mesma loja organiza eventos normais.
2. Contas fundidas:
   a) manualmente, em player_merges.txt (`<conta a remover> <conta a manter>`);
   b) automaticamente: contas do Play Hub com o MESMO nickname sao a mesma pessoa, e fica a conta
      com o torneio mais recente (desempate: mais eventos, depois mais partidas), que mantem o
      nome e o id. Nao se fundem contas que:
        - alguma vez jogaram o mesmo evento (uma pessoa nao joga um evento com duas contas);
        - tem um nome abreviado tipo "Pedro R" (o Play Hub usa "Nome I" quando falta o nickname,
          e muita gente partilha esse nome);
        - estao marcadas com `keep <id>` em player_merges.txt.
      Fica tudo listado ao gerar a pagina; para fundir uma dessas, usa a linha manual.
3. Minimo de eventos: jogadores com menos de MIN_EVENTS eventos distintos (contados depois dos
   passos 1 e 2) deixam de ser considerados: as suas partidas nao entram no Elo de ninguem.
   Repete-se ate ninguem ficar abaixo do minimo (tirar um jogador pode tirar um evento a outro).
   Serve para tirar visitantes que jogaram um torneio em Portugal.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path

import db
from elo import Match

MIN_EVENTS = 2
EXCLUDED_EVENTS_FILE = "excluded_events.txt"
MERGES_FILE = "player_merges.txt"
# "pedro r", "joao m": nome + uma letra = nome abreviado do Play Hub, nao um nickname escolhido.
ABBREVIATED = re.compile(r"^\S+ \S$")


def norm(s: str | None) -> str:
    """Minusculas, sem acentos, so letras e numeros separados por um espaco."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).casefold()
    return re.sub(r"[^0-9a-z]+", " ", s).strip()


def _lines(path: str | None):
    if not path or not Path(path).exists():
        return
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            yield line


def load_excluded(path: str | None) -> list[str]:
    return [t for t in (norm(l) for l in _lines(path)) if t]


def load_merges(path: str | None) -> dict[str, str]:
    """{conta a remover: conta a manter}, ja resolvido (A->B e B->C dao A->C)."""
    direct: dict[str, str] = {}
    for line in _lines(path):
        parts = line.split()
        if len(parts) == 2 and parts[0] != "keep" and parts[0] != parts[1]:
            direct[parts[0]] = parts[1]

    def final(pid: str) -> str:
        seen = {pid}
        while pid in direct:
            pid = direct[pid]
            if pid in seen:      # ciclo mal escrito: nao fundir
                return pid
            seen.add(pid)
        return pid

    return {a: final(a) for a in direct if final(a) != a}


def load_keep_separate(path: str | None) -> set[str]:
    """Ids marcados com `keep <id>`: nunca entram numa fusao automatica."""
    out = set()
    for line in _lines(path):
        parts = line.split()
        if len(parts) == 2 and parts[0] == "keep":
            out.add(parts[1])
    return out


@dataclass
class Report:
    excluded_events: int = 0
    excluded_matches: int = 0
    merged: list[tuple[str, str]] = field(default_factory=list)                 # manuais: (remover, manter)
    auto_merged: list[tuple[str, str, str]] = field(default_factory=list)       # (nome, remover, manter)
    kept_separate: list[tuple[str, list[str], str]] = field(default_factory=list)  # (nome, ids, motivo)
    dropped_players: int = 0
    dropped_matches: int = 0

    def lines(self, min_events: int) -> list[str]:
        out = [f"Curadoria: {self.excluded_events} eventos excluidos ({self.excluded_matches} partidas), "
               f"{len(self.merged) + len(self.auto_merged)} contas fundidas "
               f"({len(self.merged)} manuais, {len(self.auto_merged)} pelo nome), "
               f"{self.dropped_players} jogadores com menos de {min_events} eventos ignorados "
               f"({self.dropped_matches} partidas)"]
        out += [f"  fundida pelo nome: {name!r}: conta {dup} passa para {keep}" for name, dup, keep in self.auto_merged]
        out += [f"  mesmo nome mas NAO fundidas ({why}): {name!r} -> {', '.join(ids)}"
                for name, ids, why in self.kept_separate]
        return out


def _auto_merges(matches: list[Match], names: dict[str, str], keep_separate: set[str],
                 rep: Report) -> dict[str, str]:
    events: dict[str, set[str]] = defaultdict(set)
    last: dict[str, str] = {}
    count: dict[str, int] = defaultdict(int)
    for m in matches:
        for p in (m.player_a, m.player_b):
            events[p].add(m.event_id)
            count[p] += 1
            if m.date > last.get(p, ""):
                last[p] = m.date
    by_name: dict[str, list[str]] = defaultdict(list)
    for p in events:
        n = norm(names.get(p, ""))
        if n:
            by_name[n].append(p)

    merges: dict[str, str] = {}
    for name in sorted(by_name):
        ids = by_name[name]
        if len(ids) < 2:
            continue
        newest_first = sorted(ids, key=lambda p: (last[p], len(events[p]), count[p], p), reverse=True)
        label = names.get(newest_first[0], name)   # o nome da conta que fica
        if ABBREVIATED.match(name):
            rep.kept_separate.append((label, sorted(ids), "nome abreviado do Play Hub"))
            continue
        fixed = [p for p in ids if p in keep_separate]
        movable = [p for p in newest_first if p not in keep_separate]
        groups: list[list[str]] = []   # cada grupo = uma pessoa; o primeiro e o mais recente
        for p in movable:
            for g in groups:
                if all(events[p].isdisjoint(events[o]) for o in g):
                    g.append(p)
                    break
            else:
                groups.append([p])
        for g in groups:
            for dup in g[1:]:
                merges[dup] = g[0]
                rep.auto_merged.append((label, dup, g[0]))
        left = [g[0] for g in groups] + fixed
        if len(left) > 1:
            why = "marcada com keep" if fixed else "jogaram no mesmo evento"
            rep.kept_separate.append((label, sorted(left), why))
    return merges


def curate(matches: list[Match], events: dict[str, dict], excluded: list[str] | None = None,
           merges: dict[str, str] | None = None, min_events: int = MIN_EVENTS,
           names: dict[str, str] | None = None, keep_separate: set[str] | None = None
           ) -> tuple[list[Match], Report]:
    """events: {id do evento: linha da tabela events (com 'name')}.
    names: {id: nickname}; se for dado, fundem-se contas com o mesmo nickname (passo 2b)."""
    rep = Report()
    excluded, merges = excluded or [], merges or {}

    bad_events = {eid for eid, ev in events.items()
                  if any(tok in norm(ev.get("name")) for tok in excluded)}
    kept = [m for m in matches if m.event_id not in bad_events]
    rep.excluded_events = len({m.event_id for m in matches} & bad_events)
    rep.excluded_matches = len(matches) - len(kept)

    def remap(ms: list[Match], mp: dict[str, str]) -> list[Match]:
        ms = [replace(m, player_a=mp.get(m.player_a, m.player_a), player_b=mp.get(m.player_b, m.player_b))
              for m in ms]
        return [m for m in ms if m.player_a != m.player_b]

    used = {p for m in kept for p in (m.player_a, m.player_b)}
    rep.merged = sorted((a, b) for a, b in merges.items() if a in used)
    if merges:
        kept = remap(kept, merges)
    if names is not None:
        auto = _auto_merges(kept, names, keep_separate or set(), rep)
        if auto:
            kept = remap(kept, auto)

    if min_events > 1:
        before = len(kept)
        dropped: set[str] = set()
        while True:   # tirar um jogador pode deixar outro abaixo do minimo: repete ate estabilizar
            seen: dict[str, set[str]] = defaultdict(set)
            for m in kept:
                seen[m.player_a].add(m.event_id)
                seen[m.player_b].add(m.event_id)
            low = {p for p, evs in seen.items() if len(evs) < min_events}
            if not low:
                break
            dropped |= low
            kept = [m for m in kept if m.player_a not in low and m.player_b not in low]
        rep.dropped_players = len(dropped)
        rep.dropped_matches = before - len(kept)
    return kept, rep


def add_arguments(ap) -> None:
    """Opcoes partilhadas por build_web.py e fetch_elorcana.py."""
    ap.add_argument("--min-events", type=int, default=MIN_EVENTS,
                    help="eventos minimos em Portugal para um jogador contar")
    ap.add_argument("--exclude-events", default=EXCLUDED_EVENTS_FILE)
    ap.add_argument("--merges", default=MERGES_FILE)
    ap.add_argument("--no-auto-merge", action="store_true",
                    help="nao fundir contas com o mesmo nickname (so as de player_merges.txt)")


def load_curated(conn, args, date_from: str | None = None, date_to: str | None = None
                 ) -> tuple[list[Match], Report]:
    """Carrega as partidas da base de dados e aplica todas as regras."""
    events = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM events")}
    names = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM players")}
    auto = not getattr(args, "no_auto_merge", False)
    return curate(db.load_matches(conn, date_from, date_to), events, load_excluded(args.exclude_events),
                  load_merges(args.merges), args.min_events, names if auto else None,
                  load_keep_separate(args.merges))
