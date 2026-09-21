#!/usr/bin/env python3
"""Gera dados FICTICIOS para testar o motor de Elo e o site.

Nada aqui vem do Play Hub: os jogadores, lojas e resultados sao inventados.
Uso: python make_sample_data.py [caminho.csv]
"""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path
from datetime import date, timedelta

random.seed(2026)

FIRST = ["Ana", "Bruno", "Carla", "Diogo", "Eva", "Filipe", "Gonçalo", "Helena", "Inês",
         "João", "Kátia", "Luís", "Marta", "Nuno", "Olga", "Pedro", "Rita", "Sérgio",
         "Teresa", "Vasco", "Xavier", "Yara", "André", "Beatriz", "Cláudio", "Daniela",
         "Emanuel", "Fátima", "Gil", "Hugo", "Isabel", "Jorge", "Lara", "Miguel", "Nádia", "Óscar"]
INITIALS = "ABCDFGJLMNPRSTV"
STORES = [("Lisboa", "Loja Demo Alfa"), ("Lisboa", "Loja Demo Beta"),
          ("Porto", "Loja Demo Gama"), ("Coimbra", "Loja Demo Delta")]
COLUMNS = ["event_id", "event_name", "event_date", "store", "city", "round",
           "player_a_id", "player_a_name", "player_b_id", "player_b_name", "result"]


def main(path: str) -> None:
    players = []
    for i, first in enumerate(FIRST):
        players.append({
            "id": f"demo-{i + 1:03d}",
            "name": f"{first} {random.choice(INITIALS)}.",
            "skill": 1500 + random.gauss(0, 140),
            "city": random.choice(["Lisboa", "Lisboa", "Porto", "Coimbra"]),
        })

    rows = []
    day = date(2025, 9, 6)  # sabado a seguir ao lancamento do Set 9
    n = 0
    while day <= date(2026, 9, 19):
        city, store = STORES[n % len(STORES)]
        n += 1
        pool = [p for p in players if p["city"] == city and random.random() < 0.75]
        pool += [p for p in players if p["city"] != city and random.random() < 0.15]
        if len(pool) >= 6:
            play_event(rows, f"demo-e-{day.isoformat()}", f"Liga semanal ({store})",
                       day, store, city, pool)
        day += timedelta(days=7)

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} linhas escritas em {path}")


def play_event(rows, event_id, name, day, store, city, pool) -> None:
    points = {p["id"]: 0.0 for p in pool}
    byes = set()
    by_id = {p["id"]: p for p in pool}
    for rnd in range(1, (3 if len(pool) <= 8 else 4) + 1):
        order = sorted(points, key=lambda pid: (-points[pid], random.random()))
        if len(order) % 2:
            bye = next(pid for pid in reversed(order) if pid not in byes)
            byes.add(bye)
            order.remove(bye)
            points[bye] += 1.0
            rows.append(row(event_id, name, day, store, city, rnd, by_id[bye], None, "A"))
        for a_id, b_id in zip(order[::2], order[1::2]):
            a, b = by_id[a_id], by_id[b_id]
            p_a = 1.0 / (1.0 + 10 ** ((b["skill"] - a["skill"]) / 400))
            r = random.random()
            result = "D" if r < 0.06 else ("A" if random.random() < p_a else "B")
            points[a_id] += {"A": 1.0, "D": 0.5, "B": 0.0}[result]
            points[b_id] += {"A": 0.0, "D": 0.5, "B": 1.0}[result]
            rows.append(row(event_id, name, day, store, city, rnd, a, b, result))


def row(event_id, name, day, store, city, rnd, a, b, result) -> dict:
    return {
        "event_id": event_id, "event_name": name, "event_date": day.isoformat(),
        "store": store, "city": city, "round": rnd,
        "player_a_id": a["id"], "player_a_name": a["name"],
        "player_b_id": b["id"] if b else "", "player_b_name": b["name"] if b else "",
        "result": result,
    }


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/sample_matches.csv")
