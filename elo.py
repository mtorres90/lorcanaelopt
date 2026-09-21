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
- K tambem escala com o tamanho do evento (numero de jogadores distintos):
  eventos ate 16 jogadores sao a base (x1), 17-32 valem x1.25, 33+ valem x1.5.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import groupby

START_RATING = 1000.0
PROVISIONAL_GAMES = 10
K_PROVISIONAL = 40.0
K_STABLE = 24.0

# Field-size tiers: matches at a deeper event move rating more, since beating a
# bigger field is a stronger signal than the same record at a small local.
# Events with up to 16 distinct players are the baseline (x1); anything smaller
# is not penalised, only bigger fields are boosted.
EVENT_SIZE_TIERS = ((33, 1.5), (17, 1.25))


def event_k_multiplier(n_players: int) -> float:
    """K multiplier for an event with `n_players` distinct participants."""
    for threshold, mult in EVENT_SIZE_TIERS:
        if n_players >= threshold:
            return mult
    return 1.0


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


def extra_stats(hist: list[HistoryRow], hidden: set[str]) -> dict:
    """Estatisticas extra por jogador, para a pagina de jogador: sequencias,
    extremos, desempenho como favorito/azarao e confrontos diretos.
    `hist` e o historico do jogador (HistoryRow), em ordem cronologica.
    `hidden` sao os ids de jogadores ocultos (opt-out): as suas partidas
    contam para os totais, mas nao aparecem nos confrontos diretos."""
    events = len({h.event_id for h in hist})
    ratings = [START_RATING] + [h.rating_after for h in hist]
    low = min(ratings)
    best_gain = max((h.delta for h in hist), default=0.0)
    worst_loss = min((h.delta for h in hist), default=0.0)

    best_win_streak = cur_win = 0
    best_loss_streak = cur_loss = 0
    for h in hist:
        if h.score == 1.0:
            cur_win += 1
            cur_loss = 0
        elif h.score == 0.0:
            cur_loss += 1
            cur_win = 0
        else:
            cur_win = cur_loss = 0
        best_win_streak = max(best_win_streak, cur_win)
        best_loss_streak = max(best_loss_streak, cur_loss)

    fav_games = fav_wins = dog_games = dog_wins = 0.0
    h2h: dict[str, dict] = {}
    for h in hist:
        if h.rating_before >= h.opponent_rating:
            fav_games += 1
            fav_wins += h.score
        else:
            dog_games += 1
            dog_wins += h.score
        if h.opponent not in hidden:
            rec = h2h.setdefault(h.opponent, {"id": h.opponent, "games": 0, "wins": 0, "draws": 0, "losses": 0})
            rec["games"] += 1
            if h.score == 1.0:
                rec["wins"] += 1
            elif h.score == 0.0:
                rec["losses"] += 1
            else:
                rec["draws"] += 1

    top_h2h = sorted(h2h.values(), key=lambda r: (-r["games"], r["id"]))[:8]

    return {
        "events": events,
        "low": low,
        "best_gain": best_gain,
        "worst_loss": worst_loss,
        "best_win_streak": best_win_streak,
        "best_loss_streak": best_loss_streak,
        "fav_games": int(fav_games), "fav_wins": fav_wins,
        "dog_games": int(dog_games), "dog_wins": dog_wins,
        "h2h": top_h2h,
    }


def dna_stats(hist: list[HistoryRow], min_n: int = 3) -> dict:
    """'Summoner's DNA': seis eixos do estilo competitivo, calculados so a partir
    do historico de partidas (sem dados por-jogo dentro da partida, que a API nao
    da). Cada eixo tem tambem a dimensao da amostra (`_n`); com menos de `min_n`
    fica a None, para o grafico assinalar 'sem dados suficientes' em vez de
    mostrar uma percentagem enganadora."""

    def rate(score_sum: float, n: int) -> float | None:
        return round(score_sum / n * 100, 1) if n >= min_n else None

    games = len(hist)
    dominance_sum = sum(h.score for h in hist)

    fav_n = fav_sum = dog_n = dog_sum = 0
    for h in hist:
        if h.rating_before >= h.opponent_rating:
            fav_n += 1
            fav_sum += h.score
        else:
            dog_n += 1
            dog_sum += h.score

    by_event: dict[str, list[HistoryRow]] = {}
    for h in hist:
        by_event.setdefault(h.event_id, []).append(h)
    final_rows = [rows[-1] for rows in by_event.values()]
    composure_sum = sum(h.score for h in final_rows)

    qualifying_events = [rows for rows in by_event.values() if len(rows) >= 2]
    mastered = sum(1 for rows in qualifying_events
                   if sum(h.score for h in rows) / len(rows) >= 0.6)

    clutch_n = clutch_sum = 0
    for prev, cur in zip(hist, hist[1:]):
        if prev.score == 0.0:
            clutch_n += 1
            clutch_sum += cur.score

    return {
        "dominance": rate(dominance_sum, games), "dominance_n": games,
        "consistency": rate(fav_sum, fav_n), "consistency_n": fav_n,
        "composure": rate(composure_sum, len(final_rows)), "composure_n": len(final_rows),
        "event_mastery": rate(mastered, len(qualifying_events)), "event_mastery_n": len(qualifying_events),
        "grit": rate(dog_sum, dog_n), "grit_n": dog_n,
        "clutch": rate(clutch_sum, clutch_n), "clutch_n": clutch_n,
    }


def rival_labels(h2h: list[dict], min_games: int = 3) -> tuple[str | None, str | None]:
    """Escolhe o maior rival (pior taxa de vitoria) e a vitima favorita (melhor
    taxa de vitoria) entre os confrontos com pelo menos `min_games` partidas."""
    qualifying = [r for r in h2h if r["games"] >= min_games]
    if not qualifying:
        return None, None

    def rate(r: dict) -> float:
        return (r["wins"] + 0.5 * r["draws"]) / r["games"]

    nemesis = min(qualifying, key=rate)
    victim = max(qualifying, key=rate)
    nemesis_id = nemesis["id"] if rate(nemesis) < 0.5 else None
    victim_id = victim["id"] if rate(victim) > 0.5 and victim["id"] != nemesis_id else None
    return nemesis_id, victim_id


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

    event_players: dict[str, set[str]] = defaultdict(set)
    for m in valid:
        event_players[m.event_id].add(m.player_a)
        event_players[m.event_id].add(m.player_b)
    event_mult = {eid: event_k_multiplier(len(ps)) for eid, ps in event_players.items()}

    for _, group in groupby(ordered, key=lambda m: (m.date, m.event_id, m.round)):
        updates = []
        for m in group:
            a, b = get(m.player_a), get(m.player_b)
            mult = event_mult[m.event_id]
            expected_a = expected_score(a.rating, b.rating)
            score_b = 1.0 - m.score_a
            new_a = a.rating + k_factor(a.games) * mult * (m.score_a - expected_a)
            new_b = b.rating + k_factor(b.games) * mult * (score_b - (1.0 - expected_a))
            history.append(HistoryRow(a.id, m.id, m.date, m.event_id, m.round, b.id,
                                      m.score_a, a.rating, new_a, b.rating))
            history.append(HistoryRow(b.id, m.id, m.date, m.event_id, m.round, a.id,
                                      score_b, b.rating, new_b, a.rating))
            updates.append((m, new_a, new_b))
        for m, new_a, new_b in updates:
            _apply(get(m.player_a), new_a, m.score_a, m.date)
            _apply(get(m.player_b), new_b, 1.0 - m.score_a, m.date)

    return stats, history
