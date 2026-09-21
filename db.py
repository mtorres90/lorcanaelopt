"""Base de dados SQLite: jogadores, eventos e partidas."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from elo import Match

SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id    TEXT PRIMARY KEY,
    name  TEXT,
    date  TEXT NOT NULL,
    store TEXT,
    city  TEXT
);
CREATE TABLE IF NOT EXISTS matches (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(id),
    round    INTEGER NOT NULL,
    player_a TEXT NOT NULL REFERENCES players(id),
    player_b TEXT NOT NULL REFERENCES players(id),
    score_a  REAL NOT NULL,
    UNIQUE (event_id, round, player_a, player_b)
);
CREATE INDEX IF NOT EXISTS idx_matches_event ON matches(event_id);
"""


def connect(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def load_matches(conn: sqlite3.Connection, date_from: str | None = None,
                 date_to: str | None = None) -> list[Match]:
    sql = (
        "SELECT m.id, m.event_id, e.date, m.round, m.player_a, m.player_b, m.score_a "
        "FROM matches m JOIN events e ON e.id = m.event_id WHERE 1 = 1"
    )
    params: list[str] = []
    if date_from:
        sql += " AND e.date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND e.date <= ?"
        params.append(date_to)
    return [
        Match(r["id"], r["event_id"], r["date"], r["round"],
              r["player_a"], r["player_b"], r["score_a"])
        for r in conn.execute(sql, params)
    ]
