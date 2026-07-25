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

APP_NAME = "Tex Statistics V28.1.2 — Estado Isolado"
CORE_API_VERSION = "28.1.2"
MODEL_VERSION = "V28.0"
ENGINE_VERSION = "V28.1.2-estado-isolado"

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
        "validated": False,
    },
}


@dataclass(frozen=True)
class V28Config:
    unit_fraction: float = 0.01
    max_entries: int = 5
    min_odd: float = 1.20
    max_odd: float = 3.00
    price_haircut: float = 0.02
    minimum_conservative_ev: float = 0.0
    near_conservative_ev: float = -0.03
    minimum_profile_sample: int = 100
    wilson_z: float = 1.2815515655446004


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
        model_path = Path(model_file)
        metadata_path = Path(metadata_file)
        reliability_path = Path(reliability_file)
        missing = [str(path) for path in (model_path, metadata_path, reliability_path) if not path.is_file()]
        if missing:
            raise FileNotFoundError("Arquivos obrigatórios do modelo ausentes: " + ", ".join(missing))

        self.model_dump = json.loads(model_path.read_text(encoding="utf-8"))
        tree_info = self.model_dump.get("tree_info")
        if not isinstance(tree_info, list) or not tree_info:
            raise RuntimeError("O arquivo do modelo não contém árvores válidas.")
        self.trees = [tree["tree_structure"] for tree in tree_info]
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if str(self.metadata.get("model_version", "")) != MODEL_VERSION:
            raise RuntimeError(
                f"Versão do artefato esperada {MODEL_VERSION}; encontrada "
                f"{self.metadata.get('model_version', 'ausente')}."
            )
        self.feature_order = list(self.metadata.get("feature_order") or [])
        if not self.feature_order:
            raise RuntimeError("A ordem das variáveis do modelo está ausente.")
        self.category_maps = self.metadata.get("category_maps") or {}
        for category in ("Code", "Market", "Side"):
            if category not in self.category_maps:
                raise RuntimeError(f"Mapa de categoria ausente no modelo: {category}.")
        self.price_haircut = float(self.metadata.get("price_haircut", 0.02))
        self.min_odd = float(self.metadata.get("min_odd", 1.20))
        self.max_odd = float(self.metadata.get("max_odd", 3.00))
        self.profiles = pd.read_csv(reliability_path)
        required_profile_columns = {
            "Level", "Code", "Market", "Side", "ProbBin", "Sample", "Wins",
            "MeanPred", "HitRate", "Brier", "CalibrationGap",
        }
        missing_profile_columns = required_profile_columns.difference(self.profiles.columns)
        if missing_profile_columns:
            raise RuntimeError(
                "Colunas ausentes nos perfis de confiabilidade: "
                + ", ".join(sorted(missing_profile_columns))
            )
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


