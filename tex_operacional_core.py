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
        self.sports_details: dict[tuple[str, str, str, str, float], dict[str, Any]] = {}
        self.market_details: dict[tuple[str, str, str, str, float], dict[str, Any]] = {}
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
            calibrated = float(row.CalibratedProbability)
            reliability = float(row.Reliability)
            sample = int(row.Sample)
            level = str(getattr(row, "Level", "GLOBAL"))
            self.sports[key] = (calibrated, reliability, sample, level)
            self.sports_details[key] = {
                "CalibratedProbability": calibrated,
                "Reliability": reliability,
                "Sample": sample,
                "Wins": int(getattr(row, "Wins", 0) or 0),
                "EmpiricalHit": float(getattr(row, "EmpiricalHit", calibrated) or calibrated),
                "RawMean": float(getattr(row, "RawMean", calibrated) or calibrated),
                "Level": level,
            }

    def _load_market(self, frame: pd.DataFrame) -> None:
        for row in frame.fillna("").itertuples(index=False):
            key = (
                str(getattr(row, "Level", "")),
                str(getattr(row, "Code", "")),
                str(row.Market),
                str(row.Side),
                round(float(row.MPBin), 3),
            )
            calibrated = float(row.CalibratedMarketP)
            reliability = float(row.Reliability)
            sample = int(row.Sample)
            level = str(getattr(row, "Level", "GLOBAL"))
            self.market[key] = (calibrated, reliability, sample, level)
            self.market_details[key] = {
                "CalibratedProbability": calibrated,
                "Reliability": reliability,
                "Sample": sample,
                "Wins": int(getattr(row, "Wins", 0) or 0),
                "EmpiricalHit": float(getattr(row, "EmpiricalHit", calibrated) or calibrated),
                "AverageOdd": float(getattr(row, "AverageOdd", 0.0) or 0.0),
                "MarketMean": float(getattr(row, "MarketMean", calibrated) or calibrated),
                "Level": level,
            }

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

    def sports_profile(self, code: str, market: str, side: str, probability: float) -> dict[str, Any]:
        bin_value = self._bin(probability, 0.05)
        key = ("LEAGUE", code, market, side, bin_value)
        fallback = ("GLOBAL", "", market, side, bin_value)
        return dict(self.sports_details.get(key, self.sports_details.get(fallback, {
            "CalibratedProbability": probability, "Reliability": 0.10, "Sample": 0,
            "Wins": 0, "EmpiricalHit": probability, "RawMean": probability, "Level": "RAW",
        })))

    def market_profile(self, code: str, market: str, side: str, probability: float) -> dict[str, Any]:
        bin_value = self._bin(probability, 0.025)
        key = ("LEAGUE", code, market, side, bin_value)
        fallback = ("GLOBAL", "", market, side, bin_value)
        return dict(self.market_details.get(key, self.market_details.get(fallback, {
            "CalibratedProbability": probability, "Reliability": 0.10, "Sample": 0,
            "Wins": 0, "EmpiricalHit": probability, "AverageOdd": 0.0,
            "MarketMean": probability, "Level": "RAW",
        })))


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


