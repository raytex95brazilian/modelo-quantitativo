from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
import math
import re
import unicodedata
from typing import Any, Iterable

import numpy as np
import pandas as pd

from tex_v25_core import (
    ANNUAL_CODES,
    CFG,
    LEAGUES,
    V25Config,
    build_current_state,
    evaluate_live_market,
    sports_probabilities_for_match,
)

VERSION = "Tex Statistics v.27.1 — Aplicativo com seletores"


@dataclass(frozen=True)
class OperationalConfig:
    unit_fraction: float = 0.01
    weekly_top_n: int = 4
    reserve_ev_threshold: float = 0.02
    max_odd: float = 3.00


OP_CFG = OperationalConfig()


def _text(value: Any) -> str:
    return " ".join(str(value or "").replace("\ufeff", "").split())


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    aliases = {
        "chapecoense sc": "chapecoense",
        "chapecoense": "chapecoense",
        "flamengo rj": "flamengo",
        "flamengo": "flamengo",
        "botafogo rj": "botafogo",
        "botafogo": "botafogo",
        "vitoria": "vitoria",
        "america mg": "america mineiro",
        "america mineiro": "america mineiro",
        "athletico pr": "athletico paranaense",
        "athletico paranaense": "athletico paranaense",
        "internacional": "internacional",
        "gremio": "gremio",
        "sao paulo": "sao paulo",
        "coritiba": "coritiba",
        "bragantino": "bragantino",
        "red bull bragantino": "bragantino",
        "kfum": "kfum oslo",
        "sk brann": "brann",
        "ik start": "start",
    }
    return aliases.get(text, text)


