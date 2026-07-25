from __future__ import annotations

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PREDICTIONS = ROOT / "backtest" / "V28_OOS_PREDICTIONS.csv.gz"
PROFILES = ROOT / "model" / "reliability_profiles.csv"
OUT_ENTRIES = ROOT / "backtest" / "V28_1_5_FILTRO_CONSERVADOR_ENTRADAS.csv"
OUT_SUMMARY = ROOT / "backtest" / "V28_1_5_FILTRO_CONSERVADOR_RESUMO.json"
Z = 1.2815515655446004


def wilson_lower(hit_rate: pd.Series, sample: pd.Series) -> np.ndarray:
    n = sample.to_numpy(dtype=float)
    p = hit_rate.to_numpy(dtype=float)
    safe_n = np.maximum(n, 1.0)
    denominator = 1.0 + Z * Z / safe_n
    centre = p + Z * Z / (2.0 * safe_n)
    adjustment = Z * np.sqrt((p * (1.0 - p) + Z * Z / (4.0 * safe_n)) / safe_n)
    result = (centre - adjustment) / denominator
    return np.where(n > 0, np.clip(result, 0.0, 1.0), 0.0)


def max_drawdown(profits: pd.Series) -> float:
    equity = profits.astype(float).cumsum().to_numpy()
    if not len(equity):
        return 0.0
    peaks = np.maximum.accumulate(np.concatenate([[0.0], equity]))[1:]
    return float(np.max(peaks - equity))


def main() -> None:
    predictions = pd.read_csv(PREDICTIONS)
    profiles = pd.read_csv(PROFILES)
    predictions["ProbBin"] = (
        np.floor(np.clip(predictions["Pred"], 0.0, 0.9999) / 0.05) * 0.05
    ).round(2)

    metrics = ["Sample", "Wins", "HitRate", "CalibrationGap"]
    league = profiles[profiles["Level"].eq("LIGA")].copy()
    league = league.rename(columns={name: f"Liga_{name}" for name in metrics})
    global_profile = profiles[profiles["Level"].eq("GLOBAL")].copy()
    global_profile = global_profile.rename(columns={name: f"Global_{name}" for name in metrics})

    frame = predictions.merge(
        league[["Code", "Market", "Side", "ProbBin"] + [f"Liga_{name}" for name in metrics]],
        on=["Code", "Market", "Side", "ProbBin"],
        how="left",
    )
    frame = frame.merge(
        global_profile[["Market", "Side", "ProbBin"] + [f"Global_{name}" for name in metrics]],
        on=["Market", "Side", "ProbBin"],
        how="left",
    )
    use_league = frame["Liga_Sample"].fillna(0).ge(100)
    for name in metrics:
        frame[name] = np.where(use_league, frame[f"Liga_{name}"], frame[f"Global_{name}"])
    frame["Sample"] = frame["Sample"].fillna(0).astype(int)
    frame["Wins"] = frame["Wins"].fillna(0).astype(int)
    frame["HitRate"] = frame["HitRate"].fillna(frame["Pred"])
    frame["CalibrationGap"] = frame["CalibrationGap"].fillna(1.0)
    frame["Reliability"] = np.clip(1.0 - frame["CalibrationGap"] / 0.15, 0.0, 1.0)
    frame["Confidence"] = np.where(
        (frame["Sample"] >= 300) & (frame["CalibrationGap"] <= 0.04),
        "FORTE",
        np.where(
            (frame["Sample"] >= 100) & (frame["CalibrationGap"] <= 0.08),
            "MODERADA",
            "FRACA",
        ),
    )
    frame["SimilarCasesLowerProbability"] = wilson_lower(frame["HitRate"], frame["Sample"])
    frame["ConservativeProbability"] = np.minimum(
        frame["Pred"], frame["SimilarCasesLowerProbability"]
    )
    frame["EffectiveOdd"] = frame["ExecBest"].astype(float)
    frame["ConservativeEV"] = frame["ConservativeProbability"] * frame["EffectiveOdd"] - 1.0
    frame["Profit"] = np.where(frame["Win"].eq(1), frame["EffectiveOdd"] - 1.0, -1.0)

    qualified = frame[
        frame["EffectiveOdd"].between(1.20, 3.00)
        & frame["ConservativeEV"].ge(0.0)
        & frame["Confidence"].isin(["MODERADA", "FORTE"])
    ].copy()
    selected = (
        qualified.sort_values(
            ["MatchID", "ConservativeEV", "Pred"], ascending=[True, False, False]
        )
        .drop_duplicates("MatchID")
        .sort_values(["WeekID", "ConservativeEV", "Pred"], ascending=[True, False, False])
        .groupby("WeekID", group_keys=False)
        .head(5)
        .sort_values(["Date", "League", "Home", "Away"])
        .reset_index(drop=True)
    )

    yearly = (
        selected.groupby("Season", as_index=False)
        .agg(
            entries=("Win", "size"),
            wins=("Win", "sum"),
            hit_rate=("Win", "mean"),
            profit_units=("Profit", "sum"),
            roi=("Profit", "mean"),
        )
        .to_dict("records")
    )
    summary = {
        "metodo": "Recalculo das previsões fora da amostra com filtro operacional conservador e máximo de cinco entradas semanais",
        "advertencia": (
            "Recalculo operacional retrospectivo. Os perfis de confiabilidade agregam previsões "
            "fora da amostra; portanto, isto não é um novo teste final independente."
        ),
        "entries": int(len(selected)),
        "weeks": int(selected["WeekID"].nunique()),
        "average_entries_per_week": float(len(selected) / max(selected["WeekID"].nunique(), 1)),
        "wins": int(selected["Win"].sum()),
        "hit_rate": float(selected["Win"].mean()),
        "profit_units": float(selected["Profit"].sum()),
        "roi": float(selected["Profit"].mean()),
        "max_drawdown_units": max_drawdown(selected["Profit"]),
        "yearly": yearly,
    }
    selected.to_csv(OUT_ENTRIES, index=False, encoding="utf-8-sig")
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