def lot_fingerprint(
    games: pd.DataFrame,
    bankroll: float | None = None,
    unit_fraction: float | None = None,
    max_entries: int | None = None,
    existing_week_counts: dict[str, int] | None = None,
    existing_match_ids: set[str] | list[str] | tuple[str, ...] | None = None,
) -> str:
    """Hash determinístico do lote e dos parâmetros que alteram a análise.

    Além das partidas e cotações, inclui banca, percentual da unidade e limite
    semanal quando esses valores são informados. Assim, um resultado calculado
    com parâmetros antigos nunca permanece válido na interface.
    """
    records: list[dict[str, Any]] = []
    if games is not None and not games.empty:
        frame = games.reindex(columns=INPUT_COLUMNS).copy()
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
    parameters = {
        "bankroll": None if bankroll is None else round(float(bankroll), 8),
        "unit_fraction": None if unit_fraction is None else round(float(unit_fraction), 8),
        "max_entries": None if max_entries is None else int(max_entries),
        "existing_week_counts": {
            str(key): int(value)
            for key, value in sorted((existing_week_counts or {}).items())
        },
        "existing_match_ids": sorted(str(value) for value in (existing_match_ids or [])),
    }
    payload = json.dumps(
        {"games": records, "parameters": parameters},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _wilson_lower_bound(wins: int, sample: int, z: float) -> float:
    """Limite inferior conservador para a taxa de acerto de casos semelhantes."""
    n = int(sample)
    if n <= 0:
        return 0.0
    p = float(np.clip(float(wins) / n, 0.0, 1.0))
    denominator = 1.0 + (z * z) / n
    centre = p + (z * z) / (2.0 * n)
    adjustment = z * math.sqrt((p * (1.0 - p) + (z * z) / (4.0 * n)) / n)
    return float(np.clip((centre - adjustment) / denominator, 0.0, 1.0))


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


def _experimental_btts_probability(market_probability: float, raw_probability: float) -> float:
    # BTTS permanece visível, porém fora da carteira validada porque a base histórica
    # não contém odds completas desse mercado. A probabilidade é apenas diagnóstica.
    return float(np.clip(0.65 * market_probability + 0.35 * raw_probability, 0.01, 0.99))


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
) -> list[dict[str, Any]]:
    definition = MARKET_DEFINITIONS[market]
    implied_sum = sum(1.0 / float(value) for value in odds)
    market_margin = max(0.0, implied_sum - 1.0)
    market_probabilities = no_vig_probabilities(odds)
    output: list[dict[str, Any]] = []
    for side, odd, market_probability in zip(definition["sides"], odds, market_probabilities):
        raw_probability = float(sports[side])
        validated = bool(definition["validated"])
        if validated:
            probability = model.predict(code, market, side, market_probability, raw_probability, odd, match_date.month)
            profile = model.reliability_profile(code, market, side, probability)
        else:
            probability = _experimental_btts_probability(market_probability, raw_probability)
            profile = {
                "Level": "EXPERIMENTAL", "Sample": 0, "Wins": 0,
                "MeanPred": probability, "HitRate": probability, "Brier": np.nan,
                "CalibrationGap": np.nan, "Confidence": "NÃO VALIDADA", "Reliability": 0.0,
            }

        profile_sample = int(profile["Sample"])
        profile_wins = int(profile["Wins"])
        if validated and profile_sample > 0:
            similar_cases_lower = _wilson_lower_bound(profile_wins, profile_sample, cfg.wilson_z)
            conservative_probability = min(float(probability), similar_cases_lower)
        else:
            similar_cases_lower = float(probability)
            conservative_probability = float(probability)

        effective_odd = odd * (1.0 - cfg.price_haircut)
        model_expected_value = probability * effective_odd - 1.0
        conservative_expected_value = conservative_probability * effective_odd - 1.0
        required_odd = 1.0 / max((1.0 - cfg.price_haircut) * conservative_probability, 1e-9)
        odd_gap = odd - required_odd
        in_odd_range = cfg.min_odd <= effective_odd <= cfg.max_odd
        sufficient_profile = (
            profile_sample >= cfg.minimum_profile_sample
            and str(profile["Confidence"]) in {"MODERADA", "FORTE"}
        )

        if not validated:
            status = "EXPERIMENTAL"
            reason = (
                "Ambas marcam é analisado como sinal complementar, mas não entra automaticamente "
                "na carteira porque não há histórico completo de cotações para validação financeira equivalente."
            )
        elif not in_odd_range:
            status = "FORA DA FAIXA"
            reason = f"Cotação efetiva fora da faixa testada ({cfg.min_odd:.2f} a {cfg.max_odd:.2f})."
        elif not sufficient_profile:
            status = "AMOSTRA INSUFICIENTE"
            reason = (
                f"Casos semelhantes insuficientes ou instáveis: {profile_sample} registros; "
                f"confiança {profile['Confidence']}."
            )
        elif conservative_expected_value >= cfg.minimum_conservative_ev:
            status = "QUALIFICADA"
            reason = (
                "A cotação supera o preço mínimo calculado com probabilidade conservadora, "
                "casos semelhantes, estabilidade e desconto operacional de 2%."
            )
        elif conservative_expected_value >= cfg.near_conservative_ev:
            status = "AGUARDAR PREÇO"
            reason = "Leitura próxima do ponto de equilíbrio conservador; precisa de cotação maior para entrar."
        else:
            status = "DESCARTAR"
            reason = "A cotação atual não remunera a probabilidade conservadora estimada."

        home_sample = int(sports.get("HomeSample", 0) or 0)
        away_sample = int(sports.get("AwaySample", 0) or 0)
        sports_sample = min(home_sample, away_sample) if home_sample and away_sample else max(home_sample, away_sample)
        sports_reliability = float(np.clip(sports_sample / 20.0, 0.0, 1.0))

        output.append({
            "DateParsed": pd.Timestamp(match_date),
            "WeekID": f"{match_date.isocalendar().year}-{match_date.isocalendar().week:02d}",
            "Code": code, "League": LEAGUES[code], "Home": home, "Away": away,
            "MatchID": f"{code}|{match_date.isoformat()}|{home}|{away}",
            "Market": market, "MarketName": definition["label"], "Side": side,
            "Selection": selection_name(side, home, away), "Odd": odd,
            "EffectiveOdd": effective_odd, "PriceHaircut": cfg.price_haircut,
            "MarketProbability": market_probability,
            "MarketOverround": implied_sum,
            "MarketMargin": market_margin,
            "CalibratedMarketProbability": market_probability,
            "RawSportsProbability": raw_probability,
            "CalibratedSportsProbability": raw_probability,
            "DecisionProbability": probability,
            "ConservativeProbability": conservative_probability,
            "SimilarCasesLowerProbability": similar_cases_lower,
            "ModelProbability": probability,
            "BreakEvenProbability": 1.0 / effective_odd,
            "ModelExpectedValue": model_expected_value,
            "ConservativeExpectedValue": conservative_expected_value,
            "ExpectedValue": conservative_expected_value,
            "RequiredOddForOperation": required_odd,
            "OddGapToOperation": odd_gap,
            "ModelMarketDifference": probability - market_probability,
            "ProfileSample": profile_sample, "ProfileWins": profile_wins,
            "EmpiricalHitRate": float(profile["HitRate"]),
            "HomeSample": home_sample, "AwaySample": away_sample,
            "SportsSample": sports_sample,
            "SportsReliability": sports_reliability,
            "SportsEmpiricalHitRate": raw_probability,
            "Reliability": float(profile["Reliability"]),
            "CalibrationGap": profile["CalibrationGap"], "Brier": profile["Brier"],
            "SampleConfidence": str(profile["Confidence"]),
            "SampleConfidenceReason": (
                f"{profile_sample} previsões fora da amostra; desvio de calibração "
                f"{float(profile['CalibrationGap']):.1%}; limite conservador dos casos semelhantes "
                f"{similar_cases_lower:.1%}." if profile_sample > 0 and pd.notna(profile["CalibrationGap"])
                else "Mercado sem perfil financeiro fora da amostra."
            ),
            "ProfileLevel": str(profile["Level"]),
            "SportsProfileLevel": "AMOSTRA DAS EQUIPES",
            "Confidence": str(profile["Confidence"]),
            "Status": status, "StatusBase": status,
            "Stake": unit_value if status == "QUALIFICADA" else 0.0,
            "Score": conservative_expected_value,
            "Reason": reason,
            "LambdaHome": float(sports["LambdaHome"]), "LambdaAway": float(sports["LambdaAway"]),
            "HomeScoreProbability": float(sports.get("HomeScoreProbability", 1.0 - math.exp(-float(sports["LambdaHome"])))),
            "AwayScoreProbability": float(sports.get("AwayScoreProbability", 1.0 - math.exp(-float(sports["LambdaAway"])))),
            "ValidatedMarket": validated, "ModelVersion": MODEL_VERSION, "CoreVersion": ENGINE_VERSION,
        })
    return output


