from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math

import numpy as np
import pandas as pd

OPERATION_API_VERSION = "28.3.10"


@dataclass(frozen=True)
class MultipleSummary:
    selections: pd.DataFrame
    factor: float
    effective_factor: float
    joint_probability: float
    break_even_probability: float
    expected_value: float


def attach_filter_results(evaluations: pd.DataFrame, filter_results: pd.DataFrame) -> pd.DataFrame:
    if evaluations.empty:
        return evaluations.copy()
    out = evaluations.copy()
    if filter_results.empty:
        out["Filter2018Approved"] = False
        out["Filter2018Status"] = "REPROVADO"
        out["Filter2018Summary"] = "Filtro de 2018 indisponível."
        return out
    return out.merge(filter_results, on="InputID", how="left", validate="many_to_one")


def _financially_favorable(row: pd.Series) -> bool:
    value = pd.to_numeric(pd.Series([row.get("ConservativeExpectedValue")]), errors="coerce").iloc[0]
    return bool(pd.notna(value) and float(value) >= 0.0)


def build_operational_outputs(
    evaluations: pd.DataFrame,
    bankroll: float,
    unit_fraction: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, MultipleSummary]:
    """Aplica o portão de 2018 sem apagar cálculos dos jogos reprovados.

    - Todos os mercados permanecem no quadro completo e podem ser salvos.
    - Reprovados jamais entram em simples ou múltipla.
    - Apostas simples usam o melhor valor financeiro não negativo por partida.
    - A múltipla usa, por partida, o mercado de maior probabilidade conservadora
      entre aqueles cujo preço também é financeiramente favorável.
    """
    if evaluations.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, MultipleSummary(empty, 0.0, 0.0, 0.0, 0.0, 0.0)

    out = evaluations.copy()
    out["Filter2018Approved"] = out.get("Filter2018Approved", False).fillna(False).astype(bool)
    filter_status = out.get("Filter2018Status", pd.Series("REPROVADO", index=out.index)).fillna("REPROVADO").astype(str)
    not_evaluable = filter_status.eq("NÃO AVALIÁVEL")
    out["FinanciallyFavorable"] = out.apply(_financially_favorable, axis=1)
    out["OperationalUniverse"] = np.select(
        [out["Filter2018Approved"], not_evaluable],
        ["APTO — FILTRO DE 2018 APROVADO", "FORA — DADOS INSUFICIENTES PARA O FILTRO"],
        default="FORA DO UNIVERSO OPERACIONAL",
    )
    out["OperationalDecision"] = np.select(
        [
            not_evaluable,
            ~out["Filter2018Approved"],
            out["Filter2018Approved"] & out["FinanciallyFavorable"],
        ],
        ["NÃO AVALIÁVEL — DADOS INSUFICIENTES", "REPROVADO NO FILTRO DE 2018", "COTAÇÃO FAVORÁVEL"],
        default="SEM VALOR AO PREÇO ATUAL",
    )
    out["Status"] = out["OperationalDecision"]
    out["Stake"] = 0.0
    out["StakeMultiplier"] = 0.0
    out["PortfolioTier"] = ""

    approved = out[out["Filter2018Approved"]].copy()
    reading_rows: list[pd.Series] = []
    individual_rows: list[pd.Series] = []
    multiple_rows: list[pd.Series] = []

    for _, group in out.groupby("InputID", sort=False):
        approved_group = group[group["Filter2018Approved"]]
        if approved_group.empty:
            chosen = group.sort_values(
                ["ConservativeProbability", "DecisionProbability"], ascending=[False, False]
            ).iloc[0].copy()
            chosen_status = str(chosen.get("Filter2018Status", "REPROVADO"))
            chosen["Status"] = (
                "NÃO AVALIÁVEL — DADOS INSUFICIENTES"
                if chosen_status == "NÃO AVALIÁVEL"
                else "REPROVADO NO FILTRO DE 2018"
            )
            chosen["Reason"] = str(chosen.get("Filter2018Summary", "Evento fora do universo operacional."))
            reading_rows.append(chosen)
            continue

        favorable = approved_group[approved_group["FinanciallyFavorable"]].copy()
        statistical_best = approved_group.sort_values(
            ["ConservativeProbability", "DecisionProbability", "ConservativeExpectedValue"],
            ascending=[False, False, False],
        ).iloc[0].copy()

        if favorable.empty:
            statistical_best["Status"] = "SEM VALOR AO PREÇO ATUAL"
            statistical_best["Reason"] = (
                "Evento aprovado no filtro de 2018 e analisado, porém nenhuma cotação informada "
                "superou a cotação mínima calculada pelo cenário conservador."
            )
            reading_rows.append(statistical_best)
            continue

        financial_best = favorable.sort_values(
            ["ConservativeExpectedValue", "ConservativeProbability", "Reliability"],
            ascending=[False, False, False],
        ).iloc[0].copy()
        financial_best["Status"] = "OPERAR"
        financial_best["StakeMultiplier"] = 1.0
        financial_best["Stake"] = float(bankroll) * float(unit_fraction)
        financial_best["PortfolioTier"] = "APROVADA NO FILTRO 2018 — VALOR FINANCEIRO POSITIVO"
        financial_best["Reason"] = (
            "Evento aprovado no filtro de 2018; este é o mercado com melhor valor esperado conservador "
            "entre as cotações informadas para a partida."
        )
        individual_rows.append(financial_best)
        reading_rows.append(financial_best)

        multiple_best = favorable.sort_values(
            ["ConservativeProbability", "DecisionProbability", "ConservativeExpectedValue"],
            ascending=[False, False, False],
        ).iloc[0].copy()
        multiple_best["IncludedInMultiple"] = True
        multiple_best["MultipleReason"] = (
            "Mercado de maior probabilidade conservadora da partida entre as opções com cotação favorável."
        )
        multiple_rows.append(multiple_best)

    entries = pd.DataFrame(individual_rows)
    readings = pd.DataFrame(reading_rows)
    multiple = pd.DataFrame(multiple_rows)

    if not entries.empty:
        entries = entries.reset_index(drop=True)
        entries["Rank"] = entries.groupby("WeekID")["ConservativeExpectedValue"].rank(
            method="first", ascending=False
        ).astype(int)
        selected = set(zip(entries["InputID"].astype(str), entries["Market"].astype(str), entries["Side"].astype(str)))
        for idx, row in out.iterrows():
            key = (str(row["InputID"]), str(row["Market"]), str(row["Side"]))
            if key in selected:
                match = entries[
                    entries["InputID"].astype(str).eq(key[0])
                    & entries["Market"].astype(str).eq(key[1])
                    & entries["Side"].astype(str).eq(key[2])
                ].iloc[0]
                out.at[idx, "Status"] = "OPERAR"
                out.at[idx, "StakeMultiplier"] = 1.0
                out.at[idx, "Stake"] = float(bankroll) * float(unit_fraction)
                out.at[idx, "PortfolioTier"] = str(match["PortfolioTier"])
                out.at[idx, "Reason"] = str(match["Reason"])

    out["IncludedInMultiple"] = False
    if not multiple.empty:
        multiple = multiple.reset_index(drop=True)
        keys = set(zip(multiple["InputID"].astype(str), multiple["Market"].astype(str), multiple["Side"].astype(str)))
        for idx, row in out.iterrows():
            if (str(row["InputID"]), str(row["Market"]), str(row["Side"])) in keys:
                out.at[idx, "IncludedInMultiple"] = True

    if len(multiple) >= 2:
        factor = float(np.prod(pd.to_numeric(multiple["Odd"], errors="coerce")))
        effective_factor = float(np.prod(pd.to_numeric(multiple["EffectiveOdd"], errors="coerce")))
        joint_probability = float(np.prod(pd.to_numeric(multiple["ConservativeProbability"], errors="coerce")))
        break_even = 1.0 / factor if factor > 0 else 0.0
        expected_value = joint_probability * effective_factor - 1.0
    else:
        factor = effective_factor = joint_probability = break_even = expected_value = 0.0

    summary = MultipleSummary(
        selections=multiple,
        factor=factor,
        effective_factor=effective_factor,
        joint_probability=joint_probability,
        break_even_probability=break_even,
        expected_value=expected_value,
    )
    return entries, readings, out.reset_index(drop=True), summary


__all__ = [
    "OPERATION_API_VERSION", "MultipleSummary", "attach_filter_results",
    "build_operational_outputs",
]
