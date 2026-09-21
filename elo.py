"""Motor de Elo do ranking Lorcana Portugal.

Recebe partidas e devolve o rating de cada jogador, mais o historico
partida a partida (usado nas paginas de jogador).

Regras:
- Todos comecam em START_RATING.
- As partidas sao processadas por ordem cronologica: data, evento, ronda.
- Partidas da mesma ronda usam os ratings de *antes* da ronda, para que
  a ordem em que aparecem no ficheiro nao altere o resultado.
- Empate vale 0.5. Byes (sem adversario) e partidas contra si proprio
  sao ignorados.
- K e maior enquanto o jogador tem poucas partidas (rating provisorio).
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import groupby

START_RATING = 1000.0
PROVISIONAL_GAMES = 10
K_PROVISIONAL = 40.0
K_STABLE = 24.0


def expected_score(rating: float, opponent: float) -> float:
    """Probabilidade esperada de `rating` vencer `opponent`."""
    return 1.0 / (1.0 + 10.0 ** ((opponent - rating) / 400.0))


def k_factor(games_played: int) -> float:
    return K_PROVISIONAL if games_played < PROVISIONAL_GAMES else K_STABLE


@dataclass(frozen=True)
class Match:
    id: int
    event_id: str
    date: str  # ISO: AAAA-MM-DD
    round: int
    player_a: str
    player_b: str
    score_a: float  # 1.0 vitoria de A, 0.5 empate, 0.0 vitoria de B


@dataclass
class PlayerStats:
    id: str
    rating: float = START_RATING
    peak: float = START_RATING
    games: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    last_date: str = ""

    @property
    def win_rate(self) -> float:
        if not self.games:
            return 0.0
        return (self.wins + 0.5 * self.draws) / self.games


@dataclass(frozen=True)
class HistoryRow:
    player: str
    match_id: int
    date: str
    event_id: str
    round: int
    opponent: str
    score: float  # do ponto de vista de `player`
    rating_before: float
    rating_after: float
    opponent_rating: float

    @property
    def delta(self) -> float:
        return self.rating_after - self.rating_before


def _apply(stats: PlayerStats, new_rating: float, score: float, date: str) -> None:
    stats.rating = new_rating
    stats.peak = max(stats.peak, new_rating)
    stats.games += 1
    if score == 1.0:
        stats.wins += 1
    elif score == 0.0:
        stats.losses += 1
    else:
        stats.draws += 1
    stats.last_date = date


def compute(matches) -> tuple[dict[str, PlayerStats], list[HistoryRow]]:
    """Devolve (estatisticas por jogador, historico por partida)."""
    stats: dict[str, PlayerStats] = {}
    history: list[HistoryRow] = []

    def get(pid: str) -> PlayerStats:
        if pid not in stats:
            stats[pid] = PlayerStats(pid)
        return stats[pid]

    valid = [m for m in matches if m.player_a and m.player_b and m.player_a != m.player_b]
    ordered = sorted(valid, key=lambda m: (m.date, m.event_id, m.round, m.id))

    for _, group in groupby(ordered, key=lambda m: (m.date, m.event_id, m.round)):
        updates = []
        for m in group:
            a, b = get(m.player_a), get(m.player_b)
            expected_a = expected_score(a.rating, b.rating)
            score_b = 1.0 - m.score_a
            new_a = a.rating + k_factor(a.games) * (m.score_a - expected_a)
            new_b = b.rating + k_factor(b.games) * (score_b - (1.0 - expected_a))
            history.append(HistoryRow(a.id, m.id, m.date, m.event_id, m.round, b.id,
                                      m.score_a, a.rating, new_a, b.rating))
            history.append(HistoryRow(b.id, m.id, m.date, m.event_id, m.round, a.id,
                                      score_b, b.rating, new_b, a.rating))
            updates.append((m, new_a, new_b))
        for m, new_a, new_b in updates:
            _apply(get(m.player_a), new_a, m.score_a, m.date)
            _apply(get(m.player_b), new_b, 1.0 - m.score_a, m.date)

    return stats, history
