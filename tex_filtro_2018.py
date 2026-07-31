from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable

import pandas as pd

from tex_operacional_core import clean_text, parse_date, standings_context

FILTER_API_VERSION = "28.2.0"
FILTER_NAME = "Filtro eliminatório de 2018"


@dataclass(frozen=True)
class Filter2018Result:
    input_id: str
    approved: bool
    status: str
    rule1_pass: bool
    rule1_basis: str
    rule1_detail: str
    rule2_pass: bool
    rule2_detail: str
    rule3_pass: bool
    rule3_count: int
    rule3_detail: str
    rule4_pass: bool
    rule4_count: int
    rule4_detail: str
    home_history_count: int
    away_history_count: int
    last_h2h_date: str
    last_h2h_score: str
    last_h2h_both_scored: str
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "InputID": self.input_id,
            "Filter2018Approved": self.approved,
            "Filter2018Status": self.status,
            "Filter2018Rule1Pass": self.rule1_pass,
            "Filter2018Rule1Basis": self.rule1_basis,
            "Filter2018Rule1Detail": self.rule1_detail,
            "Filter2018Rule2Pass": self.rule2_pass,
            "Filter2018Rule2Detail": self.rule2_detail,
            "Filter2018Rule3Pass": self.rule3_pass,
            "Filter2018Rule3Count": self.rule3_count,
            "Filter2018Rule3Detail": self.rule3_detail,
            "Filter2018Rule4Pass": self.rule4_pass,
            "Filter2018Rule4Count": self.rule4_count,
            "Filter2018Rule4Detail": self.rule4_detail,
            "Filter2018HomeHistoryCount": self.home_history_count,
            "Filter2018AwayHistoryCount": self.away_history_count,
            "Filter2018LastH2HDate": self.last_h2h_date,
            "Filter2018LastH2HScore": self.last_h2h_score,
            "Filter2018LastH2HBothScored": self.last_h2h_both_scored,
            "Filter2018Summary": self.summary,
        }


def _is_round_robin_match(raw: dict[str, Any]) -> bool:
    explicit = raw.get("IsRoundRobin")
    if explicit is not None:
        if isinstance(explicit, str):
            return explicit.strip().lower() in {"1", "true", "sim", "yes"}
        return bool(explicit)
    competition_type = clean_text(raw.get("CompetitionType") or raw.get("Tipo da competição")).lower()
    if competition_type:
        if any(term in competition_type for term in ("copa", "cup", "mata", "knockout", "amistoso", "friendly")):
            return False
        if any(term in competition_type for term in ("liga", "league", "pontos corridos", "round robin")):
            return True
    # A fonte histórica atual é composta por ligas de pontos corridos.
    return True


class HistoryIndex:
    """Índice cronológico para as regras de forma e confronto direto.

    A base atual contém partidas de liga. O índice usa todas as partidas carregadas,
    sem separar mando, e pode atravessar temporadas e códigos de liga quando o nome
    da equipe é idêntico. Copas e amistosos só serão considerados quando existirem
    na fonte de dados carregada.
    """

    def __init__(self, matches: Iterable[dict[str, Any]]):
        team_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        h2h_history: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for raw in matches:
            try:
                match_date = raw.get("DateParsed")
                if not isinstance(match_date, date):
                    match_date = parse_date(match_date or raw.get("Date"))
                home = clean_text(raw.get("Home"))
                away = clean_text(raw.get("Away"))
                hg = int(float(raw.get("HG")))
                ag = int(float(raw.get("AG")))
            except Exception:
                continue
            if not home or not away or home == away:
                continue
            item = {
                "DateParsed": match_date,
                "Home": home,
                "Away": away,
                "HG": hg,
                "AG": ag,
                "Code": clean_text(raw.get("Code")),
                "League": clean_text(raw.get("League")),
                "IsRoundRobin": _is_round_robin_match(raw),
            }
            team_history[home].append(item)
            team_history[away].append(item)
            h2h_history[tuple(sorted((home, away)))].append(item)
        for values in team_history.values():
            values.sort(key=lambda item: item["DateParsed"], reverse=True)
        for values in h2h_history.values():
            values.sort(key=lambda item: item["DateParsed"], reverse=True)
        self.team_history = dict(team_history)
        self.h2h_history = dict(h2h_history)

    def last_matches(self, team: str, before: date, limit: int = 5) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        for item in self.team_history.get(team, []):
            if item["DateParsed"] < before:
                selected.append(item)
                if len(selected) >= limit:
                    break
        return selected

    def last_h2h(self, home: str, away: str, before: date) -> tuple[dict[str, Any] | None, int]:
        skipped_non_round_robin = 0
        for item in self.h2h_history.get(tuple(sorted((home, away))), []):
            if item["DateParsed"] >= before:
                continue
            if not bool(item.get("IsRoundRobin", True)):
                skipped_non_round_robin += 1
                continue
            return item, skipped_non_round_robin
        return None, skipped_non_round_robin


def _team_scored(item: dict[str, Any], team: str) -> bool:
    if item["Home"] == team:
        return int(item["HG"]) > 0
    if item["Away"] == team:
        return int(item["AG"]) > 0
    return False


