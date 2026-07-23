from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
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

APP_NAME = "Tex Statistics V28 — Carteira Walk-Forward"
MODEL_VERSION = "V28.0"

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
    target_entries: int = 4
    min_odd: float = 1.20
    max_odd: float = 3.00
    price_haircut: float = 0.02
    minimum_ev: float = 0.0
    near_ev: float = -0.03


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
        self.min_odd = float(self.metadata.get("min_odd", 1.20))
        self.max_odd = float(self.metadata.get("max_odd", 3.00))
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


def _complete_odds(row: pd.Series, columns: list[str]) -> list[float] | None:
    parsed = [parse_odd(row.get(column)) for column in columns]
    if all(value is None for value in parsed):
        return None
    if any(value is None for value in parsed):
        raise ValueError(f"Preencha todas as odds do mercado: {', '.join(columns)}.")
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

        effective_odd = odd * (1.0 - cfg.price_haircut)
        expected_value = probability * effective_odd - 1.0
        required_odd = 1.0 / max((1.0 - cfg.price_haircut) * probability, 1e-9)
        odd_gap = odd - required_odd
        in_odd_range = cfg.min_odd <= effective_odd <= cfg.max_odd

        if not validated:
            status = "EXPERIMENTAL"
            reason = "Ambas marcam é calculado e exibido, mas não entra na carteira: faltam odds históricas completas para backtest financeiro."
        elif in_odd_range and expected_value >= cfg.minimum_ev:
            status = "QUALIFICADA"
            reason = "Preço atual supera a odd mínima do modelo após desconto operacional de 2%."
        elif in_odd_range and expected_value >= cfg.near_ev:
            status = "AGUARDAR PREÇO"
            reason = "Leitura próxima do ponto de equilíbrio; precisa de cotação maior para entrar."
        elif not in_odd_range:
            status = "FORA DA FAIXA"
            reason = f"Odd efetiva fora da faixa testada ({cfg.min_odd:.2f} a {cfg.max_odd:.2f})."
        else:
            status = "DESCARTAR"
            reason = "Preço atual não remunera a probabilidade estimada pelo modelo."

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
            "DecisionProbability": probability,
            "ModelProbability": probability,
            "BreakEvenProbability": 1.0 / effective_odd,
            "ExpectedValue": expected_value,
            "RequiredOddForOperation": required_odd,
            "OddGapToOperation": odd_gap,
            "ModelMarketDifference": raw_probability - market_probability,
            "ProfileSample": int(profile["Sample"]), "ProfileWins": int(profile["Wins"]),
            "EmpiricalHitRate": float(profile["HitRate"]),
            "SportsSample": int(profile["Sample"]),
            "SportsReliability": float(profile["Reliability"]),
            "SportsEmpiricalHitRate": float(profile["HitRate"]),
            "Reliability": float(profile["Reliability"]),
            "CalibrationGap": profile["CalibrationGap"], "Brier": profile["Brier"],
            "SampleConfidence": str(profile["Confidence"]),
            "SampleConfidenceReason": (
                f"{int(profile['Sample'])} previsões fora da amostra; desvio de calibração "
                f"{float(profile['CalibrationGap']):.1%}." if int(profile["Sample"]) > 0 and pd.notna(profile["CalibrationGap"])
                else "Mercado sem perfil financeiro fora da amostra."
            ),
            "ProfileLevel": str(profile["Level"]),
            "SportsProfileLevel": str(profile["Level"]),
            "Confidence": str(profile["Confidence"]),
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
    """Analisa todos os mercados e monta uma carteira ranqueada por semana.

    O volume é um alvo de 3–5 entradas por semana, nunca uma fabricação: somente
    preços com EV não negativo entram. Uma seleção por partida.
    """
    if games.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, empty

    target = int(np.clip(max_entries, 3, 5))
    unit_value = max(0.0, float(bankroll) * float(unit_fraction))
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
                item["InputID"] = clean_text(row.get("ID"))
                item["Time"] = clean_text(row.get("Hora"))
                item["Bookmaker"] = clean_text(row.get("Casa de apostas")) or "Não informada"
            diagnostics.append({
                "Jogo": f"{home} x {away}", "Liga": LEAGUES[code], "Situação": "ANALISADO",
                "Detalhe": f"{len(evaluations)-start} seleções avaliadas; carteira V28 usa 1X2 e gols, uma seleção por jogo."
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

    # Primeiro, melhor preço qualificado por partida; depois, top 3–5 por semana.
    qualified = all_evaluations[
        all_evaluations["ValidatedMarket"].eq(True)
        & all_evaluations["StatusBase"].eq("QUALIFICADA")
    ].copy()
    best_per_match = (
        qualified.sort_values(["MatchID", "ExpectedValue", "DecisionProbability"], ascending=[True, False, False])
        .drop_duplicates("MatchID")
    )
    entries = (
        best_per_match.sort_values(["WeekID", "ExpectedValue", "DecisionProbability"], ascending=[True, False, False])
        .groupby("WeekID", group_keys=False)
        .head(target)
        .copy()
    )
    if not entries.empty:
        entries["Rank"] = entries.groupby("WeekID")["ExpectedValue"].rank(method="first", ascending=False).astype(int)
        entries["Status"] = "OPERAR"
        entries["Stake"] = unit_value
        entries["Reason"] = "Selecionada na carteira semanal pelo maior EV entre preços qualificados; uma seleção por partida."

    selected_keys = set(zip(entries.get("MatchID", []), entries.get("Side", [])))
    selected_matches = set(entries.get("MatchID", []))
    for idx, row in all_evaluations.iterrows():
        key = (row["MatchID"], row["Side"])
        if key in selected_keys:
            all_evaluations.at[idx, "Status"] = "OPERAR"
            all_evaluations.at[idx, "Stake"] = unit_value
            all_evaluations.at[idx, "Reason"] = "Selecionada na carteira semanal pelo maior EV entre preços qualificados."
        elif row["StatusBase"] == "QUALIFICADA":
            all_evaluations.at[idx, "Status"] = "RESERVA"
            all_evaluations.at[idx, "Stake"] = 0.0
            all_evaluations.at[idx, "Reason"] = (
                "Preço qualificado, mas ficou atrás de outra seleção do mesmo jogo ou do limite semanal."
            )

    order = {"OPERAR":0,"RESERVA":1,"QUALIFICADA":1,"AGUARDAR PREÇO":2,"EXPERIMENTAL":3,"DESCARTAR":4,"FORA DA FAIXA":5}
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
        "Rank","Status","DateParsed","Time","League","Home","Away","MarketName","Selection","Odd","EffectiveOdd",
        "DecisionProbability","MarketProbability","RawSportsProbability","ExpectedValue","RequiredOddForOperation",
        "OddGapToOperation","ProfileSample","EmpiricalHitRate","SampleConfidence","Reliability","Stake","Reason"
    ]
    out=frame[[c for c in cols if c in frame.columns]].copy()
    rename={
        "Rank":"Rank","Status":"Status","DateParsed":"Data","Time":"Hora","League":"Liga","Home":"Mandante","Away":"Visitante",
        "MarketName":"Mercado","Selection":"Seleção","Odd":"Odd informada","EffectiveOdd":"Odd efetiva (-2%)",
        "DecisionProbability":"Probabilidade V28","MarketProbability":"Mercado sem margem","RawSportsProbability":"Poisson dinâmico",
        "ExpectedValue":"EV após desconto","RequiredOddForOperation":"Odd mínima","OddGapToOperation":"Folga da odd",
        "ProfileSample":"Amostra OOS","EmpiricalHitRate":"Acerto OOS","SampleConfidence":"Confiança da amostra",
        "Reliability":"Estabilidade","Stake":"Entrada fixa","Reason":"Motivo"
    }
    return out.rename(columns=rename)


def build_ai_summary(
    games: pd.DataFrame,
    readings: pd.DataFrame,
    evaluations: pd.DataFrame,
    diagnostics: pd.DataFrame,
    matches: list[dict[str, Any]],
) -> str:
    lines=[
        f"RESUMO PARA IA — {APP_NAME}",
        "Arquitetura: mercado sem margem + Poisson dinâmico + LightGBM regularizado, treinado sem CalP/Rel/N e testado walk-forward.",
        "Protocolo: odd informada recebe desconto operacional de 2%; carteira usa 1X2 e mais/menos 2,5; uma seleção por jogo; alvo de 3–5 entradas por semana.",
        "Ambas marcam é exibido como experimental e não entra na carteira financeira por ausência de odds históricas completas.",
        f"Partidas: {len(games)} | leituras: {len(readings)} | mercados: {len(evaluations)}",
        "",
    ]
    for _, game in games.iterrows():
        input_id=str(game.get("ID","")); home=str(game.get("Mandante","")); away=str(game.get("Visitante",""))
        code=str(game.get("Código da liga","")); match_date=parse_date(game.get("Data"))
        context=standings_context(matches,code,match_date,home,away)
        lines.append(f"JOGO: {home} x {away} | {game.get('Liga','')} | {match_date.strftime('%d/%m/%Y')} {game.get('Hora','')}")
        if context.get("Available"):
            lines.append(f"Classificação: {home} {context['HomePosition']}º, {context['HomePoints']} pts, {context['HomePPG']:.2f} PPG | {away} {context['AwayPosition']}º, {context['AwayPoints']} pts, {context['AwayPPG']:.2f} PPG.")
        r=readings[readings["InputID"].astype(str).eq(input_id)] if not readings.empty else pd.DataFrame()
        if not r.empty:
            row=r.iloc[0]
            lines.append(
                f"Leitura principal: {row['Selection']} | {row['Status']} | odd {row['Odd']:.2f} | odd efetiva {row['EffectiveOdd']:.2f} | "
                f"P(V28) {row['DecisionProbability']:.1%} | mercado {row['MarketProbability']:.1%} | Poisson {row['RawSportsProbability']:.1%} | "
                f"EV {row['ExpectedValue']:.1%} | odd mínima {row['RequiredOddForOperation']:.2f}."
            )
            lines.append(f"Amostra OOS: {int(row['ProfileSample'])}; acerto {row['EmpiricalHitRate']:.1%}; confiança {row['SampleConfidence']}; estabilidade {row['Reliability']:.1%}.")
        evs=evaluations[evaluations["InputID"].astype(str).eq(input_id)] if not evaluations.empty else pd.DataFrame()
        for _,e in evs.sort_values(["StatusOrder","ExpectedValue"],ascending=[True,False]).iterrows():
            lines.append(f"- {e['Selection']}: {e['Status']}; odd {e['Odd']:.2f}; P(V28) {e['DecisionProbability']:.1%}; EV {e['ExpectedValue']:.1%}; odd mínima {e['RequiredOddForOperation']:.2f}; amostra {int(e['ProfileSample'])}.")
        lines.append("")
    if not diagnostics.empty:
        errors=diagnostics[diagnostics["Situação"].eq("ERRO")]
        for _,row in errors.iterrows(): lines.append(f"ERRO: {row['Jogo']} — {row['Detalhe']}")
    lines.append("Nota: probabilidades não são garantias. A evidência histórica depende de preços competitivos; odds médias com desconto de 2% não foram lucrativas no teste.")
    return "\n".join(lines)


__all__=[
    "APP_NAME","INPUT_COLUMNS","V28_CFG","V28Config","analyze_games","build_ai_summary","display_frame",
    "enrich_with_standings","latest_team_catalog","load_v28_model","no_vig_probabilities","parse_odd","standings_context"
]
