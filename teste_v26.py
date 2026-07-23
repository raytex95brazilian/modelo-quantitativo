from __future__ import annotations

from pathlib import Path
import pandas as pd

from tex_v25_core import normalize_zip
from tex_v26_operacional import analyze_batch, parse_odd, select_weekly_portfolio

ROOT = Path(__file__).resolve().parent


def test_odd_recovery() -> None:
    assert abs(parse_odd("31.12", "55,55555556") - 1.8) < 0.001
    assert abs(parse_odd("1.1", "46,72897196") - 2.14) < 0.001
    assert abs(parse_odd("1,86", "53,76344086") - 1.86) < 0.001


def test_backtest_reproduction() -> None:
    selected = pd.read_csv(ROOT / "output" / "v25_test_bets.csv")
    selected["Decision"] = "CANDIDATA"
    selected["Reason"] = ""
    selected["Stake"] = 1.0
    selected["HistoricalBets"] = selected["TotalBets"]
    selected["HistoricalPriceEV"] = selected["HistoricalHitRate"] * selected["ExecutableOdd"] - 1
    selected["SportsEV"] = selected["SportsProbability"] * selected["ExecutableOdd"] - 1
    selected["BreakEvenProbability"] = 1 / selected["ExecutableOdd"]
    selected["FairOddSports"] = 1 / selected["SportsProbability"]
    selected["Selection"] = selected["Side"]
    selected["MarketName"] = selected["Market"]
    result = select_weekly_portfolio(selected, 4)
    operating = result[result["Decision"].eq("OPERAR")]
    assert len(operating) == 547
    assert int(operating["Win"].sum()) == 341
    assert abs(float(operating["Profit"].sum()) - 33.8264) < 1e-6


def test_current_11_games() -> None:
    example = pd.read_csv(ROOT / "EXEMPLO_11_JOGOS.csv")
    matches = normalize_zip(ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)
    zones = pd.read_csv(ROOT / "output" / "v25_zone_season_metrics.csv")
    portfolio, diagnostics = analyze_batch(example, matches, zones, 1000.0, 0.01, 4)
    assert len(diagnostics) == 11
    assert not diagnostics["Situação"].eq("ERRO").any()
    operating = portfolio[portfolio["Decision"].eq("OPERAR")]
    assert len(operating) == 1
    assert operating.iloc[0]["Home"] == "Bragantino"
    assert operating.iloc[0]["Side"] == "O25"
    assert abs(float(operating.iloc[0]["Stake"]) - 10.0) < 1e-9


if __name__ == "__main__":
    test_odd_recovery()
    test_backtest_reproduction()
    test_current_11_games()
    print("TESTES V26: OK")
