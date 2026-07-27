from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from backtest_v28_meta5 import prepare

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "backtest" / "V28_1_5_6_META_5_SENSIBILIDADE_PISO.csv"
TARGET = 5
PRINCIPAL_FLOOR = 0.0
FALLBACK_STAKE = 0.50
FLOORS = [-0.05, -0.075, -0.10, -0.125, -0.15, -0.20, -1.0]


def simulate(frame: pd.DataFrame, price_column: str, fallback_floor: float) -> dict:
    data = frame.copy()
    data["EffectiveOdd"] = pd.to_numeric(data[price_column], errors="coerce")
    data["EV"] = data["ConservativeProbability"] * data["EffectiveOdd"] - 1.0
    data["FullProfit"] = np.where(data["Win"].eq(1), data["EffectiveOdd"] - 1.0, -1.0)
    candidates = data[
        data["EffectiveOdd"].between(1.20, 3.00)
        & data["Confidence"].isin(["MODERADA", "FORTE"])
    ].copy()
    best_per_match = (
        candidates.sort_values(["MatchID", "EV", "Pred"], ascending=[True, False, False])
        .drop_duplicates("MatchID")
    )
    weekly: list[pd.DataFrame] = []
    for _, group in best_per_match.groupby("WeekID", sort=True):
        ordered = group.sort_values(["EV", "Pred", "Reliability"], ascending=[False, False, False])
        principal = ordered[ordered["EV"].ge(PRINCIPAL_FLOOR)].head(TARGET).copy()
        principal["StakeMultiplier"] = 1.0
        needed = TARGET - len(principal)
        if needed > 0:
            complement = ordered[
                ~ordered["MatchID"].isin(principal["MatchID"])
                & ordered["EV"].ge(fallback_floor)
            ].head(needed).copy()
            complement["StakeMultiplier"] = FALLBACK_STAKE
            principal = pd.concat([principal, complement], ignore_index=False)
        weekly.append(principal)
    selected = pd.concat(weekly, ignore_index=True)
    selected["Profit"] = selected["FullProfit"] * selected["StakeMultiplier"]
    counts = selected.groupby("WeekID").size()
    stake = float(selected["StakeMultiplier"].sum())
    return {
        "cenario_preco": "melhor" if price_column == "ExecBest" else "medio",
        "piso_complemento": fallback_floor,
        "entradas": int(len(selected)),
        "semanas_com_5": int((counts >= TARGET).sum()),
        "media_por_semana": float(len(selected) / frame["WeekID"].nunique()),
        "taxa_acerto": float(selected["Win"].mean()),
        "roi_por_unidade_apostada": float(selected["Profit"].sum() / stake),
        "menor_ev_selecionado": float(selected["EV"].min()),
    }


def main() -> None:
    frame = prepare()
    rows = [
        simulate(frame, price, floor)
        for floor in FLOORS
        for price in ("ExecBest", "ExecAvg")
    ]
    pd.DataFrame(rows).to_csv(OUT, index=False, encoding="utf-8-sig")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
