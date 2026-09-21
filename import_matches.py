#!/usr/bin/env python3
"""Importa partidas de um CSV normalizado para a base de dados.

Colunas obrigatorias:
  event_id, event_name, event_date, store, city, round,
  player_a_id, player_a_name, player_b_id, player_b_name, result

Colunas opcionais (ficam em branco se a fonte nao as tiver):
  player_a_real_name, player_b_real_name

`result` e A (ganhou o jogador A), B (ganhou o jogador B) ou D (empate).
Linhas sem player_b_id sao byes e ficam de fora.
A importacao e idempotente: importar o mesmo ficheiro duas vezes nao duplica nada.

Uso:
  python import_matches.py data/matches.csv --db data/lorcana.db --from 2025-09-05
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date

import db

REQUIRED = [
    "event_id", "event_name", "event_date", "store", "city", "round",
    "player_a_id", "player_a_name", "player_b_id", "player_b_name", "result",
]
RESULTS = {"A": 1.0, "B": 0.0, "D": 0.5}


def parse_date(value: str) -> str:
    return date.fromisoformat(value.strip()[:10]).isoformat()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv_path")
    ap.add_argument("--db", default="data/lorcana.db")
    ap.add_argument("--from", dest="date_from", default="2025-09-05",
                    help="ignora eventos anteriores a esta data (AAAA-MM-DD)")
    ap.add_argument("--to", dest="date_to", default=None,
                    help="ignora eventos posteriores a esta data (AAAA-MM-DD)")
    args = ap.parse_args()

    conn = db.connect(args.db)
    counts = {"lidas": 0, "importadas": 0, "byes": 0, "fora_do_periodo": 0, "invalidas": 0}

    with open(args.csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            print(f"Faltam colunas no CSV: {', '.join(missing)}", file=sys.stderr)
            return 1

        for row in reader:
            counts["lidas"] += 1
            try:
                event_date = parse_date(row["event_date"])
                rnd = int(row["round"])
                score_a = RESULTS[row["result"].strip().upper()]
            except (ValueError, KeyError):
                counts["invalidas"] += 1
                continue

            if event_date < args.date_from or (args.date_to and event_date > args.date_to):
                counts["fora_do_periodo"] += 1
                continue
            a_id, b_id = row["player_a_id"].strip(), row["player_b_id"].strip()
            if not b_id:
                counts["byes"] += 1
                continue
            if not a_id or a_id == b_id:
                counts["invalidas"] += 1
                continue

            conn.execute(
                "INSERT INTO events(id, name, date, store, city) VALUES (?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, date=excluded.date, "
                "store=excluded.store, city=excluded.city",
                (row["event_id"].strip(), row["event_name"].strip(), event_date,
                 row["store"].strip(), row["city"].strip()),
            )
            for pid, pname, prealname in (
                (a_id, row["player_a_name"], row.get("player_a_real_name", "")),
                (b_id, row["player_b_name"], row.get("player_b_real_name", "")),
            ):
                conn.execute(
                    "INSERT INTO players(id, name, real_name) VALUES (?,?,?) "
                    "ON CONFLICT(id) DO UPDATE SET name=excluded.name, "
                    "real_name=COALESCE(NULLIF(excluded.real_name, ''), players.real_name)",
                    (pid, pname.strip() or pid, (prealname or "").strip()),
                )
            cur = conn.execute(
                "INSERT OR IGNORE INTO matches(event_id, round, player_a, player_b, score_a) "
                "VALUES (?,?,?,?,?)",
                (row["event_id"].strip(), rnd, a_id, b_id, score_a),
            )
            counts["importadas"] += cur.rowcount

    conn.commit()
    print("Resumo:", ", ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