def parse_date_br(value: Any) -> date:
    text = _text(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        timestamp = pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")
    else:
        timestamp = pd.to_datetime(text, dayfirst=True, errors="coerce")
    if pd.isna(timestamp):
        raise ValueError(f"Data inválida: {text or 'em branco'}")
    return timestamp.date()


def parse_odd(value: Any, implied_probability_percent: Any | None = None) -> float | None:
    """Converte odd localizada e corrige células que viraram datas no Google/Excel.

    Quando a coluna de probabilidade implícita bruta está disponível, ela é a fonte
    de verificação: odd = 100 / probabilidade. A correção só ocorre quando a odd
    textual diverge materialmente desse valor.
    """
    text = _text(value).replace(" ", "")
    number: float | None = None
    if text:
        try:
            number = float(text.replace(",", "."))
        except ValueError:
            number = None

    implied: float | None = None
    if implied_probability_percent not in (None, ""):
        try:
            implied = float(str(implied_probability_percent).replace(",", "."))
        except ValueError:
            implied = None
    recovered = 100.0 / implied if implied and implied > 0 else None

    if recovered and recovered > 1.0:
        if number is None or number <= 1.0 or number > 20.0:
            return round(recovered, 4)
        relative_error = abs(number - recovered) / recovered
        if relative_error > 0.04:
            return round(recovered, 4)
    if number is None or not math.isfinite(number) or number <= 1.0:
        return None
    return number


def season_for_match(code: str, match_date: date) -> int:
    if code in ANNUAL_CODES:
        return match_date.year
    return match_date.year if match_date.month >= 7 else match_date.year - 1


def league_code(value: Any) -> str | None:
    raw = _norm(value)
    for code, name in LEAGUES.items():
        if raw in {_norm(code), _norm(name)}:
            return code
    # Busca controlada para pequenas variações no nome da liga.
    scores = [(SequenceMatcher(None, raw, _norm(name)).ratio(), code) for code, name in LEAGUES.items()]
    score, code = max(scores, default=(0.0, ""))
    return code if score >= 0.78 else None


def team_names_by_league(matches: list[dict[str, Any]]) -> dict[str, list[str]]:
    teams: dict[str, set[str]] = {code: set() for code in LEAGUES}
    for item in matches:
        code = str(item.get("Code") or "")
        if code not in teams:
            continue
        if item.get("Home"):
            teams[code].add(str(item["Home"]))
        if item.get("Away"):
            teams[code].add(str(item["Away"]))
    return {code: sorted(values) for code, values in teams.items()}


def resolve_team(code: str, typed_name: Any, teams_by_league: dict[str, list[str]]) -> str:
    typed = _text(typed_name)
    if not typed:
        raise ValueError("Nome de equipe em branco.")
    candidates = teams_by_league.get(code, [])
    normalized = _norm(typed)
    exact = [team for team in candidates if _norm(team) == normalized]
    if exact:
        return exact[0]
    scored = sorted(
        ((SequenceMatcher(None, normalized, _norm(team)).ratio(), team) for team in candidates),
        reverse=True,
    )
    if scored and scored[0][0] >= 0.76:
        return scored[0][1]
    raise ValueError(f"Equipe não encontrada na liga: {typed}")


def selection_name(side: str, home: str, away: str) -> str:
    return {
        "H": home,
        "D": "Empate",
        "A": away,
        "O25": "Mais de 2,5 gols",
        "U25": "Menos de 2,5 gols",
    }.get(str(side), str(side))


def market_name(market: str) -> str:
    return {"1X2": "Resultado final", "OU": "Total de gols 2,5"}.get(str(market), str(market))


def enrich_live_evaluation(frame: pd.DataFrame, match_date: date, unit_value: float) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    result = frame.copy()
    result["DateParsed"] = pd.Timestamp(match_date)
    result["WeekID"] = f"{match_date.isocalendar().year}-{match_date.isocalendar().week:02d}"
    result["MatchID"] = (
        result["League"].astype(str)
        + "|" + result["DateParsed"].dt.date.astype(str)
        + "|" + result["Home"].astype(str)
        + "|" + result["Away"].astype(str)
    )
    result["BreakEvenProbability"] = 1.0 / result["ExecutableOdd"]
    result["SportsEV"] = result["SportsProbability"] * result["ExecutableOdd"] - 1.0
    result["HistoricalPriceEV"] = result["HistoricalHitRate"] * result["ExecutableOdd"] - 1.0
    result["FairOddSports"] = 1.0 / result["SportsProbability"].clip(lower=1e-9)
    result["Selection"] = [selection_name(side, home, away) for side, home, away in zip(result["Side"], result["Home"], result["Away"])]
    result["MarketName"] = result["Market"].map(market_name)
    result["Stake"] = float(unit_value)
    result["Decision"] = np.where(result["Status"].eq("APROVADA"), "CANDIDATA", "DESCARTAR")
    result["Reason"] = np.where(
        result["Status"].eq("APROVADA"),
        "Faixa histórica aprovada pela regra congelada da V25.",
        np.where(
            result["SportsEV"] >= OP_CFG.reserve_ev_threshold,
            "Valor esportivo calculado, mas sem aprovação histórica da faixa.",
            "Sem aprovação histórica e sem vantagem operacional suficiente.",
        ),
    )
    return result


def choose_one_per_match(evaluations: pd.DataFrame) -> pd.DataFrame:
    """Escolhe no máximo uma candidata por partida, com a regra original da V25."""
    if evaluations.empty:
        return evaluations.copy()
    candidates = evaluations[evaluations["Decision"].eq("CANDIDATA")].copy()
    if candidates.empty:
        return candidates
    return (
        candidates.sort_values(
            ["MatchID", "MarketProbability", "HistoricalHitRate", "HistoricalROI"],
            ascending=[True, False, False, False],
        )
        .drop_duplicates("MatchID")
        .reset_index(drop=True)
    )


def select_weekly_portfolio(evaluations: pd.DataFrame, weekly_top_n: int = 4) -> pd.DataFrame:
    """Aplica a carteira semanal validada: uma por jogo e até N por semana."""
    chosen = choose_one_per_match(evaluations)
    if chosen.empty:
        return chosen
    chosen = chosen.sort_values(
        ["WeekID", "MarketProbability", "HistoricalHitRate", "HistoricalROI"],
        ascending=[True, False, False, False],
    ).copy()
    chosen["WeeklyRank"] = chosen.groupby("WeekID").cumcount() + 1
    chosen["Decision"] = np.where(chosen["WeeklyRank"] <= int(weekly_top_n), "OPERAR", "RESERVA")
    chosen["Reason"] = np.where(
        chosen["Decision"].eq("OPERAR"),
        "Selecionada pela carteira semanal: uma por jogo e dentro do limite semanal.",
        "Faixa aprovada, mas ficou abaixo do limite de posições da semana.",
    )
    return chosen.reset_index(drop=True)


def analyze_batch(
    batch: pd.DataFrame,
    matches: list[dict[str, Any]],
    zone_metrics: pd.DataFrame,
    bankroll: float,
    unit_fraction: float = OP_CFG.unit_fraction,
    weekly_top_n: int = OP_CFG.weekly_top_n,
    cfg: V25Config = CFG,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Analisa um lote e devolve carteira semanal e diagnóstico de cada linha."""
    if batch.empty:
        return pd.DataFrame(), pd.DataFrame()
    unit_value = max(0.0, float(bankroll) * float(unit_fraction))
    teams = team_names_by_league(matches)
    state_cache: dict[str, dict[str, Any]] = {}
    evaluations: list[pd.DataFrame] = []
    diagnostics: list[dict[str, Any]] = []

    for row_index, row in batch.reset_index(drop=True).iterrows():
        visible_index = row_index + 1
        try:
            code = league_code(row.get("Liga"))
            if not code:
                raise ValueError(f"Liga não reconhecida: {_text(row.get('Liga'))}")
            match_date = parse_date_br(row.get("Data"))
            home = resolve_team(code, row.get("Mandante"), teams)
            away = resolve_team(code, row.get("Visitante"), teams)
            if home == away:
                raise ValueError("Mandante e visitante não podem ser a mesma equipe.")

            odds = {
                "H": parse_odd(row.get("Cotação mandante"), row.get("Prob. bruta mandante %")),
                "D": parse_odd(row.get("Cotação empate"), row.get("Prob. bruta empate %")),
                "A": parse_odd(row.get("Cotação visitante"), row.get("Prob. bruta visitante %")),
            }
            if not all(odds[key] and odds[key] > 1.0 for key in ("H", "D", "A")):
                raise ValueError("As três cotações de resultado final são obrigatórias e devem ser maiores que 1,00.")

            over = parse_odd(row.get("Cotação mais de 2,5"), row.get("Prob. bruta mais de 2,5 %"))
            under = parse_odd(row.get("Cotação menos de 2,5"), row.get("Prob. bruta menos de 2,5 %"))
            if over and under:
                odds.update({"O25": over, "U25": under})

            key = match_date.isoformat()
            if key not in state_cache:
                before = [item for item in matches if item["DateParsed"] < match_date]
                state_cache[key] = build_current_state(before, cfg)
            sports = sports_probabilities_for_match(code, home, away, state_cache[key], cfg)
            season = season_for_match(code, match_date)
            evaluated = evaluate_live_market(code, season, home, away, odds, odds, sports, zone_metrics, cfg)
            evaluated = enrich_live_evaluation(evaluated, match_date, unit_value)
            evaluated["InputRow"] = visible_index
            evaluated["Source"] = _text(row.get("Casa de apostas")) or "Não informada"
            evaluations.append(evaluated)
            diagnostics.append({
                "Linha": visible_index,
                "Liga": LEAGUES[code],
                "Data": match_date.strftime("%d/%m/%Y"),
                "Mandante": home,
                "Visitante": away,
                "Situação": "ANALISADA",
                "Detalhe": f"{len(evaluated)} mercados avaliados.",
            })
        except Exception as exc:
            diagnostics.append({
                "Linha": visible_index,
                "Liga": _text(row.get("Liga")),
                "Data": _text(row.get("Data")),
                "Mandante": _text(row.get("Mandante")),
                "Visitante": _text(row.get("Visitante")),
                "Situação": "ERRO",
                "Detalhe": str(exc),
            })

    all_evaluations = pd.concat(evaluations, ignore_index=True) if evaluations else pd.DataFrame()
    portfolio = select_weekly_portfolio(all_evaluations, weekly_top_n)
    return portfolio, pd.DataFrame(diagnostics)


def operational_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    columns = [
        "Decision", "WeekID", "DateParsed", "League", "Home", "Away", "MarketName",
        "Selection", "ExecutableOdd", "MarketProbability", "SportsProbability",
        "HistoricalHitRate", "HistoricalROI", "HistoricalBets", "Stake", "WeeklyRank", "Reason",
    ]
    available = [column for column in columns if column in frame.columns]
    return frame[available].copy()


BATCH_TEXT_COLUMNS = [
    "Data", "Liga", "Mandante", "Visitante", "Casa de apostas",
]

BATCH_ODD_COLUMNS = [
    "Cotação mandante", "Cotação empate", "Cotação visitante",
    "Cotação mais de 2,5", "Cotação menos de 2,5",
]

BATCH_COLUMNS = BATCH_TEXT_COLUMNS + BATCH_ODD_COLUMNS


def empty_batch(rows: int = 12) -> pd.DataFrame:
    """Cria o editor semanal com tipos explícitos.

    Pandas 3 passou a inferir texto como ArrowStringArray. Uma tabela criada
    apenas com strings recusava a inserção posterior de odds numéricas. Aqui,
    textos ficam como object e odds como float64, evitando o TypeError tanto
    no modelo CSV quanto no editor do Streamlit.
    """
    rows = max(int(rows), 0)
    data: dict[str, pd.Series] = {
        column: pd.Series([""] * rows, dtype=object)
        for column in BATCH_TEXT_COLUMNS
    }
    data.update({
        column: pd.Series([np.nan] * rows, dtype="float64")
        for column in BATCH_ODD_COLUMNS
    })
    return pd.DataFrame(data, columns=BATCH_COLUMNS)
