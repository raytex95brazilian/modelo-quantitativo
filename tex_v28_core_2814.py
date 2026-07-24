from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
import hashlib
import json
import math

import numpy as np
import pandas as pd

from tex_v25_core import CFG, LEAGUES, V25Config, build_current_state, no_vig_probabilities, sports_probabilities_for_match
from tex_operacional_core import (
    INPUT_COLUMNS,
    clean_text,
    enrich_with_standings,
    latest_team_catalog,
    parse_date,
    parse_odd,
    season_for_match,
    standings_context,
)

APP_NAME = "Tex Statistics V28.1.4.3 — Faixa de cotação controlada"
CORE_API_VERSION = "28.1.4.3"
MODEL_VERSION = "V28.1.4.3-faixa-150-200"

MARKET_DEFINITIONS = {
    "1X2": {
        "label": "Resultado final 1X2",
        "sides": ["H", "D", "A"],
        "odd_columns": ["Odd mandante", "Odd empate", "Odd visitante"],
        "validated": True,
    },
    "OU25": {
        "label": "Total de gols 2,5",
        "sides": ["O25", "U25"],
        "odd_columns": ["Odd mais de 2,5", "Odd menos de 2,5"],
        "validated": True,
    },
    "BTTS": {
        "label": "Ambas marcam",
        "sides": ["BTTS_Y", "BTTS_N"],
        "odd_columns": ["Odd ambas marcam — Sim", "Odd ambas marcam — Não"],
        "validated": True,
    },
}


@dataclass(frozen=True)
class V28Config:
    unit_fraction: float = 0.01
    target_entries: int = 5
    min_odd: float = 1.50
    max_odd: float = 2.00
    price_haircut: float = 0.02
    minimum_ev: float = 0.0
    near_ev: float = -0.03
    profile_prior_strength: float = 100.0
    minimum_profile_sample: int = 40
    btts_history_limit_per_league: int = 900


V28_CFG = V28Config()


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


def _logit(value: float) -> float:
    p = float(np.clip(value, 1e-6, 1 - 1e-6))
    return math.log(p / (1 - p))