def analyze_games(
    games: pd.DataFrame,
    matches: list[dict[str, Any]],
    model: V28Model,
    bankroll: float,
    unit_fraction: float = V28_CFG.unit_fraction,
    max_entries: int = V28_CFG.max_entries,
    cfg: V28Config = V28_CFG,
    sports_cfg: V25Config = CFG,
    existing_week_counts: dict[str, int] | None = None,
    existing_match_ids: set[str] | list[str] | tuple[str, ...] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Analisa todos os mercados e monta uma carteira com limite semanal.

    O número informado é apenas um máximo. Entram somente preços aprovados pelo
    filtro conservador, e no máximo uma seleção por partida.
    """
    if games.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, empty

    if not math.isfinite(float(bankroll)) or float(bankroll) < 0.0:
        raise ValueError("A banca deve ser um número não negativo.")
    if not math.isfinite(float(unit_fraction)) or not 0.0 < float(unit_fraction) <= 0.02:
        raise ValueError("A unidade fixa deve ser maior que 0% e no máximo 2% da banca.")
    try:
        target = int(max_entries)
    except (TypeError, ValueError) as exc:
        raise ValueError("O máximo semanal deve ser um número inteiro entre 1 e 5.") from exc
    if not 1 <= target <= 5:
        raise ValueError("O máximo semanal deve estar entre 1 e 5 entradas.")
    registered_by_week: dict[str, int] = {}
    for week, count in (existing_week_counts or {}).items():
        parsed_count = int(count)
        if parsed_count < 0:
            raise ValueError("A contagem semanal de apostas registradas não pode ser negativa.")
        registered_by_week[str(week)] = parsed_count
    registered_matches = {str(value) for value in (existing_match_ids or [])}
    unit_value = float(bankroll) * float(unit_fraction)
    state_cache: dict[str, dict[str, Any]] = {}
    evaluations: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    for _, row in games.reset_index(drop=True).iterrows():
        try:
            code = clean_text(row.get("Código da liga"))
            if code not in LEAGUES:
                raise ValueError("Liga inválida.")
            match_date = parse_date(row.get("Data"))
            home = clean_text(row.get("Mandante")); away = clean_text(row.get("Visitante"))
            if not home or not away or home == away:
                raise ValueError("Mandante e visitante devem ser equipes diferentes.")
            groups: list[tuple[str, list[float]]] = []
            for market, definition in MARKET_DEFINITIONS.items():
                odds = _complete_odds(row, definition["odd_columns"])
                if odds is not None:
                    validate_market_odds(market, odds)
                    groups.append((market, odds))
            if not groups:
                raise ValueError("Informe ao menos um mercado completo: 1X2, gols ou ambas marcam.")

            key = match_date.isoformat()
            if key not in state_cache:
                previous = [match for match in matches if match["DateParsed"] < match_date]
                state_cache[key] = build_current_state(previous, sports_cfg)
            sports = sports_probabilities_for_match(code, home, away, state_cache[key], sports_cfg)

            start = len(evaluations)
            for market, odds in groups:
                evaluations.extend(_evaluate_group(code, match_date, home, away, market, odds, sports, model, unit_value, cfg))
            for item in evaluations[start:]:
                item["InputID"] = clean_text(row.get("ID")) or str(item["MatchID"])
                item["Time"] = clean_text(row.get("Hora"))
                item["Bookmaker"] = clean_text(row.get("Casa de apostas")) or "Não informada"
            diagnostics.append({
                "Jogo": f"{home} x {away}", "Liga": LEAGUES[code], "Situação": "ANALISADO",
                "Detalhe": f"{len(evaluations)-start} seleções avaliadas; carteira validada usa 1X2 e gols, uma seleção por jogo."
            })
        except Exception as exc:
            diagnostics.append({
                "Jogo": f"{clean_text(row.get('Mandante'))} x {clean_text(row.get('Visitante'))}",
                "Liga": clean_text(row.get("Liga")), "Situação": "ERRO", "Detalhe": str(exc),
            })

    all_evaluations = pd.DataFrame(evaluations)
    diagnostics_frame = pd.DataFrame(diagnostics)
    if all_evaluations.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, diagnostics_frame

    # Primeiro, melhor preço qualificado por partida; depois, respeita o máximo semanal.
    qualified = all_evaluations[
        all_evaluations["ValidatedMarket"].eq(True)
        & all_evaluations["StatusBase"].eq("QUALIFICADA")
        & ~all_evaluations["MatchID"].astype(str).isin(registered_matches)
    ].copy()
    best_per_match = (
        qualified.sort_values(["MatchID", "ExpectedValue", "DecisionProbability"], ascending=[True, False, False])
        .drop_duplicates("MatchID")
    )
    weekly_entries: list[pd.DataFrame] = []
    ordered_candidates = best_per_match.sort_values(
        ["WeekID", "ExpectedValue", "DecisionProbability"],
        ascending=[True, False, False],
    )
    for week_id, candidates in ordered_candidates.groupby("WeekID", sort=True):
        remaining = max(0, target - registered_by_week.get(str(week_id), 0))
        if remaining:
            weekly_entries.append(candidates.head(remaining).copy())
    entries = (
        pd.concat(weekly_entries, ignore_index=False)
        if weekly_entries else best_per_match.iloc[0:0].copy()
    )
    if not entries.empty:
        entries["Rank"] = entries.groupby("WeekID")["ExpectedValue"].rank(method="first", ascending=False).astype(int)
        entries["Status"] = "OPERAR"
        entries["Stake"] = unit_value
        entries["Reason"] = "Selecionada pelo maior valor esperado conservador entre preços qualificados; uma seleção por partida."

    selected_keys = set(zip(entries.get("MatchID", []), entries.get("Side", [])))
    for idx, row in all_evaluations.iterrows():
        key = (row["MatchID"], row["Side"])
        if key in selected_keys:
            all_evaluations.at[idx, "Status"] = "OPERAR"
            all_evaluations.at[idx, "Stake"] = unit_value
            all_evaluations.at[idx, "Reason"] = "Selecionada pelo maior valor esperado conservador entre preços qualificados."
        elif row["StatusBase"] == "QUALIFICADA":
            all_evaluations.at[idx, "Status"] = "RESERVA"
            all_evaluations.at[idx, "Stake"] = 0.0
            already_registered = registered_by_week.get(str(row["WeekID"]), 0)
            if str(row["MatchID"]) in registered_matches:
                all_evaluations.at[idx, "Reason"] = (
                    "Preço qualificado, mas esta partida já possui uma aposta registrada."
                )
            elif already_registered >= target:
                all_evaluations.at[idx, "Reason"] = (
                    f"Preço qualificado, mas o máximo semanal de {target} já foi atingido "
                    f"por {already_registered} aposta(s) registrada(s)."
                )
            else:
                all_evaluations.at[idx, "Reason"] = (
                    "Preço qualificado, mas ficou atrás de outra seleção do mesmo jogo ou do máximo semanal."
                )

    # Uma leitura experimental nunca deve ocultar um mercado financeiramente validado.
    order = {"OPERAR": 0, "RESERVA": 1, "QUALIFICADA": 1, "AGUARDAR PREÇO": 2,
             "DESCARTAR": 3, "AMOSTRA INSUFICIENTE": 4, "FORA DA FAIXA": 5, "EXPERIMENTAL": 6}
    all_evaluations["StatusOrder"] = all_evaluations["Status"].map(order).fillna(9)
    readings = (
        all_evaluations.sort_values(["MatchID","StatusOrder","ExpectedValue","DecisionProbability"], ascending=[True,True,False,False])
        .drop_duplicates("MatchID").reset_index(drop=True)
    )
    return entries.reset_index(drop=True), readings, all_evaluations.reset_index(drop=True), diagnostics_frame


def display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    cols = [
        "Rank", "Status", "DateParsed", "Time", "League", "Home", "Away", "MarketName", "Selection",
        "Odd", "EffectiveOdd", "DecisionProbability", "ConservativeProbability", "MarketProbability",
        "RawSportsProbability", "ExpectedValue", "RequiredOddForOperation", "OddGapToOperation",
        "ProfileSample", "EmpiricalHitRate", "SampleConfidence", "Reliability", "Stake", "Reason",
    ]
    out = frame[[column for column in cols if column in frame.columns]].copy()
    rename = {
        "Rank": "Posição", "Status": "Situação", "DateParsed": "Data", "Time": "Hora",
        "League": "Liga", "Home": "Mandante", "Away": "Visitante", "MarketName": "Mercado",
        "Selection": "Seleção", "Odd": "Cotação informada", "EffectiveOdd": "Cotação após desconto de 2%",
        "DecisionProbability": "Probabilidade do modelo", "ConservativeProbability": "Probabilidade conservadora",
        "MarketProbability": "Mercado sem margem", "RawSportsProbability": "Probabilidade esportiva",
        "ExpectedValue": "Valor esperado conservador", "RequiredOddForOperation": "Cotação mínima",
        "OddGapToOperation": "Diferença da cotação", "ProfileSample": "Casos semelhantes",
        "EmpiricalHitRate": "Acerto dos casos semelhantes", "SampleConfidence": "Confiança da amostra",
        "Reliability": "Estabilidade", "Stake": "Entrada fixa", "Reason": "Motivo",
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
        f"RESUMO PARA ANÁLISE — {APP_NAME}",
        "Arquitetura: mercado sem margem, modelo dinâmico de gols e árvores regularizadas, com avaliação fora da amostra.",
        "Protocolo: desconto operacional de 2% na cotação, probabilidade conservadora baseada em casos semelhantes e no máximo uma seleção por jogo.",
        "A quantidade semanal é um limite máximo, nunca uma obrigação de preencher apostas.",
        "Ambas marcam é exibido como análise complementar e não entra automaticamente na carteira validada por ausência de histórico completo de cotações.",
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
                f"{context['HomePPG']:.2f} ponto(s) por jogo | {away} {context['AwayPosition']}º, "
                f"{context['AwayPoints']} pontos, {context['AwayPPG']:.2f} ponto(s) por jogo."
            )
        reading = readings[readings["InputID"].astype(str).eq(input_id)] if not readings.empty else pd.DataFrame()
        if not reading.empty:
            row = reading.iloc[0]
            lines.append(
                f"Leitura principal: {row['Selection']} | {row['Status']} | cotação {row['Odd']:.2f} | "
                f"cotação após desconto {row['EffectiveOdd']:.2f} | probabilidade do modelo "
                f"{row['DecisionProbability']:.1%} | probabilidade conservadora "
                f"{row['ConservativeProbability']:.1%} | mercado {row['MarketProbability']:.1%} | "
                f"probabilidade esportiva {row['RawSportsProbability']:.1%} | valor esperado conservador "
                f"{row['ExpectedValue']:.1%} | cotação mínima {row['RequiredOddForOperation']:.2f}."
            )
            lines.append(
                f"Casos semelhantes: {int(row['ProfileSample'])}; acerto {row['EmpiricalHitRate']:.1%}; "
                f"confiança {row['SampleConfidence']}; estabilidade {row['Reliability']:.1%}."
            )
        game_evaluations = (
            evaluations[evaluations["InputID"].astype(str).eq(input_id)]
            if not evaluations.empty else pd.DataFrame()
        )
        for _, item in game_evaluations.sort_values(["StatusOrder", "ExpectedValue"], ascending=[True, False]).iterrows():
            lines.append(
                f"- {item['Selection']}: {item['Status']}; cotação {item['Odd']:.2f}; "
                f"probabilidade do modelo {item['DecisionProbability']:.1%}; probabilidade conservadora "
                f"{item['ConservativeProbability']:.1%}; valor esperado conservador "
                f"{item['ExpectedValue']:.1%}; cotação mínima {item['RequiredOddForOperation']:.2f}; "
                f"casos semelhantes {int(item['ProfileSample'])}."
            )
        lines.append("")
    if not diagnostics.empty:
        errors = diagnostics[diagnostics["Situação"].eq("ERRO")]
        for _, row in errors.iterrows():
            lines.append(f"ERRO: {row['Jogo']} — {row['Detalhe']}")
    lines.append(
        "Nota: probabilidades não garantem resultado. A evidência histórica depende de cotações competitivas e disciplina de entrada fixa."
    )
    return "\n".join(lines)


__all__ = [
    "APP_NAME", "CORE_API_VERSION", "MODEL_VERSION", "ENGINE_VERSION", "INPUT_COLUMNS", "V28_CFG", "V28Config",
    "analyze_games", "build_ai_summary", "display_frame", "enrich_with_standings",
    "latest_team_catalog", "load_v28_model", "lot_fingerprint", "no_vig_probabilities",
    "parse_odd", "standings_context", "validate_market_odds",
]
