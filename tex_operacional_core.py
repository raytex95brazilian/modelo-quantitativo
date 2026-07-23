from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
import math
import re
import unicodedata

import numpy as np
import pandas as pd

from tex_v25_core import (
    ANNUAL_CODES,
    CFG,
    LEAGUES,
    V25Config,
    build_current_state,
    no_vig_probabilities,
    sports_probabilities_for_match,
)

APP_NAME = "Tex Statistics — Operacional Reconstruído"


@dataclass(frozen=True)
class OperationalConfig:
    unit_fraction: float = 0.01
    max_entries: int = 4
    max_odd: float = 3.00
    min_profile_sample: int = 150
    min_sports_profile_sample_btts: int = 250
    min_reliability: float = 0.15
    min_probability_1x2: float = 0.50
    min_probability_ou25: float = 0.55
    min_probability_btts: float = 0.52
    min_ev_1x2: float = 0.02
    min_ev_ou25: float = 0.04
    min_ev_btts: float = 0.04
    max_negative_model_disagreement: float = 0.15


OP_CFG = OperationalConfig()

MARKET_DEFINITIONS = {
    "1X2": {
        "label": "Resultado final 1X2",
        "sides": ["H", "D", "A"],
        "odd_columns": ["Odd mandante", "Odd empate", "Odd visitante"],
    },
    "OU25": {
        "label": "Total de gols 2,5",
        "sides": ["O25", "U25"],
        "odd_columns": ["Odd mais de 2,5", "Odd menos de 2,5"],
    },
    "BTTS": {
        "label": "Ambas marcam",
        "sides": ["BTTS_Y", "BTTS_N"],
        "odd_columns": ["Odd ambas marcam — Sim", "Odd ambas marcam — Não"],
    },
}

INPUT_COLUMNS = [
    "ID",
    "Data",
    "Hora",
    "Código da liga",
    "Liga",
    "Mandante",
    "Visitante",
    "Casa de apostas",
    "Odd mandante",
    "Odd empate",
    "Odd visitante",
    "Odd mais de 2,5",
    "Odd menos de 2,5",
    "Odd ambas marcam — Sim",
    "Odd ambas marcam — Não",
]


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\ufeff", "").split())


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", clean_text(value).casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def parse_odd(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = clean_text(value).replace(" ", "").replace(",", ".")
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number <= 1.0 or number > 100.0:
        return None
    return number


def parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    text = clean_text(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        stamp = pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")
    else:
        stamp = pd.to_datetime(text, dayfirst=True, errors="coerce")
    if pd.isna(stamp):
        raise ValueError("Data inválida.")
    return stamp.date()


def season_for_match(code: str, match_date: date) -> int:
    if code in ANNUAL_CODES:
        return match_date.year
    return match_date.year if match_date.month >= 7 else match_date.year - 1


def latest_team_catalog(matches: list[dict[str, Any]]) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Lista os times da temporada mais recente encontrada em cada liga."""
    frame = pd.DataFrame(
        [(m.get("Code"), m.get("Season"), m.get("Home"), m.get("Away")) for m in matches],
        columns=["Code", "Season", "Home", "Away"],
    )
    teams: dict[str, list[str]] = {}
    seasons: dict[str, int] = {}
    for code in LEAGUES:
        subset = frame[frame["Code"].eq(code)].copy()
        if subset.empty:
            teams[code] = []
            continue
        subset["Season"] = pd.to_numeric(subset["Season"], errors="coerce")
        latest = int(subset["Season"].dropna().max())
        current = subset[subset["Season"].eq(latest)]
        names = sorted(
            set(current["Home"].dropna().astype(str))
            | set(current["Away"].dropna().astype(str))
        )
        # Uma temporada recém-iniciada pode conter poucos clubes. Nesse caso,
        # completa o seletor com a temporada anterior, sem exigir digitação.
        if len(names) < 12:
            previous = subset[subset["Season"].eq(latest - 1)]
            names = sorted(
                set(names)
                | set(previous["Home"].dropna().astype(str))
                | set(previous["Away"].dropna().astype(str))
            )
        teams[code] = names
        seasons[code] = latest
    return teams, seasons


class CalibrationBook:
    def __init__(self, sports_profiles: pd.DataFrame, market_profiles: pd.DataFrame):
        self.sports: dict[tuple[str, str, str, str, float], tuple[float, float, int, str]] = {}
        self.market: dict[tuple[str, str, str, str, float], tuple[float, float, int, str]] = {}
        self._load_sports(sports_profiles)
        self._load_market(market_profiles)

    @staticmethod
    def _bin(value: float, width: float) -> float:
        maximum = 1.0 - width
        return round(min(maximum, max(0.0, math.floor(value / width) * width)), 3)

    def _load_sports(self, frame: pd.DataFrame) -> None:
        for row in frame.fillna("").itertuples(index=False):
            key = (
                str(getattr(row, "Level", "")),
                str(getattr(row, "Code", "")),
                str(row.Market),
                str(row.Side),
                round(float(row.Bin), 3),
            )
            self.sports[key] = (
                float(row.CalibratedProbability),
                float(row.Reliability),
                int(row.Sample),
                str(getattr(row, "Level", "GLOBAL")),
            )

    def _load_market(self, frame: pd.DataFrame) -> None:
        for row in frame.fillna("").itertuples(index=False):
            key = (
                str(getattr(row, "Level", "")),
                str(getattr(row, "Code", "")),
                str(row.Market),
                str(row.Side),
                round(float(row.MPBin), 3),
            )
            self.market[key] = (
                float(row.CalibratedMarketP),
                float(row.Reliability),
                int(row.Sample),
                str(getattr(row, "Level", "GLOBAL")),
            )

    def sports_lookup(self, code: str, market: str, side: str, probability: float) -> tuple[float, float, int, str]:
        bin_value = self._bin(probability, 0.05)
        return self.sports.get(
            ("LEAGUE", code, market, side, bin_value),
            self.sports.get(("GLOBAL", "", market, side, bin_value), (probability, 0.10, 0, "RAW")),
        )

    def market_lookup(self, code: str, market: str, side: str, probability: float) -> tuple[float, float, int, str]:
        bin_value = self._bin(probability, 0.025)
        return self.market.get(
            ("LEAGUE", code, market, side, bin_value),
            self.market.get(("GLOBAL", "", market, side, bin_value), (probability, 0.10, 0, "RAW")),
        )


def load_calibration_book(directory: str | Path) -> CalibrationBook:
    directory = Path(directory)
    sports = pd.read_csv(directory / "calibration_profiles.csv")
    market = pd.read_csv(directory / "market_calibration_profiles.csv")
    return CalibrationBook(sports, market)


def selection_name(side: str, home: str, away: str) -> str:
    return {
        "H": home,
        "D": "Empate",
        "A": away,
        "O25": "Mais de 2,5 gols",
        "U25": "Menos de 2,5 gols",
        "BTTS_Y": "Ambas marcam — Sim",
        "BTTS_N": "Ambas marcam — Não",
    }[side]


def thresholds(market: str, cfg: OperationalConfig) -> tuple[float, float]:
    if market == "1X2":
        return cfg.min_probability_1x2, cfg.min_ev_1x2
    if market == "OU25":
        return cfg.min_probability_ou25, cfg.min_ev_ou25
    return cfg.min_probability_btts, cfg.min_ev_btts


def decision_reason(
    market: str,
    odd: float,
    probability: float,
    expected_value: float,
    profile_sample: int,
    reliability: float,
    disagreement: float,
    status: str,
    cfg: OperationalConfig,
) -> str:
    min_probability, min_ev = thresholds(market, cfg)
    failures: list[str] = []
    if odd > cfg.max_odd:
        failures.append(f"odd acima do teto {cfg.max_odd:.2f}")
    if probability < min_probability:
        failures.append(f"probabilidade abaixo de {min_probability:.0%}")
    if expected_value < min_ev:
        failures.append(f"margem de preço abaixo de {min_ev:.0%}")
    if profile_sample < cfg.min_profile_sample:
        failures.append("amostra histórica insuficiente")
    if reliability < cfg.min_reliability:
        failures.append("calibração pouco estável")
    if disagreement < -cfg.max_negative_model_disagreement:
        failures.append("modelo esportivo contradiz fortemente o mercado")
    if status == "OPERAR":
        return "Preço, probabilidade e amostra ultrapassaram as regras fixas."
    if status == "OBSERVAR":
        return "Leitura estatística útil, mas ainda sem preço suficiente para entrada."
    return "; ".join(failures) if failures else "Não atingiu a classificação operacional."


def _evaluate_group(
    code: str,
    match_date: date,
    home: str,
    away: str,
    market: str,
    odds: list[float],
    sports: dict[str, float],
    book: CalibrationBook,
    unit_value: float,
    cfg: OperationalConfig,
) -> list[dict[str, Any]]:
    definition = MARKET_DEFINITIONS[market]
    sides = definition["sides"]
    market_probabilities = no_vig_probabilities(odds)
    rows: list[dict[str, Any]] = []

    for side, odd, market_probability in zip(sides, odds, market_probabilities):
        raw_sports = float(sports[side])
        calibrated_sports, sports_reliability, sports_sample, sports_level = book.sports_lookup(
            code, market, side, raw_sports
        )

        if market == "BTTS":
            calibrated_market = market_probability
            market_reliability = sports_reliability
            market_sample = sports_sample
            market_level = "SEM_ODDS_HISTÓRICAS"
            # BTTS tem calibração esportiva histórica, mas não há odds históricas
            # completas nas 24 ligas. O mercado atual permanece a âncora.
            decision_probability = 0.80 * calibrated_market + 0.20 * calibrated_sports
        else:
            calibrated_market, market_reliability, market_sample, market_level = book.market_lookup(
                code, market, side, market_probability
            )
            disagreement = calibrated_sports - calibrated_market
            # A auditoria da V25 mostrou que o Poisson não pode criar sozinho uma
            # entrada. Ele só ajusta a âncora de mercado de maneira limitada.
            if disagreement < 0:
                adjustment = max(-0.05, 0.25 * disagreement)
            else:
                adjustment = min(0.02, 0.10 * disagreement)
            decision_probability = calibrated_market + adjustment

        decision_probability = float(np.clip(decision_probability, 0.01, 0.99))
        disagreement = calibrated_sports - calibrated_market
        break_even = 1.0 / odd
        expected_value = decision_probability * odd - 1.0
        min_probability, min_ev = thresholds(market, cfg)
        profile_sample = market_sample if market != "BTTS" else sports_sample
        reliability = market_reliability if market != "BTTS" else sports_reliability
        min_sample = cfg.min_profile_sample if market != "BTTS" else cfg.min_sports_profile_sample_btts

        operational = (
            odd <= cfg.max_odd
            and decision_probability >= min_probability
            and expected_value >= min_ev
            and profile_sample >= min_sample
            and reliability >= cfg.min_reliability
            and disagreement >= -cfg.max_negative_model_disagreement
        )
        if operational:
            status = "OPERAR"
        elif expected_value > 0 or decision_probability >= min_probability:
            status = "OBSERVAR"
        else:
            status = "DESCARTAR"

        if decision_probability >= 0.65 and reliability >= 0.30:
            confidence = "FORTE"
        elif decision_probability >= 0.55:
            confidence = "MODERADA"
        else:
            confidence = "BAIXA"

        score = (
            decision_probability
            + 0.20 * reliability
            + 0.50 * max(expected_value, -0.10)
            - (0.04 if market == "OU25" else 0.0)
            - (0.02 if market == "BTTS" else 0.0)
        )

        rows.append(
            {
                "DateParsed": pd.Timestamp(match_date),
                "WeekID": f"{match_date.isocalendar().year}-{match_date.isocalendar().week:02d}",
                "Code": code,
                "League": LEAGUES[code],
                "Home": home,
                "Away": away,
                "MatchID": f"{code}|{match_date.isoformat()}|{home}|{away}",
                "Market": market,
                "MarketName": definition["label"],
                "Side": side,
                "Selection": selection_name(side, home, away),
                "Odd": odd,
                "MarketProbability": market_probability,
                "CalibratedMarketProbability": calibrated_market,
                "RawSportsProbability": raw_sports,
                "CalibratedSportsProbability": calibrated_sports,
                "DecisionProbability": decision_probability,
                "BreakEvenProbability": break_even,
                "ExpectedValue": expected_value,
                "ModelMarketDifference": disagreement,
                "ProfileSample": int(profile_sample),
                "Reliability": reliability,
                "ProfileLevel": market_level,
                "SportsProfileLevel": sports_level,
                "Confidence": confidence,
                "Status": status,
                "Stake": unit_value if operational else 0.0,
                "Score": score,
                "Reason": decision_reason(
                    market,
                    odd,
                    decision_probability,
                    expected_value,
                    int(profile_sample),
                    reliability,
                    disagreement,
                    status,
                    cfg,
                ),
                "LambdaHome": float(sports["LambdaHome"]),
                "LambdaAway": float(sports["LambdaAway"]),
            }
        )
    return rows


def _complete_odds(row: pd.Series, columns: list[str]) -> list[float] | None:
    parsed = [parse_odd(row.get(column)) for column in columns]
    if all(value is None for value in parsed):
        return None
    if any(value is None for value in parsed):
        raise ValueError(f"Preencha todas as odds do mercado: {', '.join(columns)}.")
    return [float(value) for value in parsed if value is not None]


def analyze_games(
    games: pd.DataFrame,
    matches: list[dict[str, Any]],
    book: CalibrationBook,
    bankroll: float,
    unit_fraction: float = OP_CFG.unit_fraction,
    max_entries: int = OP_CFG.max_entries,
    cfg: OperationalConfig = OP_CFG,
    sports_cfg: V25Config = CFG,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Retorna entradas, leitura principal por jogo, todos os mercados e erros."""
    if games.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, empty

    unit_value = max(0.0, float(bankroll) * float(unit_fraction))
    state_cache: dict[str, dict[str, Any]] = {}
    evaluations: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    for position, row in games.reset_index(drop=True).iterrows():
        try:
            code = clean_text(row.get("Código da liga"))
            if code not in LEAGUES:
                raise ValueError("Liga inválida.")
            match_date = parse_date(row.get("Data"))
            home = clean_text(row.get("Mandante"))
            away = clean_text(row.get("Visitante"))
            if not home or not away or home == away:
                raise ValueError("Mandante e visitante devem ser equipes diferentes.")

            groups: list[tuple[str, list[float]]] = []
            for market, definition in MARKET_DEFINITIONS.items():
                odds = _complete_odds(row, definition["odd_columns"])
                if odds is not None:
                    groups.append((market, odds))
            if not groups:
                raise ValueError("Informe ao menos um mercado completo: 1X2, gols ou ambas marcam.")

            cache_key = match_date.isoformat()
            if cache_key not in state_cache:
                previous = [match for match in matches if match["DateParsed"] < match_date]
                state_cache[cache_key] = build_current_state(previous, sports_cfg)
            sports = sports_probabilities_for_match(code, home, away, state_cache[cache_key], sports_cfg)

            before_count = len(evaluations)
            for market, odds in groups:
                evaluations.extend(
                    _evaluate_group(
                        code,
                        match_date,
                        home,
                        away,
                        market,
                        odds,
                        sports,
                        book,
                        unit_value,
                        cfg,
                    )
                )
            for item in evaluations[before_count:]:
                item["InputID"] = clean_text(row.get("ID"))
                item["Time"] = clean_text(row.get("Hora"))
                item["Bookmaker"] = clean_text(row.get("Casa de apostas")) or "Não informada"

            diagnostics.append(
                {
                    "Jogo": f"{home} x {away}",
                    "Liga": LEAGUES[code],
                    "Situação": "ANALISADO",
                    "Detalhe": f"{len(evaluations) - before_count} seleções avaliadas.",
                }
            )
        except Exception as exc:
            diagnostics.append(
                {
                    "Jogo": f"{clean_text(row.get('Mandante'))} x {clean_text(row.get('Visitante'))}",
                    "Liga": clean_text(row.get("Liga")),
                    "Situação": "ERRO",
                    "Detalhe": str(exc),
                }
            )

    all_evaluations = pd.DataFrame(evaluations)
    diagnostics_frame = pd.DataFrame(diagnostics)
    if all_evaluations.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, diagnostics_frame

    order = {"OPERAR": 0, "OBSERVAR": 1, "DESCARTAR": 2}
    all_evaluations["StatusOrder"] = all_evaluations["Status"].map(order).fillna(9)
    readings = (
        all_evaluations.sort_values(
            ["MatchID", "StatusOrder", "Score", "DecisionProbability"],
            ascending=[True, True, False, False],
        )
        .drop_duplicates("MatchID")
        .reset_index(drop=True)
    )

    entries = readings[readings["Status"].eq("OPERAR")].copy()
    if not entries.empty:
        entries = entries.sort_values(
            ["ExpectedValue", "DecisionProbability", "Reliability"],
            ascending=[False, False, False],
        ).head(max(0, int(max_entries)))
        entries["Rank"] = np.arange(1, len(entries) + 1)
        retained = set(entries["MatchID"])
        readings.loc[
            readings["Status"].eq("OPERAR") & ~readings["MatchID"].isin(retained),
            ["Status", "Stake", "Reason"],
        ] = ["RESERVA", 0.0, "Preço aprovado, mas ficou fora do limite de entradas do lote."]

    return entries.reset_index(drop=True), readings, all_evaluations, diagnostics_frame


def display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    out = frame.copy()
    columns = [
        "Status",
        "DateParsed",
        "Time",
        "League",
        "Home",
        "Away",
        "MarketName",
        "Selection",
        "Odd",
        "DecisionProbability",
        "BreakEvenProbability",
        "ExpectedValue",
        "Confidence",
        "ProfileSample",
        "Reliability",
        "Stake",
        "Reason",
    ]
    out = out[[column for column in columns if column in out.columns]]
    if "DateParsed" in out:
        out["DateParsed"] = pd.to_datetime(out["DateParsed"]).dt.strftime("%d/%m/%Y")
    for percentage_column in ("DecisionProbability", "BreakEvenProbability", "ExpectedValue", "Reliability"):
        if percentage_column in out:
            out[percentage_column] = pd.to_numeric(out[percentage_column], errors="coerce") * 100.0
    rename = {
        "DateParsed": "Data",
        "Time": "Hora",
        "League": "Liga",
        "Home": "Mandante",
        "Away": "Visitante",
        "MarketName": "Mercado",
        "Selection": "Seleção",
        "Odd": "Odd",
        "DecisionProbability": "Probabilidade operacional",
        "BreakEvenProbability": "Probabilidade mínima da odd",
        "ExpectedValue": "Margem estimada",
        "Confidence": "Confiança",
        "ProfileSample": "Amostra histórica",
        "Reliability": "Estabilidade",
        "Stake": "Entrada fixa",
        "Reason": "Motivo",
    }
    return out.rename(columns=rename)
