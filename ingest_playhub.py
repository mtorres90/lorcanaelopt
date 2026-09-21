#!/usr/bin/env python3
"""Ingestao do Ravensburger Play Hub: eventos de Portugal -> CSV normalizado.

ESTADO: escrito a partir de fontes publicas sobre a API (endpoints "TV" confirmados;
os restantes caminhos e nomes de campos sao os mais provaveis, mas NAO foram testados
contra a API real). Por isso existe o modo --probe: guarda respostas reais em
raw/probe/ e resume as chaves, para ajustar o que for preciso numa so iteracao.

Uso:
  python ingest_playhub.py --probe                     # descobre base URL e formatos
  python ingest_playhub.py --from 2025-09-05 --out data/matches.csv

So usa a biblioteca padrao. Faz cache em disco (raw/) e espera entre pedidos.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

USER_AGENT = "lorcana-pt-elo/0.1 (projeto de fas; ranking Elo Portugal)"
GAME_SLUG = "disney-lorcana"

# Bases candidatas (a primeira que responder e usada). Podes forcar com --base.
BASE_CANDIDATES = [
    "https://api.cloudflare.ravensburgerplay.com/hydraproxy/api/v2",
    "https://api.ravensburgerplay.com/api/v2",
]

# Centros de pesquisa cobrindo Portugal (lat, lon, raio em milhas).
SEARCH_CENTERS = [
    (39.6, -8.0, 260),    # continente
    (32.75, -16.95, 80),  # Madeira
    (37.75, -25.7, 220),  # Acores
]

CSV_COLUMNS = ["event_id", "event_name", "event_date", "store", "city", "round",
               "player_a_id", "player_a_name", "player_b_id", "player_b_name", "result"]


# ---------- utilitarios de parsing (tolerantes a variacoes de nomes) ----------

def dig(obj, *paths, default=None):
    """Primeiro valor nao-nulo entre varios caminhos com pontos: dig(o, 'a.b', 'c')."""
    for path in paths:
        cur = obj
        for part in path.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                cur = cur[int(part)]
            else:
                cur = None
            if cur is None:
                break
        if cur not in (None, "", []):
            return cur
    return default


def items_of(data) -> list:
    """Lista de resultados de uma resposta paginada (DRF) ou de uma lista simples."""
    if isinstance(data, dict):
        for key in ("results", "items", "data", "matches"):
            if isinstance(data.get(key), list):
                return data[key]
        return []
    return data if isinstance(data, list) else []


def country_of(event: dict) -> str:
    """Codigo de pais (ex.: 'PT') a partir da loja/morada do evento."""
    store = event.get("store") if isinstance(event.get("store"), dict) else {}
    code = dig(store, "country_code", "country") or dig(event, "country_code", "country")
    if isinstance(code, dict):
        code = dig(code, "code", "name")
    if code:
        code = str(code).strip()
        return "PT" if code.lower() == "portugal" else code.upper()
    address = str(dig(store, "full_address", "address") or dig(event, "full_address", "address") or "")
    if "portugal" in address.lower():
        return "PT"
    tail = address.split(",")[-1].strip().upper() if address else ""
    return tail if len(tail) == 2 else ""


def event_date_of(event: dict) -> str | None:
    raw = dig(event, "start_datetime", "start_date", "starts_at", "start_time")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return str(raw)[:10] if re.match(r"\d{4}-\d{2}-\d{2}", str(raw)) else None


def matches_format(event: dict, tokens: list[str]) -> bool:
    """Procura os textos de formato nos campos do evento (sem a descricao nem a loja)."""
    if not tokens:
        return True
    skip = {"store", "description", "full_address"}
    text = json.dumps({k: v for k, v in event.items() if k not in skip}, ensure_ascii=False).lower()
    return any(t in text for t in tokens)


def player_key(p: dict) -> str:
    """Id estavel do jogador. Prefere o id de utilizador; cai para o id do jogador."""
    val = dig(p, "user_id", "user.id", "account_id", "account.id", "player_id", "id")
    return str(val) if val is not None else ""


def player_name(p: dict) -> str:
    """Nome a mostrar: nome de utilizador; senao primeiro nome + inicial do apelido."""
    shown = dig(p, "best_identifier", "display_name", "username", "user.username", "screen_name", "name")
    if shown:
        return str(shown).strip()
    first = str(dig(p, "first_name", "user.first_name", default="")).strip()
    last = str(dig(p, "last_name", "user.last_name", default="")).strip()
    return f"{first} {last[:1]}.".strip() if first else ""


def parse_match(m: dict):
    """Devolve (a_id, a_nome, b_id, b_nome, resultado A/B/D) ou None (bye/sem resultado)."""
    rels = m.get("player_match_relationships") or m.get("players") or []
    if m.get("match_is_bye") or len(rels) < 2:
        return None
    a_rel, b_rel = rels[0], rels[1]
    a = a_rel.get("player") if isinstance(a_rel.get("player"), dict) else a_rel
    b = b_rel.get("player") if isinstance(b_rel.get("player"), dict) else b_rel
    a_id, b_id = player_key(a), player_key(b)
    if not a_id or not b_id:
        return None

    result = None
    winner = m.get("winning_player")
    if isinstance(winner, dict):
        winner = player_key(winner)
    if m.get("match_is_intentional_draw"):
        result = "D"
    elif winner not in (None, ""):
        winner = str(winner)
        ids_a = {a_id, str(a_rel.get("id", "")), str(a.get("id", ""))}
        ids_b = {b_id, str(b_rel.get("id", "")), str(b.get("id", ""))}
        result = "A" if winner in ids_a else "B" if winner in ids_b else None
    if result is None:
        ga, gb = a_rel.get("games_won"), b_rel.get("games_won")
        if isinstance(ga, int) and isinstance(gb, int):
            result = "A" if ga > gb else "B" if gb > ga else "D"
    if result is None:
        return None
    return a_id, player_name(a), b_id, player_name(b), result


def round_ids_of(detail: dict) -> list[tuple[int, str]]:
    """[(numero_da_ronda, id_da_ronda)] a partir do detalhe do evento."""
    rounds = []
    phases = detail.get("tournament_phases") or []
    for phase in phases:
        for r in phase.get("rounds") or []:
            rounds.append(r)
    if not rounds:
        rounds = detail.get("rounds") or []
    out = []
    for i, r in enumerate(rounds, start=1):
        rid = dig(r, "id")
        if rid is not None:
            out.append((int(dig(r, "round_number", default=i)), str(rid)))
    return out


# ---------- cliente HTTP com cache e cortesia ----------

class Client:
    def __init__(self, base: str, cache_dir: Path, delay: float = 0.6):
        self.base = base.rstrip("/")
        self.cache_dir = cache_dir
        self.delay = delay
        self.requests = 0

    def _cache_path(self, url: str) -> Path:
        return self.cache_dir / (hashlib.sha1(url.encode()).hexdigest() + ".json")

    def get(self, path: str, params: dict | None = None, cache: bool = True):
        url = f"{self.base}/{path.lstrip('/')}"
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        cp = self._cache_path(url)
        if cache and cp.exists():
            return json.loads(cp.read_text(encoding="utf-8"))
        last_err = None
        for attempt in range(4):
            time.sleep(self.delay)
            self.requests += 1
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                if cache:
                    cp.parent.mkdir(parents=True, exist_ok=True)
                    cp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                return data
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code in (404, 400, 401, 403):
                    break
                time.sleep(2 ** attempt)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last_err = e
                time.sleep(2 ** attempt)
        raise RuntimeError(f"Falhou {url}: {last_err}")


# ---------- descoberta e recolha ----------

def event_list_params(lat, lon, miles, page, page_size=100):
    return {"game_slug": GAME_SLUG, "latitude": lat, "longitude": lon, "num_miles": miles,
            "upcoming_only": "false", "page": page, "page_size": page_size}


def iter_events(client: Client, max_pages: int = 60):
    seen = set()
    for lat, lon, miles in SEARCH_CENTERS:
        for page in range(1, max_pages + 1):
            data = client.get("events/", event_list_params(lat, lon, miles, page), cache=False)
            results = items_of(data)
            if not results:
                break
            for ev in results:
                eid = str(ev.get("id"))
                if eid not in seen:
                    seen.add(eid)
                    yield ev
            if isinstance(data, dict) and not data.get("next"):
                break


def collect(args) -> int:
    client = Client(args.base or discover_base(args.cache), Path(args.cache), args.delay)
    date_from = args.date_from
    date_to = args.date_to or (date.today() - timedelta(days=1)).isoformat()
    tokens = [t.strip().lower() for t in args.formats.split(",") if t.strip()]
    stats = {"eventos_vistos": 0, "pais_errado": 0, "fora_do_periodo": 0, "formato_excluido": 0,
             "sem_rondas": 0, "eventos_usados": 0, "partidas": 0, "byes_ou_sem_resultado": 0}

    rows = []
    for ev in iter_events(client):
        stats["eventos_vistos"] += 1
        if country_of(ev) != args.country:
            stats["pais_errado"] += 1
            continue
        day = event_date_of(ev)
        if not day or day < date_from or day > date_to:
            stats["fora_do_periodo"] += 1
            continue
        if not matches_format(ev, tokens):
            stats["formato_excluido"] += 1
            continue
        detail = client.get(f"events/{ev['id']}/")
        rounds = round_ids_of(detail)
        if not rounds:
            stats["sem_rondas"] += 1
            continue
        store = detail.get("store") if isinstance(detail.get("store"), dict) else (ev.get("store") or {})
        store_name = dig(store, "name", default="")
        city = dig(store, "city", "administrative_area_level_2", default="")
        used = False
        for number, rid in rounds:
            page = 1
            while True:
                data = client.get(f"tournament-rounds/{rid}/matches/paginated/",
                                  {"page": page, "page_size": 100})
                for m in items_of(data):
                    parsed = parse_match(m)
                    if not parsed:
                        stats["byes_ou_sem_resultado"] += 1
                        continue
                    a_id, a_name, b_id, b_name, result = parsed
                    rows.append([ev["id"], dig(detail, "name", default=dig(ev, "name", default="")),
                                 day, store_name, city, number, a_id, a_name, b_id, b_name, result])
                    stats["partidas"] += 1
                    used = True
                if not (isinstance(data, dict) and data.get("next")):
                    break
                page += 1
        stats["eventos_usados"] += used

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        w.writerows(rows)
    print("Resumo:", ", ".join(f"{k}={v}" for k, v in stats.items()), f"| pedidos={client.requests}")
    print(f"CSV escrito em {out}")
    return 0 if rows else 2


# ---------- modo de descoberta ----------

def summarize(obj, depth=0, max_depth=3) -> str:
    """Resumo das chaves e tipos, sem valores (evita expor dados pessoais nos logs)."""
    pad = "  " * depth
    if isinstance(obj, dict):
        if depth >= max_depth:
            return f"{{...{len(obj)} chaves}}"
        lines = []
        for k, v in obj.items():
            lines.append(f"{pad}  {k}: {summarize(v, depth + 1, max_depth)}")
        return "{\n" + "\n".join(lines) + f"\n{pad}}}"
    if isinstance(obj, list):
        return f"[{len(obj)} itens] " + (summarize(obj[0], depth, max_depth) if obj else "")
    return type(obj).__name__


def discover_base(cache: str) -> str:
    for base in BASE_CANDIDATES:
        try:
            Client(base, Path(cache), 0.3).get("events/", event_list_params(39.6, -8.0, 260, 1, 1), cache=False)
            print(f"Base URL a funcionar: {base}")
            return base
        except RuntimeError as e:
            print(f"Base URL falhou: {base} ({e})")
    raise SystemExit("Nenhuma base URL respondeu. Indica uma com --base.")


def probe(args) -> int:
    out = Path("raw/probe")
    out.mkdir(parents=True, exist_ok=True)
    base = args.base or discover_base(args.cache)
    client = Client(base, Path(args.cache), args.delay)

    events_data = client.get("events/", event_list_params(39.6, -8.0, 260, 1, 25), cache=False)
    (out / "events_page1.json").write_text(json.dumps(events_data, ensure_ascii=False, indent=1), encoding="utf-8")
    events = items_of(events_data)
    print(f"\nEventos na 1.a pagina: {len(events)}")
    if not events:
        print("Sem eventos: confirma os parametros de pesquisa.")
        return 2
    print("Forma de um evento (so chaves):", summarize(events[0]))
    print("Paises detetados:", sorted({country_of(e) or '?' for e in events}))

    pt = [e for e in events if country_of(e) == "PT"] or events
    past = [e for e in pt if (event_date_of(e) or "9999") < date.today().isoformat()] or pt
    chosen = past[0]
    detail = client.get(f"events/{chosen['id']}/", cache=False)
    (out / "event_detail.json").write_text(json.dumps(detail, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nDetalhe do evento (so chaves):", summarize(detail))
    rounds = round_ids_of(detail)
    print("Rondas encontradas:", rounds)
    if rounds:
        rid = rounds[0][1]
        data = client.get(f"tournament-rounds/{rid}/matches/paginated/", {"page": 1, "page_size": 100}, cache=False)
        (out / "round_matches.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        ms = items_of(data)
        print(f"\nPartidas na ronda {rid}: {len(ms)}")
        if ms:
            print("Forma de uma partida (so chaves):", summarize(ms[0]))
            print("Interpretada como:", parse_match(ms[0]))
    print("\nFicheiros brutos guardados em raw/probe/")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--probe", action="store_true", help="modo de descoberta: guarda amostras e resume a forma dos dados")
    ap.add_argument("--from", dest="date_from", default="2025-09-05",
                    help="data de lancamento do Set 9 (inicio da rotacao)")
    ap.add_argument("--to", dest="date_to", default=None, help="por omissao, ontem")
    ap.add_argument("--country", default="PT")
    ap.add_argument("--formats", default="core constructed",
                    help="textos de formato a aceitar, separados por virgula (vazio = todos)")
    ap.add_argument("--out", default="data/matches.csv")
    ap.add_argument("--cache", default="raw")
    ap.add_argument("--base", default=None, help="URL base da API (por omissao, testa candidatas)")
    ap.add_argument("--delay", type=float, default=0.6, help="segundos entre pedidos")
    args = ap.parse_args()
    return probe(args) if args.probe else collect(args)


if __name__ == "__main__":
    sys.exit(main())