def sample_confidence_label(sample: int, reliability: float) -> tuple[str, str]:
    """Classifica a qualidade da amostra sem esconder os números usados."""
    if sample >= 500 and reliability >= 0.70:
        return "FORTE", f"{sample} registros e estabilidade de calibração {reliability:.0%}."
    if sample >= 150 and reliability >= 0.35:
        return "MODERADA", f"{sample} registros e estabilidade de calibração {reliability:.0%}."
    return "FRACA", f"{sample} registros e estabilidade de calibração {reliability:.0%}."


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
        sports_profile = book.sports_profile(code, market, side, raw_sports)
        calibrated_sports = float(sports_profile["CalibratedProbability"])
        sports_reliability = float(sports_profile["Reliability"])
        sports_sample = int(sports_profile["Sample"])
        sports_level = str(sports_profile["Level"])

        if market == "BTTS":
            calibrated_market = market_probability
            market_reliability = sports_reliability
            market_sample = sports_sample
            market_level = "SEM_ODDS_HISTÓRICAS"
            market_profile = {
                "EmpiricalHit": float(sports_profile["EmpiricalHit"]),
                "Wins": int(sports_profile["Wins"]),
                "AverageOdd": 0.0,
            }
            # BTTS tem calibração esportiva histórica, mas não há odds históricas
            # completas nas 24 ligas. O mercado atual permanece a âncora.
            decision_probability = 0.80 * calibrated_market + 0.20 * calibrated_sports
        else:
            market_profile = book.market_profile(code, market, side, market_probability)
            calibrated_market = float(market_profile["CalibratedProbability"])
            market_reliability = float(market_profile["Reliability"])
            market_sample = int(market_profile["Sample"])
            market_level = str(market_profile["Level"])
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

        sample_confidence, sample_confidence_reason = sample_confidence_label(int(profile_sample), float(reliability))
        required_odd = (1.0 + min_ev) / max(decision_probability, 1e-9)
        odd_gap = odd - required_odd
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
                "ProfileWins": int(market_profile.get("Wins", 0)),
                "EmpiricalHitRate": float(market_profile.get("EmpiricalHit", calibrated_market)),
                "AverageHistoricalOdd": float(market_profile.get("AverageOdd", 0.0)),
                "Reliability": reliability,
                "SampleConfidence": sample_confidence,
                "SampleConfidenceReason": sample_confidence_reason,
                "SportsSample": int(sports_sample),
                "SportsReliability": float(sports_reliability),
                "SportsEmpiricalHitRate": float(sports_profile.get("EmpiricalHit", calibrated_sports)),
                "ProfileLevel": market_level,
                "SportsProfileLevel": sports_level,
                "Confidence": confidence,
                "RequiredOddForOperation": float(required_odd),
                "OddGapToOperation": float(odd_gap),
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
        "EmpiricalHitRate",
        "SampleConfidence",
        "Reliability",
        "RequiredOddForOperation",
        "OddGapToOperation",
        "Stake",
        "Reason",
    ]
    out = out[[column for column in columns if column in out.columns]]
    if "DateParsed" in out:
        out["DateParsed"] = pd.to_datetime(out["DateParsed"]).dt.strftime("%d/%m/%Y")
    for percentage_column in ("DecisionProbability", "BreakEvenProbability", "ExpectedValue", "EmpiricalHitRate", "Reliability"):
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
        "Confidence": "Confiança da leitura",
        "ProfileSample": "Amostra histórica",
        "EmpiricalHitRate": "Acerto empírico da faixa",
        "SampleConfidence": "Confiança da amostra",
        "Reliability": "Estabilidade da calibração",
        "RequiredOddForOperation": "Odd mínima para operar",
        "OddGapToOperation": "Diferença para odd mínima",
        "Stake": "Entrada fixa",
        "Reason": "Motivo",
    }
    return out.rename(columns=rename)