class V28Model:
    def __init__(self, model_file: str | Path, metadata_file: str | Path, reliability_file: str | Path):
        # Inferência pura em Python: evita dependência binária do LightGBM no Streamlit Cloud.
        self.model_dump = json.loads(Path(model_file).read_text(encoding="utf-8"))
        self.trees = [tree["tree_structure"] for tree in self.model_dump["tree_info"]]
        self.metadata = json.loads(Path(metadata_file).read_text(encoding="utf-8"))
        self.feature_order = list(self.metadata["feature_order"])
        self.category_maps = self.metadata["category_maps"]
        self.price_haircut = float(self.metadata.get("price_haircut", 0.02))
        self.min_odd = float(self.metadata.get("min_odd", 1.50))
        self.max_odd = float(self.metadata.get("max_odd", 2.00))
        self.profiles = pd.read_csv(reliability_file)
        self.profiles["ProbBin"] = pd.to_numeric(self.profiles["ProbBin"], errors="coerce").round(2)

    def predict(self, code: str, market: str, side: str, market_probability: float, raw_probability: float, odd: float, month: int) -> float:
        diff = raw_probability - market_probability
        row = {
            "MarketP": market_probability,
            "RawP": raw_probability,
            "diff": diff,
            "absdiff": abs(diff),
            "ratio": raw_probability / max(market_probability, 1e-6),
            "AvgOdd": odd,
            "logit_market": _logit(market_probability),
            "logit_raw": _logit(raw_probability),
            "Month": month,
            "Code_cat": int(self.category_maps.get("Code", {}).get(code, -1)),
            "Market_cat": int(self.category_maps.get("Market", {}).get(market, -1)),
            "Side_cat": int(self.category_maps.get("Side", {}).get(side, -1)),
        }
        values = [float(row[name]) for name in self.feature_order]
        raw_score = sum(self._tree_value(tree, values) for tree in self.trees)
        if raw_score >= 0:
            probability = 1.0 / (1.0 + math.exp(-raw_score))
        else:
            exp_score = math.exp(raw_score)
            probability = exp_score / (1.0 + exp_score)
        return float(np.clip(probability, 0.01, 0.99))

    @staticmethod
    def _tree_value(tree: dict[str, Any], values: list[float]) -> float:
        node = tree
        while "leaf_value" not in node:
            value = values[int(node["split_feature"])]
            missing = value is None or (isinstance(value, float) and math.isnan(value))
            if missing:
                go_left = bool(node.get("default_left", True))
            elif node["decision_type"] == "<=":
                go_left = float(value) <= float(node["threshold"])
            elif node["decision_type"] == "==":
                categories = {int(item) for item in str(node["threshold"]).split("||") if item}
                go_left = int(value) in categories
            else:
                raise ValueError(f"Tipo de decisão desconhecido: {node['decision_type']}")
            node = node["left_child"] if go_left else node["right_child"]
        return float(node["leaf_value"])

    def reliability_profile(self, code: str, market: str, side: str, probability: float) -> dict[str, Any]:
        prob_bin = round(math.floor(float(np.clip(probability, 0, 0.9999)) / 0.05) * 0.05, 2)
        league = self.profiles[
            self.profiles["Level"].eq("LIGA")
            & self.profiles["Code"].fillna("").eq(code)
            & self.profiles["Market"].eq(market)
            & self.profiles["Side"].eq(side)
            & self.profiles["ProbBin"].eq(prob_bin)
        ]
        global_profile = self.profiles[
            self.profiles["Level"].eq("GLOBAL")
            & self.profiles["Market"].eq(market)
            & self.profiles["Side"].eq(side)
            & self.profiles["ProbBin"].eq(prob_bin)
        ]
        # Liga só é usada quando há volume razoável; caso contrário, usa o perfil global.
        if not league.empty and int(league.iloc[0]["Sample"]) >= 100:
            row = league.iloc[0]
        elif not global_profile.empty:
            row = global_profile.iloc[0]
        elif not league.empty:
            row = league.iloc[0]
        else:
            return {
                "Level": "SEM PERFIL", "Sample": 0, "Wins": 0, "MeanPred": probability,
                "HitRate": probability, "Brier": np.nan, "CalibrationGap": np.nan,
                "Confidence": "FRACA", "Reliability": 0.0,
            }
        sample = int(row["Sample"])
        gap = float(row["CalibrationGap"])
        if sample >= 300 and gap <= 0.04:
            confidence = "FORTE"
        elif sample >= 100 and gap <= 0.08:
            confidence = "MODERADA"
        else:
            confidence = "FRACA"
        reliability = float(np.clip(1.0 - gap / 0.15, 0.0, 1.0))
        return {
            "Level": str(row["Level"]), "Sample": sample, "Wins": int(row["Wins"]),
            "MeanPred": float(row["MeanPred"]), "HitRate": float(row["HitRate"]),
            "Brier": float(row["Brier"]), "CalibrationGap": gap,
            "Confidence": confidence, "Reliability": reliability,
        }


def load_v28_model(directory: str | Path) -> V28Model:
    directory = Path(directory)
    return V28Model(
        directory / "tex_v28_lgbm.json",
        directory / "metadata.json",
        directory / "reliability_profiles.csv",
    )


def lot_fingerprint(games: pd.DataFrame) -> str:
    """Hash determinístico do lote inteiro, incluindo todas as cotações.

    Impede que resultados antigos continuem visíveis depois que qualquer jogo,
    equipe, horário ou odd for alterado na interface.
    """
    if games is None or games.empty:
        return hashlib.sha256(b"[]").hexdigest()
    frame = games.reindex(columns=INPUT_COLUMNS).copy()
    records: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        record: dict[str, Any] = {}
        for column in INPUT_COLUMNS:
            value = row.get(column)
            if value is None or (not isinstance(value, (list, dict, tuple)) and pd.isna(value)):
                record[column] = None
            elif isinstance(value, (float, np.floating)):
                record[column] = round(float(value), 8)
            elif isinstance(value, (int, np.integer)):
                record[column] = int(value)
            else:
                record[column] = str(value)
        records.append(record)
    payload = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_market_odds(market: str, odds: list[float]) -> float:
    """Valida coerência matemática da linha antes de retirar a margem.

    Retorna a soma das probabilidades implícitas. Linhas muito abaixo de 100%
    normalmente indicam cotações misturadas entre partidas; linhas extremas
    também são bloqueadas para evitar alimentar o modelo com dados corrompidos.
    """
    if market not in MARKET_DEFINITIONS:
        raise ValueError(f"Mercado desconhecido: {market}.")
    if any((not math.isfinite(float(odd))) or float(odd) <= 1.0 for odd in odds):
        raise ValueError(f"{MARKET_DEFINITIONS[market]['label']}: todas as cotações devem ser maiores que 1,00.")
    implied_sum = sum(1.0 / float(odd) for odd in odds)
    lower, upper = ((0.98, 1.30) if market == "1X2" else (0.98, 1.22))
    if not lower <= implied_sum <= upper:
        raise ValueError(
            f"COTAÇÕES INCONSISTENTES em {MARKET_DEFINITIONS[market]['label']}: "
            f"soma implícita {implied_sum:.2%}; faixa aceita {lower:.0%}–{upper:.0%}. "
            "Revise se alguma cotação pertence a outra partida."
        )
    return implied_sum