def evaluate_game_2018(
    game: dict[str, Any] | pd.Series,
    matches: list[dict[str, Any]],
    history: HistoryIndex | None = None,
) -> Filter2018Result:
    payload = dict(game)
    input_id = clean_text(payload.get("ID"))
    code = clean_text(payload.get("Código da liga"))
    home = clean_text(payload.get("Mandante"))
    away = clean_text(payload.get("Visitante"))
    match_date = parse_date(payload.get("Data"))
    history = history or HistoryIndex(matches)

    context = standings_context(matches, code, match_date, home, away)
    if context.get("Available"):
        home_position = int(context["HomePosition"])
        away_position = int(context["AwayPosition"])
        home_points = int(context["HomePoints"])
        away_points = int(context["AwayPoints"])
        if away_position < home_position:
            rule1_pass = True
            rule1_basis = "VISITANTE ACIMA NA CLASSIFICAÇÃO"
            rule1_detail = (
                f"Visitante em {away_position}º, acima do mandante em {home_position}º; "
                f"pontos: {away_points} x {home_points}."
            )
        elif away_points + 3 >= home_points:
            rule1_pass = True
            rule1_basis = "EXCEÇÃO DOS TRÊS PONTOS"
            rule1_detail = (
                f"Visitante em {away_position}º e abaixo do mandante em {home_position}º, porém "
                f"{away_points} + 3 = {away_points + 3}, alcançando os {home_points} pontos do mandante."
            )
        else:
            rule1_pass = False
            rule1_basis = "REPROVADO"
            rule1_detail = (
                f"Visitante em {away_position}º, mandante em {home_position}º; "
                f"{away_points} + 3 = {away_points + 3}, abaixo dos {home_points} pontos do mandante."
            )
    else:
        rule1_pass = False
        rule1_basis = "DADOS INSUFICIENTES"
        rule1_detail = "Não foi possível reconstruir posição e pontuação antes da partida."

    last_h2h, skipped_non_round_robin = history.last_h2h(home, away, match_date)
    exception_note = (
        f" {skipped_non_round_robin} confronto(s) mais recente(s) de competição não classificada como pontos corridos "
        "foi(ram) ignorado(s), conforme a exceção da Regra 2."
        if skipped_non_round_robin else ""
    )
    if last_h2h is None:
        rule2_pass = True
        last_h2h_date = ""
        last_h2h_score = ""
        last_h2h_both = "Não havia confronto anterior na base"
        rule2_detail = (
            "Nenhum confronto direto anterior foi encontrado na base carregada; "
            "a regra não encontrou motivo para eliminar o evento." + exception_note
        )
    else:
        both_scored = int(last_h2h["HG"]) > 0 and int(last_h2h["AG"]) > 0
        rule2_pass = not both_scored
        last_h2h_date = last_h2h["DateParsed"].strftime("%d/%m/%Y")
        last_h2h_score = f"{last_h2h['Home']} {last_h2h['HG']} x {last_h2h['AG']} {last_h2h['Away']}"
        last_h2h_both = "Sim" if both_scored else "Não"
        if both_scored:
            rule2_detail = (
                f"Último confronto direto da base em {last_h2h_date}: {last_h2h_score}; "
                "as duas equipes marcaram, portanto o evento é eliminado." + exception_note
            )
        else:
            rule2_detail = (
                f"Último confronto direto da base em {last_h2h_date}: {last_h2h_score}; "
                "não houve gols das duas equipes, portanto a regra foi atendida." + exception_note
            )

    home_last5 = history.last_matches(home, match_date, 5)
    away_last5 = history.last_matches(away, match_date, 5)
    home_scored = sum(_team_scored(item, home) for item in home_last5)
    away_scored = sum(_team_scored(item, away) for item in away_last5)

    rule3_pass = len(home_last5) == 5 and home_scored >= 4
    rule4_pass = len(away_last5) == 5 and away_scored >= 4
    rule3_detail = (
        f"Mandante marcou em {home_scored} das {len(home_last5)} partidas anteriores encontradas; "
        + ("regra atendida." if rule3_pass else "são necessárias cinco partidas e gols em pelo menos quatro.")
    )
    rule4_detail = (
        f"Visitante marcou em {away_scored} das {len(away_last5)} partidas anteriores encontradas; "
        + ("regra atendida." if rule4_pass else "são necessárias cinco partidas e gols em pelo menos quatro.")
    )

    approved = bool(rule1_pass and rule2_pass and rule3_pass and rule4_pass)
    status = "APROVADO" if approved else "REPROVADO"
    failed: list[str] = []
    if not rule1_pass:
        failed.append("Regra 1")
    if not rule2_pass:
        failed.append("Regra 2")
    if not rule3_pass:
        failed.append("Regra 3")
    if not rule4_pass:
        failed.append("Regra 4")
    summary = (
        "Todas as regras foram atendidas; evento apto para análise estatística e financeira."
        if approved
        else "Evento eliminado no filtro de 2018: " + ", ".join(failed) + "."
    )

    return Filter2018Result(
        input_id=input_id,
        approved=approved,
        status=status,
        rule1_pass=rule1_pass,
        rule1_basis=rule1_basis,
        rule1_detail=rule1_detail,
        rule2_pass=rule2_pass,
        rule2_detail=rule2_detail,
        rule3_pass=rule3_pass,
        rule3_count=home_scored,
        rule3_detail=rule3_detail,
        rule4_pass=rule4_pass,
        rule4_count=away_scored,
        rule4_detail=rule4_detail,
        home_history_count=len(home_last5),
        away_history_count=len(away_last5),
        last_h2h_date=last_h2h_date,
        last_h2h_score=last_h2h_score,
        last_h2h_both_scored=last_h2h_both,
        summary=summary,
    )


def evaluate_lot_2018(games: pd.DataFrame, matches: list[dict[str, Any]]) -> pd.DataFrame:
    if games.empty:
        return pd.DataFrame()
    history = HistoryIndex(matches)
    results = [evaluate_game_2018(row, matches, history).as_dict() for _, row in games.iterrows()]
    return pd.DataFrame(results)


__all__ = [
    "FILTER_API_VERSION", "FILTER_NAME", "Filter2018Result", "HistoryIndex",
    "evaluate_game_2018", "evaluate_lot_2018",
]