def standings_before_match(matches: list[dict[str, Any]], code: str, match_date: date) -> pd.DataFrame:
    """Reconstrói a classificação da temporada corrente usando apenas jogos anteriores à partida."""
    season = season_for_match(code, match_date)
    table: dict[str, dict[str, float]] = {}

    def row_for(team: str) -> dict[str, float]:
        if team not in table:
            table[team] = {
                "Jogos": 0, "Vitórias": 0, "Empates": 0, "Derrotas": 0,
                "Gols marcados": 0, "Gols sofridos": 0, "Pontos": 0,
            }
        return table[team]

    season_matches = sorted(
        (m for m in matches if m.get("Code") == code and int(m.get("Season", -1)) == season
         and m.get("DateParsed") < match_date),
        key=lambda item: item.get("DateParsed"),
    )
    for match in season_matches:
        home = clean_text(match.get("Home")); away = clean_text(match.get("Away"))
        hg = int(match.get("HG", 0)); ag = int(match.get("AG", 0))
        h = row_for(home); a = row_for(away)
        h["Jogos"] += 1; a["Jogos"] += 1
        h["Gols marcados"] += hg; h["Gols sofridos"] += ag
        a["Gols marcados"] += ag; a["Gols sofridos"] += hg
        if hg > ag:
            h["Vitórias"] += 1; a["Derrotas"] += 1; h["Pontos"] += 3
        elif ag > hg:
            a["Vitórias"] += 1; h["Derrotas"] += 1; a["Pontos"] += 3
        else:
            h["Empates"] += 1; a["Empates"] += 1; h["Pontos"] += 1; a["Pontos"] += 1

    rows: list[dict[str, Any]] = []
    for team, values in table.items():
        games = int(values["Jogos"])
        if games <= 0:
            continue
        rows.append({
            "Equipe": team, **values,
            "Saldo": int(values["Gols marcados"] - values["Gols sofridos"]),
            "Pontos por jogo": float(values["Pontos"] / games),
            "Gols por jogo": float(values["Gols marcados"] / games),
            "Gols sofridos por jogo": float(values["Gols sofridos"] / games),
            "Temporada": season,
        })
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows).sort_values(
        ["Pontos", "Vitórias", "Saldo", "Gols marcados"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    frame.insert(0, "Posição", np.arange(1, len(frame) + 1))
    return frame


def standings_context(matches: list[dict[str, Any]], code: str, match_date: date, home: str, away: str) -> dict[str, Any]:
    table = standings_before_match(matches, code, match_date)
    context: dict[str, Any] = {"Available": False, "Table": table, "Season": season_for_match(code, match_date)}
    if table.empty:
        return context
    home_row = table[table["Equipe"].eq(home)]
    away_row = table[table["Equipe"].eq(away)]
    if home_row.empty or away_row.empty:
        return context
    h = home_row.iloc[0]; a = away_row.iloc[0]
    context.update({
        "Available": True,
        "HomePosition": int(h["Posição"]), "AwayPosition": int(a["Posição"]),
        "HomePoints": int(h["Pontos"]), "AwayPoints": int(a["Pontos"]),
        "HomeGames": int(h["Jogos"]), "AwayGames": int(a["Jogos"]),
        "HomePPG": float(h["Pontos por jogo"]), "AwayPPG": float(a["Pontos por jogo"]),
        "HomeGFPG": float(h["Gols por jogo"]), "AwayGFPG": float(a["Gols por jogo"]),
        "HomeGAPG": float(h["Gols sofridos por jogo"]), "AwayGAPG": float(a["Gols sofridos por jogo"]),
    })
    return context


def build_ai_summary(
    games: pd.DataFrame,
    readings: pd.DataFrame,
    evaluations: pd.DataFrame,
    diagnostics: pd.DataFrame,
    matches: list[dict[str, Any]],
) -> str:
    """Gera um relatório copiável com tudo o que outra IA precisa para revisar o lote."""
    lines = [
        f"RESUMO PARA ANÁLISE EXTERNA — {APP_NAME}",
        f"Partidas informadas: {len(games)} | partidas analisadas: {readings['MatchID'].nunique() if not readings.empty else 0} | mercados avaliados: {len(evaluations)}",
        "A entrada operacional é separada da leitura estatística. A ausência de entrada não elimina a análise do jogo.",
        "",
    ]
    if not diagnostics.empty:
        errors = diagnostics[diagnostics["Situação"].ne("ANALISADO")]
        for row in errors.itertuples(index=False):
            lines.append(f"ERRO — {row.Jogo}: {row.Detalhe}")
        if not errors.empty:
            lines.append("")

    for game in games.itertuples(index=False):
        code = str(getattr(game, "_3", getattr(game, "Código_da_liga", "")))
        # itertuples renomeia colunas com espaços; usa o ID para localizar a leitura com segurança.
        input_id = str(getattr(game, "ID"))
        game_reading = readings[readings["InputID"].eq(input_id)] if not readings.empty else pd.DataFrame()
        game_evals = evaluations[evaluations["InputID"].eq(input_id)] if not evaluations.empty else pd.DataFrame()
        source_row = games[games["ID"].astype(str).eq(input_id)].iloc[0]
        code = str(source_row["Código da liga"])
        match_date = parse_date(source_row["Data"])
        home = str(source_row["Mandante"]); away = str(source_row["Visitante"])
        context = standings_context(matches, code, match_date, home, away)
        lines.append(f"JOGO: {home} x {away}")
        lines.append(f"Liga: {source_row['Liga']} | Data: {match_date.strftime('%d/%m/%Y')} | Hora: {source_row['Hora']} | Casa: {source_row['Casa de apostas']}")
        if context.get("Available"):
            lines.append(
                f"Classificação antes do jogo: {home} {context['HomePosition']}º ({context['HomePoints']} pts em {context['HomeGames']} jogos, {context['HomePPG']:.2f} PPG) | "
                f"{away} {context['AwayPosition']}º ({context['AwayPoints']} pts em {context['AwayGames']} jogos, {context['AwayPPG']:.2f} PPG)."
            )
        else:
            lines.append(f"Classificação antes do jogo: indisponível para a temporada {context.get('Season')}.")
        if game_reading.empty:
            lines.append("Leitura principal: indisponível.")
        else:
            r = game_reading.iloc[0]
            lines.append(
                f"Leitura principal: {r['Selection']} | status {r['Status']} | odd {r['Odd']:.2f} | "
                f"prob. operacional {r['DecisionProbability']:.1%} | prob. mercado sem margem {r['MarketProbability']:.1%} | "
                f"prob. esportiva calibrada {r['CalibratedSportsProbability']:.1%}."
            )
            lines.append(
                f"Amostra: {int(r['ProfileSample'])} registros | acerto empírico {r['EmpiricalHitRate']:.1%} | "
                f"confiança da amostra {r['SampleConfidence']} | estabilidade {r['Reliability']:.1%}."
            )
            lines.append(
                f"Preço: odd mínima operacional {r['RequiredOddForOperation']:.2f} | diferença da odd atual {r['OddGapToOperation']:+.2f} | "
                f"margem estimada {r['ExpectedValue']:.1%}. Motivo: {r['Reason']}"
            )
            lines.append(f"Gols projetados: {home} {r['LambdaHome']:.2f} x {r['LambdaAway']:.2f} {away}.")
        if not game_evals.empty:
            lines.append("Todos os mercados:")
            ordered = game_evals.sort_values(["StatusOrder", "Score"], ascending=[True, False])
            for _, row in ordered.iterrows():
                lines.append(
                    f"- {row['Selection']}: status {row['Status']}; odd {row['Odd']:.2f}; prob. operacional {row['DecisionProbability']:.1%}; "
                    f"mercado {row['MarketProbability']:.1%}; esportiva {row['CalibratedSportsProbability']:.1%}; "
                    f"amostra {int(row['ProfileSample'])} ({row['SampleConfidence']}, estabilidade {row['Reliability']:.1%}); "
                    f"odd mínima {row['RequiredOddForOperation']:.2f}; EV {row['ExpectedValue']:.1%}."
                )
        lines.append("")
    lines.append("Observação: o resumo contém apenas dados e cálculos do aplicativo; escalações, lesões e notícias não são incorporadas automaticamente.")
    return "\n".join(lines)



def enrich_with_standings(
    frame: pd.DataFrame,
    games: pd.DataFrame,
    matches: list[dict[str, Any]],
) -> pd.DataFrame:
    """Acrescenta classificação corrente a qualquer quadro de resultados."""
    if frame.empty:
        return frame.copy()
    out = frame.copy()
    contexts: dict[str, dict[str, Any]] = {}
    for _, game in games.iterrows():
        input_id = str(game.get("ID", ""))
        try:
            contexts[input_id] = standings_context(
                matches,
                str(game.get("Código da liga", "")),
                parse_date(game.get("Data")),
                str(game.get("Mandante", "")),
                str(game.get("Visitante", "")),
            )
        except Exception:
            contexts[input_id] = {"Available": False}
    mapping = {
        "StandingsAvailable": "Available",
        "Season": "Season",
        "HomePosition": "HomePosition",
        "AwayPosition": "AwayPosition",
        "HomePoints": "HomePoints",
        "AwayPoints": "AwayPoints",
        "HomeGames": "HomeGames",
        "AwayGames": "AwayGames",
        "HomePPG": "HomePPG",
        "AwayPPG": "AwayPPG",
        "HomeGFPG": "HomeGFPG",
        "AwayGFPG": "AwayGFPG",
        "HomeGAPG": "HomeGAPG",
        "AwayGAPG": "AwayGAPG",
    }
    for target, source in mapping.items():
        out[target] = out["InputID"].astype(str).map(lambda key: contexts.get(key, {}).get(source, np.nan))
    return out