def _complete_odds(row: pd.Series, columns: list[str]) -> list[float] | None:
    parsed = [parse_odd(row.get(column)) for column in columns]
    if all(value is None for value in parsed):
        return None
    if any(value is None for value in parsed):
        raise ValueError(f"Preencha todas as cotações do mercado: {', '.join(columns)}.")
    return [float(value) for value in parsed if value is not None]



_BTTS_CALIBRATION_CACHE: dict[tuple[Any, ...], "BttsCalibration"] = {}


def _match_value(match: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in match:
            value = match.get(name)
            if value is not None and not (isinstance(value, float) and math.isnan(value)):
                return value
    return None


def _match_code(match: dict[str, Any]) -> str:
    return clean_text(_match_value(match, "Code", "Código da liga", "LeagueCode", "Div"))


def _match_date(match: dict[str, Any]) -> date | None:
    value = _match_value(match, "DateParsed", "Data", "Date")
    if value is None:
        return None
    try:
        return parse_date(value)
    except Exception:
        return None


def _match_goals(match: dict[str, Any]) -> tuple[int, int] | None:
    home = _match_value(
        match, "FTHG", "HomeGoals", "HG", "GolsMandante", "Gols mandante",
        "HomeScore", "MandanteGols",
    )
    away = _match_value(
        match, "FTAG", "AwayGoals", "AG", "GolsVisitante", "Gols visitante",
        "AwayScore", "VisitanteGols",
    )
    try:
        if home is None or away is None:
            return None
        return int(float(home)), int(float(away))
    except (TypeError, ValueError):
        return None


class BttsCalibration:
    """Calibração de Ambas Marcam feita somente com partidas anteriores.

    As previsões históricas são produzidas em sequência temporal. Cada partida é
    calculada com um estado construído apenas a partir de jogos de datas anteriores.
    """

    def __init__(self, records: list[dict[str, Any]]):
        self.records = pd.DataFrame(records)

    def profile(self, code: str, side: str, probability: float, minimum_sample: int) -> dict[str, Any]:
        if self.records.empty:
            return self._empty(probability)
        base = self.records[self.records["Side"].eq(side)].copy()
        candidates: list[tuple[str, pd.DataFrame]] = []
        league = base[base["Code"].eq(code)]
        global_rows = base
        for radius in (0.025, 0.05, 0.075, 0.10):
            candidates.append(("LIGA", league[(league["Probability"] - probability).abs() <= radius]))
        for radius in (0.025, 0.05, 0.075, 0.10):
            candidates.append(("GERAL", global_rows[(global_rows["Probability"] - probability).abs() <= radius]))

        chosen_level = "SEM PERFIL"
        chosen = pd.DataFrame()
        for level, frame in candidates:
            if len(frame) >= minimum_sample:
                chosen_level, chosen = level, frame
                break
            if len(frame) > len(chosen):
                chosen_level, chosen = level, frame
        if chosen.empty:
            return self._empty(probability)

        sample = int(len(chosen))
        wins = int(chosen["Outcome"].sum())
        mean_pred = float(chosen["Probability"].mean())
        hit_rate = float(wins / sample)
        brier = float(((chosen["Probability"] - chosen["Outcome"]) ** 2).mean())
        gap = abs(hit_rate - mean_pred)
        if sample >= 200 and gap <= 0.05:
            confidence = "FORTE"
        elif sample >= minimum_sample and gap <= 0.10:
            confidence = "MODERADA"
        else:
            confidence = "FRACA"
        sample_strength = sample / (sample + 100.0)
        calibration_strength = float(np.clip(1.0 - gap / 0.15, 0.0, 1.0))
        reliability = float(sample_strength * calibration_strength)
        return {
            "Level": chosen_level,
            "Sample": sample,
            "Wins": wins,
            "MeanPred": mean_pred,
            "HitRate": hit_rate,
            "Brier": brier,
            "CalibrationGap": gap,
            "Confidence": confidence,
            "Reliability": reliability,
        }

    @staticmethod
    def _empty(probability: float) -> dict[str, Any]:
        return {
            "Level": "SEM PERFIL", "Sample": 0, "Wins": 0,
            "MeanPred": probability, "HitRate": probability,
            "Brier": np.nan, "CalibrationGap": np.nan,
            "Confidence": "FRACA", "Reliability": 0.0,
        }


def build_btts_calibration(
    matches: list[dict[str, Any]],
    codes: set[str],
    cutoff: date,
    sports_cfg: V25Config = CFG,
    history_limit_per_league: int = 900,
) -> BttsCalibration:
    """Reconstrói uma calibração temporal para Ambas Marcam.

    O cálculo é limitado às ligas presentes no lote e às partidas anteriores à
    primeira data analisada. O resultado fica em memória durante a execução do app.
    """
    last_date = max((_match_date(item) for item in matches if _match_date(item) is not None), default=None)
    cache_key = (
        id(matches), len(matches), str(last_date), tuple(sorted(codes)), cutoff.isoformat(),
        int(history_limit_per_league),
    )
    cached = _BTTS_CALIBRATION_CACHE.get(cache_key)
    if cached is not None:
        return cached

    records: list[dict[str, Any]] = []
    for code in sorted(codes):
        league_matches = [
            item for item in matches
            if _match_code(item) == code
            and (_match_date(item) is not None and _match_date(item) < cutoff)
            and _match_goals(item) is not None
        ]
        league_matches.sort(key=lambda item: (_match_date(item), clean_text(_match_value(item, "Home", "Mandante"))))
        if not league_matches:
            continue
        sample_matches = league_matches[-int(history_limit_per_league):]
        sample_dates = sorted({_match_date(item) for item in sample_matches if _match_date(item) is not None})
        for current_date in sample_dates:
            previous = [item for item in league_matches if _match_date(item) < current_date]
            if not previous:
                continue
            try:
                state = build_current_state(previous, sports_cfg)
            except Exception:
                continue
            current_matches = [item for item in sample_matches if _match_date(item) == current_date]
            for item in current_matches:
                home = clean_text(_match_value(item, "Home", "Mandante"))
                away = clean_text(_match_value(item, "Away", "Visitante"))
                goals = _match_goals(item)
                if not home or not away or goals is None:
                    continue
                try:
                    sports = sports_probabilities_for_match(code, home, away, state, sports_cfg)
                    probability_yes = float(np.clip(sports["BTTS_Y"], 0.01, 0.99))
                    probability_no = float(np.clip(sports["BTTS_N"], 0.01, 0.99))
                except Exception:
                    continue
                outcome_yes = int(goals[0] > 0 and goals[1] > 0)
                records.append({"Code": code, "Side": "BTTS_Y", "Probability": probability_yes, "Outcome": outcome_yes})
                records.append({"Code": code, "Side": "BTTS_N", "Probability": probability_no, "Outcome": 1 - outcome_yes})

    calibration = BttsCalibration(records)
    _BTTS_CALIBRATION_CACHE[cache_key] = calibration
    return calibration


def adjusted_probability_from_profile(
    base_probability: float,
    profile: dict[str, Any],
    prior_strength: float,
    minimum_sample: int,
) -> float:
    """Combina a previsão atual com o acerto observado fora da amostra.

    A previsão atual funciona como uma informação prévia equivalente a
    ``prior_strength`` observações. Perfis pequenos não alteram a previsão.
    """
    sample = int(profile.get("Sample", 0) or 0)
    wins = int(profile.get("Wins", 0) or 0)
    if sample < int(minimum_sample):
        return float(np.clip(base_probability, 0.01, 0.99))
    posterior = (wins + float(prior_strength) * float(base_probability)) / (sample + float(prior_strength))
    return float(np.clip(posterior, 0.01, 0.99))

def _evaluate_group(
    code: str,
    match_date: date,
    home: str,
    away: str,
    market: str,
    odds: list[float],
    sports: dict[str, float],
    model: V28Model,
    unit_value: float,
    cfg: V28Config,
    btts_calibration: BttsCalibration,
) -> list[dict[str, Any]]:
    definition = MARKET_DEFINITIONS[market]
    market_probabilities = no_vig_probabilities(odds)
    output: list[dict[str, Any]] = []
    for side, odd, market_probability in zip(definition["sides"], odds, market_probabilities):
        raw_probability = float(np.clip(sports[side], 0.01, 0.99))
        if market == "BTTS":
            original_probability = raw_probability
            profile = btts_calibration.profile(
                code, side, original_probability, cfg.minimum_profile_sample
            )
        else:
            original_probability = model.predict(
                code, market, side, market_probability, raw_probability, odd, match_date.month
            )
            profile = model.reliability_profile(code, market, side, original_probability)

        probability = adjusted_probability_from_profile(
            original_probability,
            profile,
            cfg.profile_prior_strength,
            cfg.minimum_profile_sample,
        )
        profile_sample = int(profile.get("Sample", 0) or 0)
        profile_confidence = str(profile.get("Confidence", "FRACA"))
        validated = profile_sample >= cfg.minimum_profile_sample and profile_confidence in ("MODERADA", "FORTE")

        effective_odd = odd * (1.0 - cfg.price_haircut)
        expected_value_original = original_probability * effective_odd - 1.0
        expected_value = probability * effective_odd - 1.0
        required_odd = 1.0 / max((1.0 - cfg.price_haircut) * probability, 1e-9)
        odd_gap = odd - required_odd
        in_odd_range = cfg.min_odd <= odd <= cfg.max_odd

        if not validated:
            status = "SEM VALIDAÇÃO"
            reason = (
                "A seleção foi calculada, mas ainda não possui quantidade e estabilidade histórica "
                "suficientes para ser autorizada."
            )
        elif in_odd_range and expected_value >= cfg.minimum_ev:
            status = "QUALIFICADA"
            reason = (
                "A cotação supera o ponto de equilíbrio após o desconto de 2%, usando a "
                "probabilidade corrigida pelo acerto histórico de previsões semelhantes."
            )
        elif in_odd_range and expected_value >= cfg.near_ev:
            status = "AGUARDAR COTAÇÃO"
            reason = "A análise é próxima do ponto de equilíbrio e precisa de cotação maior."
        elif not in_odd_range:
            status = "FORA DA FAIXA"
            reason = f"Cotação informada fora da faixa autorizada ({cfg.min_odd:.2f} a {cfg.max_odd:.2f})."
        else:
            status = "DESCARTADA"
            reason = "A cotação atual não remunera a probabilidade corrigida pelo histórico."

        output.append({
            "DateParsed": pd.Timestamp(match_date),
            "WeekID": f"{match_date.isocalendar().year}-{match_date.isocalendar().week:02d}",
            "Code": code, "League": LEAGUES[code], "Home": home, "Away": away,
            "MatchID": f"{code}|{match_date.isoformat()}|{home}|{away}",
            "Market": market, "MarketName": definition["label"], "Side": side,
            "Selection": selection_name(side, home, away), "Odd": odd,
            "EffectiveOdd": effective_odd, "PriceHaircut": cfg.price_haircut,
            "MarketProbability": market_probability,
            "CalibratedMarketProbability": market_probability,
            "RawSportsProbability": raw_probability,
            "CalibratedSportsProbability": raw_probability,
            "OriginalProbability": original_probability,
            "DecisionProbability": probability,
            "ModelProbability": original_probability,
            "HistoricalAdjustment": probability - original_probability,
            "BreakEvenProbability": 1.0 / effective_odd,
            "ExpectedValueOriginal": expected_value_original,
            "ExpectedValue": expected_value,
            "RequiredOddForOperation": required_odd,
            "OddGapToOperation": odd_gap,
            "ModelMarketDifference": probability - market_probability,
            "ProfileSample": profile_sample, "ProfileWins": int(profile.get("Wins", 0) or 0),
            "EmpiricalHitRate": float(profile.get("HitRate", probability)),
            "SportsSample": profile_sample,
            "SportsReliability": float(profile.get("Reliability", 0.0)),
            "SportsEmpiricalHitRate": float(profile.get("HitRate", probability)),
            "Reliability": float(profile.get("Reliability", 0.0)),
            "CalibrationGap": profile.get("CalibrationGap", np.nan),
            "Brier": profile.get("Brier", np.nan),
            "SampleConfidence": profile_confidence,
            "SampleConfidenceReason": (
                f"{profile_sample} previsões anteriores semelhantes; diferença de calibração "
                f"{float(profile['CalibrationGap']):.1%}."
                if profile_sample > 0 and pd.notna(profile.get("CalibrationGap"))
                else "Ainda não há histórico suficiente para esta faixa de probabilidade."
            ),
            "ProfileLevel": str(profile.get("Level", "SEM PERFIL")),
            "SportsProfileLevel": str(profile.get("Level", "SEM PERFIL")),
            "Confidence": profile_confidence,
            "Status": status, "StatusBase": status,
            "Stake": unit_value if status == "QUALIFICADA" else 0.0,
            "Score": expected_value,
            "Reason": reason,
            "LambdaHome": float(sports["LambdaHome"]), "LambdaAway": float(sports["LambdaAway"]),
            "ValidatedMarket": validated, "ModelVersion": MODEL_VERSION,
        })
    return output

def analyze_games(
    games: pd.DataFrame,
    matches: list[dict[str, Any]],
    model: V28Model,
    bankroll: float,
    unit_fraction: float = V28_CFG.unit_fraction,
    max_entries: int = V28_CFG.target_entries,
    cfg: V28Config = V28_CFG,
    sports_cfg: V25Config = CFG,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Analisa sete seleções por partida e escolhe no máximo uma por jogo.

    A probabilidade usada para autorizar a entrada é corrigida pelo acerto
    observado em previsões históricas semelhantes. O limite semanal organiza o
    volume, mas nunca cria uma entrada quando o valor esperado é negativo.
    """
    if games.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, empty

    target = int(np.clip(max_entries, 1, 5))
    unit_value = max(0.0, float(bankroll) * float(unit_fraction))
    state_cache: dict[str, dict[str, Any]] = {}
    evaluations: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    valid_dates: list[date] = []
    valid_codes: set[str] = set()
    for _, input_row in games.iterrows():
        try:
            valid_dates.append(parse_date(input_row.get("Data")))
            code = clean_text(input_row.get("Código da liga"))
            if code in LEAGUES:
                valid_codes.add(code)
        except Exception:
            continue
    cutoff = min(valid_dates) if valid_dates else date.today()
    try:
        btts_calibration = build_btts_calibration(
            matches,
            valid_codes,
            cutoff,
            sports_cfg,
            cfg.btts_history_limit_per_league,
        )
    except Exception:
        btts_calibration = BttsCalibration([])

    for _, row in games.reset_index(drop=True).iterrows():
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
                    validate_market_odds(market, odds)
                    groups.append((market, odds))
            if not groups:
                raise ValueError("Informe ao menos um mercado completo: resultado, gols ou ambas marcam.")

            key = match_date.isoformat()
            if key not in state_cache:
                previous = [
                    match for match in matches
                    if (_match_date(match) is not None and _match_date(match) < match_date)
                ]
                state_cache[key] = build_current_state(previous, sports_cfg)
            sports = sports_probabilities_for_match(code, home, away, state_cache[key], sports_cfg)

            start = len(evaluations)
            for market, odds in groups:
                evaluations.extend(
                    _evaluate_group(
                        code, match_date, home, away, market, odds, sports,
                        model, unit_value, cfg, btts_calibration,
                    )
                )
            for item in evaluations[start:]:
                item["InputID"] = clean_text(row.get("ID"))
                item["Time"] = clean_text(row.get("Hora"))
                item["Bookmaker"] = clean_text(row.get("Casa de apostas")) or "Não informada"
            diagnostics.append({
                "Jogo": f"{home} x {away}",
                "Liga": LEAGUES[code],
                "Situação": "ANALISADO",
                "Detalhe": (
                    f"{len(evaluations)-start} seleções avaliadas; resultado final, total de gols "
                    "e ambas marcam concorrem pela melhor entrada do jogo."
                ),
            })
        except Exception as exc:
            diagnostics.append({
                "Jogo": f"{clean_text(row.get('Mandante'))} x {clean_text(row.get('Visitante'))}",
                "Liga": clean_text(row.get("Liga")),
                "Situação": "ERRO",
                "Detalhe": str(exc),
            })

    all_evaluations = pd.DataFrame(evaluations)
    diagnostics_frame = pd.DataFrame(diagnostics)
    if all_evaluations.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, diagnostics_frame

    qualified = all_evaluations[all_evaluations["StatusBase"].eq("QUALIFICADA")].copy()
    best_per_match = (
        qualified.sort_values(
            ["MatchID", "ExpectedValue", "Reliability", "ProfileSample", "DecisionProbability"],
            ascending=[True, False, False, False, False],
        )
        .drop_duplicates("MatchID")
    )
    entries = (
        best_per_match.sort_values(
            ["WeekID", "ExpectedValue", "Reliability", "ProfileSample"],
            ascending=[True, False, False, False],
        )
        .groupby("WeekID", group_keys=False)
        .head(target)
        .copy()
    )
    if not entries.empty:
        entries["Rank"] = entries.groupby("WeekID")["ExpectedValue"].rank(method="first", ascending=False).astype(int)
        entries["Status"] = "AUTORIZADA"
        entries["Stake"] = unit_value
        entries["Reason"] = (
            "Melhor seleção autorizada desta partida, classificada pelo valor esperado corrigido, "
            "estabilidade e quantidade de casos históricos."
        )

    selected_keys = set(zip(entries.get("MatchID", []), entries.get("Side", [])))
    for idx, item in all_evaluations.iterrows():
        selection_key = (item["MatchID"], item["Side"])
        if selection_key in selected_keys:
            all_evaluations.at[idx, "Status"] = "AUTORIZADA"
            all_evaluations.at[idx, "Stake"] = unit_value
            all_evaluations.at[idx, "Reason"] = (
                "Melhor seleção autorizada desta partida após a correção pelo histórico."
            )
        elif item["StatusBase"] == "QUALIFICADA":
            all_evaluations.at[idx, "Status"] = "ALTERNATIVA"
            all_evaluations.at[idx, "Stake"] = 0.0
            all_evaluations.at[idx, "Reason"] = (
                "Possui valor esperado positivo, mas ficou atrás de outra seleção do mesmo jogo "
                "ou do limite semanal de cinco entradas."
            )

    order = {
        "AUTORIZADA": 0,
        "ALTERNATIVA": 1,
        "QUALIFICADA": 1,
        "AGUARDAR COTAÇÃO": 2,
        "DESCARTADA": 3,
        "FORA DA FAIXA": 4,
        "SEM VALIDAÇÃO": 5,
    }
    all_evaluations["StatusOrder"] = all_evaluations["Status"].map(order).fillna(9)
    readings = (
        all_evaluations.sort_values(
            ["MatchID", "StatusOrder", "ExpectedValue", "Reliability", "ProfileSample"],
            ascending=[True, True, False, False, False],
        )
        .drop_duplicates("MatchID")
        .reset_index(drop=True)
    )
    return entries.reset_index(drop=True), readings, all_evaluations.reset_index(drop=True), diagnostics_frame

def display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    cols = [
        "Rank", "Status", "DateParsed", "Time", "League", "Home", "Away",
        "MarketName", "Selection", "Odd", "EffectiveOdd", "OriginalProbability",
        "DecisionProbability", "HistoricalAdjustment", "MarketProbability",
        "RawSportsProbability", "ExpectedValue", "RequiredOddForOperation",
        "OddGapToOperation", "ProfileSample", "EmpiricalHitRate",
        "SampleConfidence", "Reliability", "Stake", "Reason",
    ]
    out = frame[[column for column in cols if column in frame.columns]].copy()
    rename = {
        "Rank": "Ordem",
        "Status": "Situação",
        "DateParsed": "Data",
        "Time": "Hora",
        "League": "Liga",
        "Home": "Mandante",
        "Away": "Visitante",
        "MarketName": "Mercado",
        "Selection": "Seleção",
        "Odd": "Cotação informada",
        "EffectiveOdd": "Cotação após desconto",
        "OriginalProbability": "Probabilidade original",
        "DecisionProbability": "Probabilidade corrigida pelo histórico",
        "HistoricalAdjustment": "Correção histórica",
        "MarketProbability": "Probabilidade do mercado sem margem",
        "RawSportsProbability": "Probabilidade esportiva",
        "ExpectedValue": "Valor esperado após desconto",
        "RequiredOddForOperation": "Cotação mínima",
        "OddGapToOperation": "Folga da cotação",
        "ProfileSample": "Casos históricos semelhantes",
        "EmpiricalHitRate": "Acerto histórico",
        "SampleConfidence": "Confiança da amostra",
        "Reliability": "Estabilidade histórica",
        "Stake": "Valor da entrada",
        "Reason": "Motivo",
    }
    return out.rename(columns=rename)


def build_ai_summary(
    games: pd.DataFrame,
    readings: pd.DataFrame,
    evaluations: pd.DataFrame,
    diagnostics: pd.DataFrame,
    matches: list[dict[str, Any]],
) -> str:
    lines = [
        f"RESUMO PARA IA — {APP_NAME}",
        "Arquitetura: probabilidades do mercado sem margem, modelo esportivo, modelo de árvores e correção pelo acerto histórico.",
        "Protocolo: somente cotações entre 1,50 e 2,00 podem ser autorizadas; a cotação recebe desconto operacional de 2%; resultado final, total de gols e ambas marcam concorrem entre si; no máximo uma seleção por partida e cinco por semana.",
        "A autorização exige valor esperado não negativo, quantidade histórica mínima e confiança moderada ou forte.",
        f"Partidas: {len(games)} | leituras principais: {len(readings)} | seleções avaliadas: {len(evaluations)}",
        "",
    ]
    for _, game in games.iterrows():
        input_id = str(game.get("ID", ""))
        home = str(game.get("Mandante", ""))
        away = str(game.get("Visitante", ""))
        code = str(game.get("Código da liga", ""))
        match_date = parse_date(game.get("Data"))
        context = standings_context(matches, code, match_date, home, away)
        lines.append(
            f"JOGO: {home} x {away} | {game.get('Liga', '')} | "
            f"{match_date.strftime('%d/%m/%Y')} {game.get('Hora', '')}"
        )
        if context.get("Available"):
            lines.append(
                f"Classificação: {home} {context['HomePosition']}º, {context['HomePoints']} pontos, "
                f"{context['HomePPG']:.2f} pontos por jogo | {away} {context['AwayPosition']}º, "
                f"{context['AwayPoints']} pontos, {context['AwayPPG']:.2f} pontos por jogo."
            )
        reading = readings[readings["InputID"].astype(str).eq(input_id)] if not readings.empty else pd.DataFrame()
        if not reading.empty:
            row = reading.iloc[0]
            lines.append(
                f"Leitura principal: {row['Selection']} | {row['Status']} | cotação {row['Odd']:.2f} | "
                f"cotação após desconto {row['EffectiveOdd']:.2f} | probabilidade original "
                f"{row['OriginalProbability']:.1%} | probabilidade corrigida {row['DecisionProbability']:.1%} | "
                f"acerto histórico {row['EmpiricalHitRate']:.1%} | valor esperado {row['ExpectedValue']:.1%} | "
                f"cotação mínima {row['RequiredOddForOperation']:.2f}."
            )
            lines.append(
                f"Casos históricos semelhantes: {int(row['ProfileSample'])}; confiança "
                f"{row['SampleConfidence']}; estabilidade {row['Reliability']:.1%}."
            )
        game_evaluations = (
            evaluations[evaluations["InputID"].astype(str).eq(input_id)]
            if not evaluations.empty else pd.DataFrame()
        )
        for _, evaluated in game_evaluations.sort_values(
            ["StatusOrder", "ExpectedValue", "Reliability"], ascending=[True, False, False]
        ).iterrows():
            lines.append(
                f"- {evaluated['Selection']}: {evaluated['Status']}; cotação {evaluated['Odd']:.2f}; "
                f"probabilidade original {evaluated['OriginalProbability']:.1%}; probabilidade corrigida "
                f"{evaluated['DecisionProbability']:.1%}; valor esperado {evaluated['ExpectedValue']:.1%}; "
                f"cotação mínima {evaluated['RequiredOddForOperation']:.2f}; "
                f"casos históricos {int(evaluated['ProfileSample'])}."
            )
        lines.append("")
    if not diagnostics.empty:
        errors = diagnostics[diagnostics["Situação"].eq("ERRO")]
        for _, row in errors.iterrows():
            lines.append(f"ERRO: {row['Jogo']} — {row['Detalhe']}")
    lines.append(
        "Nota: o limite semanal não cria apostas. Se menos de cinco seleções apresentarem valor esperado "
        "não negativo e histórico suficiente, o aplicativo mostrará menos de cinco."
    )
    return "\n".join(lines)


__all__ = [
    "APP_NAME", "INPUT_COLUMNS", "V28_CFG", "V28Config", "analyze_games",
    "adjusted_probability_from_profile", "build_ai_summary", "build_btts_calibration",
    "display_frame", "enrich_with_standings", "latest_team_catalog", "load_v28_model",
    "lot_fingerprint", "no_vig_probabilities", "parse_odd", "standings_context",
    "validate_market_odds",
]
