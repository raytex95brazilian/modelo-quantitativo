from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PREDICTIONS = ROOT / "backtest" / "V28_OOS_PREDICTIONS.csv.gz"
PROFILES = ROOT / "model" / "reliability_profiles.csv"
OUT_ENTRIES = ROOT / "backtest" / "V28_1_5_6_META_5_ENTRADAS_MELHOR_PRECO.csv"
OUT_SUMMARY = ROOT / "backtest" / "V28_1_5_6_META_5_RESUMO.json"
Z = 1.2815515655446004
TARGET = 5
PORTFOLIO_FLOOR = 0.0
FALLBACK_FLOOR = -0.15
FALLBACK_STAKE = 0.50


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


def prepare() -> pd.DataFrame:
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
        on=["Code", "Market", "Side", "ProbBin"], how="left",
    )
    frame = frame.merge(
        global_profile[["Market", "Side", "ProbBin"] + [f"Global_{name}" for name in metrics]],
        on=["Market", "Side", "ProbBin"], how="left",
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
        (frame["Sample"] >= 300) & (frame["CalibrationGap"] <= 0.04), "FORTE",
        np.where(
            (frame["Sample"] >= 100) & (frame["CalibrationGap"] <= 0.08),
            "MODERADA", "FRACA",
        ),
    )
    frame["Lower"] = wilson_lower(frame["HitRate"], frame["Sample"])
    frame["ConservativeProbability"] = np.minimum(frame["Pred"], frame["Lower"])
    return frame


def simulate(frame: pd.DataFrame, price_column: str) -> tuple[pd.DataFrame, dict]:
    data = frame.copy()
    data["EffectiveOdd"] = pd.to_numeric(data[price_column], errors="coerce")
    data["ConservativeEV"] = data["ConservativeProbability"] * data["EffectiveOdd"] - 1.0
    data["FullUnitProfit"] = np.where(data["Win"].eq(1), data["EffectiveOdd"] - 1.0, -1.0)
    candidates = data[
        data["EffectiveOdd"].between(1.20, 3.00)
        & data["Confidence"].isin(["MODERADA", "FORTE"])
    ].copy()
    best_per_match = (
        candidates.sort_values(
            ["MatchID", "ConservativeEV", "Pred"], ascending=[True, False, False]
        ).drop_duplicates("MatchID")
    )

    weekly: list[pd.DataFrame] = []
    for _, group in best_per_match.groupby("WeekID", sort=True):
        ordered = group.sort_values(
            ["ConservativeEV", "Pred", "Reliability"], ascending=[False, False, False]
        )
        principal = ordered[ordered["ConservativeEV"].ge(PORTFOLIO_FLOOR)].head(TARGET).copy()
        principal["PortfolioTier"] = "EV CONSERVADOR NÃO NEGATIVO"
        principal["StakeMultiplier"] = 1.0
        need = TARGET - len(principal)
        selected = principal
        if need > 0:
            complement = ordered[
                ~ordered["MatchID"].isin(principal["MatchID"])
                & ordered["ConservativeEV"].ge(FALLBACK_FLOOR)
            ].head(need).copy()
            complement["PortfolioTier"] = "COMPLEMENTO DE META — MEIA UNIDADE"
            complement["StakeMultiplier"] = FALLBACK_STAKE
            selected = pd.concat([principal, complement], ignore_index=False)
        weekly.append(selected)

    selected = pd.concat(weekly, ignore_index=True)
    selected["Profit"] = selected["FullUnitProfit"] * selected["StakeMultiplier"]
    counts = selected.groupby("WeekID").size()
    stake_units = float(selected["StakeMultiplier"].sum())
    yearly = (
        selected.groupby("Season", as_index=False)
        .agg(
            entries=("Win", "size"), wins=("Win", "sum"), hit_rate=("Win", "mean"),
            profit_units=("Profit", "sum"), stake_units=("StakeMultiplier", "sum"),
        )
    )
    yearly["roi_per_staked_unit"] = yearly["profit_units"] / yearly["stake_units"]
    result = {
        "entries": int(len(selected)),
        "weeks": int(frame["WeekID"].nunique()),
        "weeks_with_target": int((counts >= TARGET).sum()),
        "average_entries_per_week": float(len(selected) / max(frame["WeekID"].nunique(), 1)),
        "principal_entries": int(selected["PortfolioTier"].eq("EV CONSERVADOR NÃO NEGATIVO").sum()),
        "complement_entries": int(selected["PortfolioTier"].eq("COMPLEMENTO DE META — MEIA UNIDADE").sum()),
        "wins": int(selected["Win"].sum()),
        "hit_rate": float(selected["Win"].mean()),
        "profit_units": float(selected["Profit"].sum()),
        "stake_units": stake_units,
        "roi_per_staked_unit": float(selected["Profit"].sum() / stake_units),
        "max_drawdown_units": max_drawdown(selected.sort_values(["Date", "MatchID"])["Profit"]),
        "yearly": yearly.to_dict("records"),
    }
    return selected, result


def main() -> None:
    frame = prepare()
    best_entries, best = simulate(frame, "ExecBest")
    _, average = simulate(frame, "ExecAvg")
    summary = {
        "metodo": (
            "Ranking semanal das previsões fora da amostra: meta de cinco seleções, uma por partida, "
            "faixa principal com EV conservador >= 0% e complemento até -15% com meia unidade quando necessário."
        ),
        "advertencia": (
            "Recalculo operacional retrospectivo sobre previsões OOS congeladas. O resultado depende do preço; "
            "a verificação por preço médio é materialmente mais fraca que por melhor preço."
        ),
        "target_per_week": TARGET,
        "portfolio_floor": PORTFOLIO_FLOOR,
        "fallback_floor": FALLBACK_FLOOR,
        "fallback_stake_fraction": FALLBACK_STAKE,
        "entries": best["entries"],
        "weeks": best["weeks"],
        "weeks_with_target": best["weeks_with_target"],
        "average_entries_per_week": best["average_entries_per_week"],
        "hit_rate": best["hit_rate"],
        "best_price_roi_per_staked_unit": best["roi_per_staked_unit"],
        "best_price_profit_units": best["profit_units"],
        "best_price_max_drawdown_units": best["max_drawdown_units"],
        "average_price_roi_per_staked_unit": average["roi_per_staked_unit"],
        "average_price_profit_units": average["profit_units"],
        "average_price_max_drawdown_units": average["max_drawdown_units"],
        "principal_entries_best_price": best["principal_entries"],
        "complement_entries_best_price": best["complement_entries"],
        "best_price_yearly": best["yearly"],
        "average_price_yearly": average["yearly"],
    }
    best_entries.to_csv(OUT_ENTRIES, index=False, encoding="utf-8-sig")
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
