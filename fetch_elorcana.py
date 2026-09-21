#!/usr/bin/env python3
"""Vai buscar o Elo internacional dos nossos jogadores ao elorcana.com.

O elorcana tem os seus proprios ids (UUID) e nao expoe o id do Play Hub, por isso a ligacao
e feita pelo nickname: para cada jogador da nossa base de dados pesquisamos o nome na API
publica deles e ficamos SO com perfis da plataforma RPH (Ravensburger Play Hub) cujo nome e
exatamente o mesmo. Os perfis MELEE sao ignorados: o mesmo jogador aparece muitas vezes
duplicado (um perfil por plataforma) e so o do Play Hub e comparavel com os nossos dados.

Regras de seguranca:
- Se houver mais de um perfil RPH com o mesmo nome, nao adivinhamos: fica "ambiguous" e o
  jogador nao mostra Elo internacional (a nao ser que ponhas o par em elorcana_overrides.txt).
- Jogadores em opt_out.txt nunca sao pesquisados.
- Se o elorcana estiver em baixo, mantemos o que ja tinhamos e o site publica na mesma.

Ficheiro de saida (tambem serve de cache entre execucoes):
  {"players": {"<id do Play Hub>": {"status": "matched", "id": "<uuid>", "username": ..,
                                    "elo": .., "rank": .., "peak": .., ...}}}

Ficheiro de correcoes (elorcana_overrides.txt), uma por linha:
  <id do Play Hub> <uuid do perfil do elorcana>   -> forca este perfil
  <id do Play Hub> none                            -> nunca mostrar Elo internacional
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import curate
from build_site import load_opt_out
from db import connect

API_BASE = "https://api.elorcana.com"
USER_AGENT = "lorcana-pt-elo/0.1 (projeto de fas; ranking Elo Portugal)"
PLATFORM = "RPH"
AUTOCOMPLETE_SIZE = 20
RECHECK_DAYS = 7       # quem nao encontramos volta a ser procurado passado este tempo
MAX_CONSECUTIVE_ERRORS = 8


def fold(s: str) -> str:
    return unicodedata.normalize("NFKC", s).casefold().strip()


class ApiError(Exception):
    pass


class Api:
    def __init__(self, base: str, delay: float = 0.3):
        self.base = base.rstrip("/")
        self.delay = delay
        self.requests = 0

    def get(self, path: str, params: dict | None = None):
        url = f"{self.base}/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        last: Exception | None = None
        for attempt in range(3):
            if self.delay:
                time.sleep(self.delay)
            self.requests += 1
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                last = e
                if e.code == 404:
                    return None
                if e.code < 500 and e.code != 429:
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last = e
            if attempt < 2:
                time.sleep(2 ** attempt)
        raise ApiError(f"{url}: {last}")


def load_overrides(path: str) -> dict[str, str | None]:
    """{id do Play Hub: uuid do elorcana, ou None para 'nunca mostrar'}."""
    out: dict[str, str | None] = {}
    p = Path(path)
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        parts = line.split()
        if len(parts) == 2:
            out[parts[0]] = None if parts[1].lower() == "none" else parts[1]
    return out


def find_profile(api: Api, name: str):
    """Devolve (status, perfil). status: matched | ambiguous | none."""
    found = api.get("players/autocompleteName", {"prefix": name, "size": AUTOCOMPLETE_SIZE}) or []
    exact = [p for p in found
             if p.get("source") == PLATFORM and p.get("id") and fold(str(p.get("username", ""))) == fold(name)]
    if len(exact) == 1:
        return "matched", exact[0]
    return ("ambiguous" if exact else "none"), None


def fetch_stats(api: Api, uuid: str):
    """Elo, posicao e pico do perfil, ou None se nao existir / nao for do Play Hub."""
    data = api.get(f"players/{urllib.parse.quote(uuid)}")
    if not data:
        return None
    player, stats = data.get("player") or {}, data.get("stats") or {}
    if player.get("source") != PLATFORM or stats.get("elo") is None:
        return None
    return {
        "id": player.get("id") or uuid,
        "username": player.get("username"),
        "elo": round(float(stats["elo"]), 1),
        "rank": stats.get("eloRank"),
        "peak": round(float(stats["peakElo"]), 1) if stats.get("peakElo") is not None else None,
    }


def stale(entry: dict, today: date) -> bool:
    try:
        return date.fromisoformat(entry.get("checked", "")) <= today - timedelta(days=RECHECK_DAYS)
    except ValueError:
        return True


def collect(args) -> int:
    conn = connect(args.db)
    try:
        matches, _ = curate.load_curated(conn, args, args.date_from)
        in_site = {p for m in matches for p in (m.player_a, m.player_b)}
        rows = sorted((r for r in conn.execute("SELECT id, name FROM players") if r["id"] in in_site),
                      key=lambda r: r["id"])
    finally:
        conn.close()
    hidden = load_opt_out(args.opt_out)
    overrides = load_overrides(args.overrides)
    out_path = Path(args.out)
    old: dict = {}
    if out_path.exists():
        try:
            old = json.loads(out_path.read_text(encoding="utf-8")).get("players", {})
        except (OSError, json.JSONDecodeError):
            old = {}
    api = Api(args.base, args.delay)
    today = date.today()
    result: dict[str, dict] = {}
    errors = consecutive = 0
    counts = {"matched": 0, "ambiguous": 0, "none": 0}

    for r in rows:
        pid, name = str(r["id"]), (r["name"] or "").strip()
        if pid in hidden or not name:
            continue
        prev = old.get(pid)
        if prev and prev.get("name") != name:
            prev = None  # mudou de nome: o que tinhamos pode ser de outra pessoa
        if consecutive >= MAX_CONSECUTIVE_ERRORS:
            if prev:
                result[pid] = prev  # API em baixo: mantem o que ja tinhamos
            continue
        try:
            entry = {"name": name, "checked": today.isoformat()}
            if pid in overrides:
                uuid = overrides[pid]
                status, uuid = ("none", None) if uuid is None else ("matched", uuid)
            elif prev and prev.get("status") == "matched":
                status, uuid = "matched", prev["id"]
            elif prev and not stale(prev, today):
                result[pid] = prev
                counts[prev["status"]] += 1
                continue
            else:
                status, profile = find_profile(api, name)
                uuid = profile["id"] if profile else None
            if status == "matched":
                stats = fetch_stats(api, uuid)
                if stats is None:
                    status = "none"
                else:
                    entry.update(stats)
            entry["status"] = status
            result[pid] = entry
            counts[status] += 1
            consecutive = 0
        except ApiError as e:
            errors += 1
            consecutive += 1
            print(f"  aviso: {name} ({pid}): {e}", file=sys.stderr, flush=True)
            if prev:
                result[pid] = prev

    if consecutive >= MAX_CONSECUTIVE_ERRORS:
        print("aviso: elorcana parece estar indisponivel; mantive os dados anteriores.", file=sys.stderr)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"updated": today.isoformat(), "players": result}, ensure_ascii=False,
                              sort_keys=True, indent=1), encoding="utf-8")
    tmp.replace(out_path)
    print(f"Elo internacional: {counts['matched']} encontrados, {counts['none']} sem perfil, "
          f"{counts['ambiguous']} ambiguos (nome repetido no Play Hub), {errors} erros | "
          f"pedidos={api.requests}")
    return 0  # nunca falha o publicar do site por causa de um servico de terceiros


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/lorcana.db")
    ap.add_argument("--out", default="raw/elorcana.json")
    ap.add_argument("--opt-out", default="opt_out.txt")
    # Mesmas regras do site (curate.py), para so procurarmos quem aparece no ranking.
    ap.add_argument("--from", dest="date_from", default="2025-09-05")
    curate.add_arguments(ap)
    ap.add_argument("--overrides", default="elorcana_overrides.txt")
    ap.add_argument("--base", default=API_BASE)
    ap.add_argument("--delay", type=float, default=0.3, help="pausa entre pedidos, em segundos")
    return collect(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())
