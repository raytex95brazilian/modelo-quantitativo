from __future__ import annotations

import csv
import io
import math
import statistics
import zipfile
from functools import lru_cache
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd

VERSION = "Tex Statistics v.25"

LEAGUES = {
    "BRA": "Brasileirão Série A",
    "ARG": "Argentina - Primera Division",
    "USA": "EUA - MLS",
    "MEX": "México - Liga MX",
    "JPN": "Japão - J1 League",
    "CHN": "China - Super League",
    "SWE": "Suécia - Allsvenskan",
    "NOR": "Noruega - Eliteserien",
    "FIN": "Finlândia - Veikkausliiga",
    "IRL": "Irlanda - Premier Division",
    "E0": "Inglaterra - Premier League",
    "E1": "Inglaterra - Championship",
    "SP1": "Espanha - La Liga",
    "SP2": "Espanha - Segunda Divisão",
    "I1": "Itália - Série A",
    "I2": "Itália - Série B",
    "D1": "Alemanha - Bundesliga",
    "D2": "Alemanha - 2. Bundesliga",
    "F1": "França - Ligue 1",
    "P1": "Portugal - Primeira Liga",
    "N1": "Holanda - Eredivisie",
    "B1": "Bélgica - Pro League",
    "T1": "Turquia - Super Lig",
    "G1": "Grécia - Super League",
}
ANNUAL_CODES = {"BRA", "ARG", "USA", "MEX", "JPN", "CHN", "SWE", "NOR", "FIN", "IRL"}


@dataclass(frozen=True)
class V25Config:
    # Modelo esportivo básico
    team_decay: float = 0.90
    league_decay: float = 0.995
    overall_games: int = 20
    venue_games: int = 12
    venue_weight: float = 0.60
    pseudo_games: float = 6.0
    dixon_coles_rho: float = -0.08
    min_team_games: int = 5
    min_league_games: int = 30

    # Zonas simples e estáveis
    market_probability_band: float = 0.025
    model_market_difference_band: float = 0.02
    lookback_seasons: int = 4
    min_zone_total_bets: int = 120
    min_zone_bets_per_season: int = 15
    min_positive_seasons: int = 3
    min_zone_roi: float = 0.02
    min_recent_season_roi: float = -0.02
    min_zone_hit_rate: float = 0.60

    # Execução e volume
    execution_haircut: float = 0.02
    max_executable_odd: float = 3.00
    weekly_top_n: int = 4
    bootstrap_samples: int = 20_000
    random_seed: int = 42


CFG = V25Config()


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin1", errors="replace")


def _number(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def _first_number(row: dict[str, Any], names: Iterable[str]) -> Optional[float]:
    for name in names:
        result = _number(row.get(name))
        if result is not None:
            return result
    return None


def _parse_date(value: Any) -> Optional[date]:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _season_start(label: Any, fallback_code: str = "") -> Optional[int]:
    text = str(label or "").strip()
    if text:
        parts = "".join(ch if ch.isdigit() else " " for ch in text).split()
        if parts:
            year = int(parts[0])
            return year + 2000 if year < 100 else year
    if len(fallback_code) == 4 and fallback_code.isdigit():
        return 2000 + int(fallback_code[:2])
    return None


def no_vig_probabilities(odds: Iterable[float]) -> list[float]:
    odds_list = [float(x) for x in odds]
    if any(x <= 1.0 or not math.isfinite(x) for x in odds_list):
        raise ValueError("Todas as odds precisam ser decimais e maiores que 1,00.")
    inverses = [1.0 / x for x in odds_list]
    total = sum(inverses)
    return [x / total for x in inverses]


def normalize_zip(zip_path: str | Path, include_incomplete_annual_2026: bool = False) -> list[dict[str, Any]]:
    zip_path = Path(zip_path)
    matches: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path) as archive:
        for raw_name in sorted(archive.namelist()):
            name = raw_name.replace("\\", "/")
            if not name.lower().endswith(".csv") or "manifesto" in name.lower():
                continue
            code = name.split("/")[0].upper()
            if code not in LEAGUES:
                continue
            reader = csv.DictReader(io.StringIO(_decode(archive.read(raw_name))))
            file_code = Path(name).stem.split("_")[-1]
            for row in reader:
                if code in ANNUAL_CODES:
                    match_date = _parse_date(row.get("Date"))
                    home = str(row.get("Home") or "").strip()
                    away = str(row.get("Away") or "").strip()
                    home_goals = _number(row.get("HG"))
                    away_goals = _number(row.get("AG"))
                    season = _season_start(row.get("Season"))
                    avg_h = _first_number(row, ["AvgCH"])
                    avg_d = _first_number(row, ["AvgCD"])
                    avg_a = _first_number(row, ["AvgCA"])
                    max_h = _first_number(row, ["MaxCH"])
                    max_d = _first_number(row, ["MaxCD"])
                    max_a = _first_number(row, ["MaxCA"])
                    avg_o = avg_u = max_o = max_u = None
                else:
                    match_date = _parse_date(row.get("Date"))
                    home = str(row.get("HomeTeam") or "").strip()
                    away = str(row.get("AwayTeam") or "").strip()
                    home_goals = _number(row.get("FTHG"))
                    away_goals = _number(row.get("FTAG"))
                    season = _season_start(None, file_code)
                    avg_h = _first_number(row, ["AvgCH", "AvgH", "BbAvH"])
                    avg_d = _first_number(row, ["AvgCD", "AvgD", "BbAvD"])
                    avg_a = _first_number(row, ["AvgCA", "AvgA", "BbAvA"])
                    max_h = _first_number(row, ["MaxCH", "MaxH", "BbMxH"])
                    max_d = _first_number(row, ["MaxCD", "MaxD", "BbMxD"])
                    max_a = _first_number(row, ["MaxCA", "MaxA", "BbMxA"])
                    avg_o = _first_number(row, ["AvgC>2.5", "Avg>2.5", "BbAv>2.5"])
                    avg_u = _first_number(row, ["AvgC<2.5", "Avg<2.5", "BbAv<2.5"])
                    max_o = _first_number(row, ["MaxC>2.5", "Max>2.5", "BbMx>2.5"])
                    max_u = _first_number(row, ["MaxC<2.5", "Max<2.5", "BbMx<2.5"])

                if not (match_date and home and away and home_goals is not None and away_goals is not None and season is not None):
                    continue
                if code in ANNUAL_CODES and season >= 2026 and not include_incomplete_annual_2026:
                    continue
                matches.append(
                    {
                        "Code": code,
                        "League": LEAGUES[code],
                        "Season": int(season),
                        "DateParsed": match_date,
                        "Date": match_date.strftime("%d/%m/%Y"),
                        "Home": home,
                        "Away": away,
                        "HG": int(home_goals),
                        "AG": int(away_goals),
                        "AvgH": avg_h,
                        "AvgD": avg_d,
                        "AvgA": avg_a,
                        "MaxH": max_h,
                        "MaxD": max_d,
                        "MaxA": max_a,
                        "AvgO25": avg_o,
                        "AvgU25": avg_u,
                        "MaxO25": max_o,
                        "MaxU25": max_u,
                    }
                )
    matches.sort(key=lambda row: (row["DateParsed"], row["League"], row["Home"], row["Away"]))
    return matches


def _weighted_average(values: list[float], decay: float) -> Optional[float]:
    if not values:
        return None
    count = len(values)
    weights = np.array([decay ** (count - 1 - index) for index in range(count)], dtype=float)
    array = np.asarray(values, dtype=float)
    return float(np.dot(array, weights) / weights.sum())


@lru_cache(maxsize=50_000)
def _poisson_probabilities_cached(lambda_home: float, lambda_away: float, rho: float, max_goals: int = 10) -> tuple[float, float, float, float, float, float, float]:
    home = np.array([math.exp(-lambda_home) * lambda_home**i / math.factorial(i) for i in range(max_goals + 1)])
    away = np.array([math.exp(-lambda_away) * lambda_away**j / math.factorial(j) for j in range(max_goals + 1)])
    matrix = np.outer(home, away)
    matrix /= matrix.sum()

    # Ajuste de Dixon-Coles apenas para os placares baixos.
    matrix[0, 0] *= max(0.0, 1.0 - lambda_home * lambda_away * rho)
    matrix[0, 1] *= max(0.0, 1.0 + lambda_home * rho)
    matrix[1, 0] *= max(0.0, 1.0 + lambda_away * rho)
    matrix[1, 1] *= max(0.0, 1.0 - rho)
    matrix /= matrix.sum()

    total_goals = np.add.outer(np.arange(max_goals + 1), np.arange(max_goals + 1))
    p_h = float(np.tril(matrix, -1).sum())
    p_d = float(np.trace(matrix))
    p_a = float(np.triu(matrix, 1).sum())
    p_o = float(matrix[total_goals >= 3].sum())
    p_u = float(matrix[total_goals <= 2].sum())
    p_b = float(matrix[1:, 1:].sum())
    return p_h, p_d, p_a, p_o, p_u, p_b, 1.0 - p_b


def _poisson_probabilities(lambda_home: float, lambda_away: float, rho: float, max_goals: int = 10) -> dict[str, float]:
    # Arredondamento de 0,01 gol torna o motor muito mais rápido e não altera a regra operacional.
    values = _poisson_probabilities_cached(round(lambda_home, 2), round(lambda_away, 2), round(rho, 3), max_goals)
    return dict(zip(("H", "D", "A", "O25", "U25", "BTTS_Y", "BTTS_N"), values))


def build_pre_match_probabilities(matches: list[dict[str, Any]], cfg: V25Config = CFG) -> list[dict[str, Any]]:
    league_history: dict[str, deque[tuple[int, int]]] = defaultdict(lambda: deque(maxlen=1000))
    team_overall: dict[tuple[str, str], deque[tuple[int, int]]] = defaultdict(lambda: deque(maxlen=cfg.overall_games))
    team_home: dict[tuple[str, str], deque[tuple[int, int]]] = defaultdict(lambda: deque(maxlen=cfg.venue_games))
    team_away: dict[tuple[str, str], deque[tuple[int, int]]] = defaultdict(lambda: deque(maxlen=cfg.venue_games))
    output: list[dict[str, Any]] = []

    for match in matches:
        code = match["Code"]
        home = match["Home"]
        away = match["Away"]
        league_values = league_history[code]

        enough_history = (
            len(league_values) >= cfg.min_league_games
            and len(team_overall[(code, home)]) >= cfg.min_team_games
            and len(team_overall[(code, away)]) >= cfg.min_team_games
        )

        if enough_history:
            league_home_goals = _weighted_average([x[0] for x in league_values], cfg.league_decay) or 1.35
            league_away_goals = _weighted_average([x[1] for x in league_values], cfg.league_decay) or 1.10

            def team_rates(team: str, venue: str) -> tuple[float, float, float]:
                overall = list(team_overall[(code, team)])
                venue_values = list(team_home[(code, team)] if venue == "H" else team_away[(code, team)])
                overall_for = _weighted_average([x[0] for x in overall], cfg.team_decay) or 0.0
                overall_against = _weighted_average([x[1] for x in overall], cfg.team_decay) or 0.0
                if venue_values:
                    venue_for = _weighted_average([x[0] for x in venue_values], cfg.team_decay) or overall_for
                    venue_against = _weighted_average([x[1] for x in venue_values], cfg.team_decay) or overall_against
                else:
                    venue_for, venue_against = overall_for, overall_against
                goals_for = cfg.venue_weight * venue_for + (1.0 - cfg.venue_weight) * overall_for
                goals_against = cfg.venue_weight * venue_against + (1.0 - cfg.venue_weight) * overall_against
                effective_n = cfg.venue_weight * min(len(venue_values), cfg.venue_games) + (1.0 - cfg.venue_weight) * min(len(overall), cfg.overall_games)
                return goals_for, goals_against, effective_n

            home_for, home_against, home_n = team_rates(home, "H")
            away_for, away_against, away_n = team_rates(away, "A")

            def shrink_ratio(value: float, base: float, sample_size: float) -> float:
                numerator = value * sample_size + base * cfg.pseudo_games
                denominator = base * (sample_size + cfg.pseudo_games)
                return numerator / max(denominator, 1e-9)

            home_attack = shrink_ratio(home_for, league_home_goals, home_n)
            home_defence = shrink_ratio(home_against, league_away_goals, home_n)
            away_attack = shrink_ratio(away_for, league_away_goals, away_n)
            away_defence = shrink_ratio(away_against, league_home_goals, away_n)

            lambda_home = min(4.0, max(0.15, league_home_goals * home_attack * away_defence))
            lambda_away = min(3.5, max(0.10, league_away_goals * away_attack * home_defence))
            probabilities = _poisson_probabilities(lambda_home, lambda_away, cfg.dixon_coles_rho)
            output.append(
                {
                    **match,
                    "LambdaHome": lambda_home,
                    "LambdaAway": lambda_away,
                    "SportsH": probabilities["H"],
                    "SportsD": probabilities["D"],
                    "SportsA": probabilities["A"],
                    "SportsO25": probabilities["O25"],
                    "SportsU25": probabilities["U25"],
                    "SportsBTTSY": probabilities["BTTS_Y"],
                    "SportsBTTSN": probabilities["BTTS_N"],
                }
            )

        # Atualização ocorre somente depois da previsão: sem vazamento temporal.
        home_goals = match["HG"]
        away_goals = match["AG"]
        league_history[code].append((home_goals, away_goals))
        team_overall[(code, home)].append((home_goals, away_goals))
        team_overall[(code, away)].append((away_goals, home_goals))
        team_home[(code, home)].append((home_goals, away_goals))
        team_away[(code, away)].append((away_goals, home_goals))

    return output


def _valid_odds(values: Iterable[Optional[float]]) -> bool:
    return all(value is not None and value > 1.0 and math.isfinite(value) for value in values)


def build_market_rows(predictions: list[dict[str, Any]], cfg: V25Config = CFG) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for match in predictions:
        common = {
            key: match[key]
            for key in ("Code", "League", "Season", "Date", "DateParsed", "Home", "Away", "HG", "AG", "LambdaHome", "LambdaAway")
        }
        if _valid_odds([match["AvgH"], match["AvgD"], match["AvgA"], match["MaxH"], match["MaxD"], match["MaxA"]]):
            market_probabilities = no_vig_probabilities([match["AvgH"], match["AvgD"], match["AvgA"]])
            sports_probabilities = [match["SportsH"], match["SportsD"], match["SportsA"]]
            averages = [match["AvgH"], match["AvgD"], match["AvgA"]]
            maximums = [match["MaxH"], match["MaxD"], match["MaxA"]]
            wins = [match["HG"] > match["AG"], match["HG"] == match["AG"], match["HG"] < match["AG"]]
            for index, side in enumerate(("H", "D", "A")):
                executable = maximums[index] * (1.0 - cfg.execution_haircut)
                rows.append(
                    {
                        **common,
                        "Market": "1X2",
                        "Side": side,
                        "MarketProbability": market_probabilities[index],
                        "SportsProbability": sports_probabilities[index],
                        "ProbabilityDifference": sports_probabilities[index] - market_probabilities[index],
                        "AverageOdd": averages[index],
                        "BestOdd": maximums[index],
                        "ExecutableOdd": executable,
                        "Win": int(wins[index]),
                        "Profit": executable - 1.0 if wins[index] else -1.0,
                    }
                )

        if _valid_odds([match["AvgO25"], match["AvgU25"], match["MaxO25"], match["MaxU25"]]):
            market_probabilities = no_vig_probabilities([match["AvgO25"], match["AvgU25"]])
            sports_probabilities = [match["SportsO25"], match["SportsU25"]]
            averages = [match["AvgO25"], match["AvgU25"]]
            maximums = [match["MaxO25"], match["MaxU25"]]
            wins = [match["HG"] + match["AG"] >= 3, match["HG"] + match["AG"] <= 2]
            for index, side in enumerate(("O25", "U25")):
                executable = maximums[index] * (1.0 - cfg.execution_haircut)
                rows.append(
                    {
                        **common,
                        "Market": "OU",
                        "Side": side,
                        "MarketProbability": market_probabilities[index],
                        "SportsProbability": sports_probabilities[index],
                        "ProbabilityDifference": sports_probabilities[index] - market_probabilities[index],
                        "AverageOdd": averages[index],
                        "BestOdd": maximums[index],
                        "ExecutableOdd": executable,
                        "Win": int(wins[index]),
                        "Profit": executable - 1.0 if wins[index] else -1.0,
                    }
                )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["MarketBand"] = (np.floor(frame["MarketProbability"] / cfg.market_probability_band) * cfg.market_probability_band).round(3)
    shifted = frame["ProbabilityDifference"] + 0.20
    frame["DifferenceBand"] = (np.floor(shifted / cfg.model_market_difference_band) * cfg.model_market_difference_band - 0.20).round(3)
    frame["MatchID"] = (
        frame["League"].astype(str)
        + "|"
        + frame["DateParsed"].astype(str)
        + "|"
        + frame["Home"].astype(str)
        + "|"
        + frame["Away"].astype(str)
    )
    iso = pd.to_datetime(frame["DateParsed"]).dt.isocalendar()
    frame["WeekID"] = iso["year"].astype(str) + "-" + iso["week"].astype(str).str.zfill(2)
    return frame


ZONE_KEYS = ["Market", "Side", "MarketBand", "DifferenceBand"]


def build_zone_season_metrics(market_rows: pd.DataFrame) -> pd.DataFrame:
    metrics = (
        market_rows.groupby(ZONE_KEYS + ["Season"], as_index=False)
        .agg(
            Bets=("Profit", "size"),
            Wins=("Win", "sum"),
            ProfitUnits=("Profit", "sum"),
            HitRate=("Win", "mean"),
            AverageOdd=("ExecutableOdd", "mean"),
        )
    )
    metrics["ROI"] = metrics["ProfitUnits"] / metrics["Bets"]
    return metrics


def approved_zones_for_season(zone_metrics: pd.DataFrame, season: int, cfg: V25Config = CFG) -> pd.DataFrame:
    history = zone_metrics[
        (zone_metrics["Season"] >= season - cfg.lookback_seasons)
        & (zone_metrics["Season"] < season)
        & (zone_metrics["Bets"] >= cfg.min_zone_bets_per_season)
    ].copy()
    if history.empty:
        return pd.DataFrame(columns=ZONE_KEYS)

    aggregate = (
        history.groupby(ZONE_KEYS, as_index=False)
        .agg(
            TotalBets=("Bets", "sum"),
            TotalWins=("Wins", "sum"),
            TotalProfit=("ProfitUnits", "sum"),
            PositiveSeasons=("ROI", lambda values: int((values > 0).sum())),
            SeasonsObserved=("Season", "nunique"),
        )
    )
    aggregate["HistoricalHitRate"] = aggregate["TotalWins"] / aggregate["TotalBets"]
    aggregate["HistoricalROI"] = aggregate["TotalProfit"] / aggregate["TotalBets"]

    recent = history[history["Season"] == season - 1][ZONE_KEYS + ["ROI", "Bets"]].rename(
        columns={"ROI": "RecentSeasonROI", "Bets": "RecentSeasonBets"}
    )
    aggregate = aggregate.merge(recent, on=ZONE_KEYS, how="left")
    approved = aggregate[
        (aggregate["TotalBets"] >= cfg.min_zone_total_bets)
        & (aggregate["SeasonsObserved"] >= cfg.min_positive_seasons)
        & (aggregate["PositiveSeasons"] >= cfg.min_positive_seasons)
        & (aggregate["HistoricalROI"] >= cfg.min_zone_roi)
        & (aggregate["RecentSeasonROI"].fillna(-99.0) >= cfg.min_recent_season_roi)
        & (aggregate["HistoricalHitRate"] >= cfg.min_zone_hit_rate)
    ].copy()
    approved["ApprovalSeason"] = season
    return approved.sort_values(["HistoricalHitRate", "HistoricalROI"], ascending=False)


def generate_approved_candidates(
    market_rows: pd.DataFrame,
    zone_metrics: pd.DataFrame,
    evaluation_seasons: Iterable[int],
    cfg: V25Config = CFG,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidates: list[pd.DataFrame] = []
    approvals: list[pd.DataFrame] = []
    for season in sorted(set(int(x) for x in evaluation_seasons)):
        approved = approved_zones_for_season(zone_metrics, season, cfg)
        if approved.empty:
            continue
        approvals.append(approved)
        current = market_rows[
            (market_rows["Season"] == season)
            & (market_rows["ExecutableOdd"] >= 1.01)
            & (market_rows["ExecutableOdd"] <= cfg.max_executable_odd)
        ].merge(
            approved[
                ZONE_KEYS
                + [
                    "TotalBets",
                    "PositiveSeasons",
                    "HistoricalHitRate",
                    "HistoricalROI",
                    "RecentSeasonROI",
                ]
            ],
            on=ZONE_KEYS,
            how="inner",
        )
        if not current.empty:
            candidates.append(current)
    candidate_frame = pd.concat(candidates, ignore_index=True) if candidates else pd.DataFrame()
    approval_frame = pd.concat(approvals, ignore_index=True) if approvals else pd.DataFrame()
    return candidate_frame, approval_frame


def select_weekly_top(candidates: pd.DataFrame, cfg: V25Config = CFG) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()
    # Uma seleção por partida e até quatro por semana civil, priorizando a maior
    # probabilidade sem margem. É a regra de simplicidade/alta assertividade.
    unique_matches = (
        candidates.sort_values(
            ["MatchID", "MarketProbability", "HistoricalHitRate", "HistoricalROI"],
            ascending=[True, False, False, False],
        )
        .drop_duplicates("MatchID")
    )
    selected = (
        unique_matches.sort_values(
            ["WeekID", "MarketProbability", "HistoricalHitRate", "HistoricalROI"],
            ascending=[True, False, False, False],
        )
        .groupby("WeekID", as_index=False)
        .head(cfg.weekly_top_n)
        .sort_values(["DateParsed", "League", "Home", "Away"])
        .reset_index(drop=True)
    )
    selected["RankInWeek"] = selected.groupby("WeekID")["MarketProbability"].rank(method="first", ascending=False).astype(int)
    return selected


def max_drawdown(profits: Iterable[float]) -> float:
    equity = peak = drawdown = 0.0
    for value in profits:
        equity += float(value)
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def longest_losing_streak(wins: Iterable[int]) -> int:
    current = longest = 0
    for win in wins:
        if int(win):
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    return longest


def performance_metrics(selected: pd.DataFrame, cfg: V25Config = CFG) -> dict[str, Any]:
    if selected.empty:
        return {"bets": 0, "wins": 0, "hit_rate": None, "profit_units": 0.0, "roi": None}
    ordered = selected.sort_values(["DateParsed", "League", "Home", "Away"])
    profits = ordered["Profit"].astype(float).to_numpy()
    weeks = ordered.groupby("WeekID", as_index=False).agg(Profit=("Profit", "sum"), Bets=("Profit", "size"))
    rng = np.random.default_rng(cfg.random_seed)
    week_profit = weeks["Profit"].to_numpy(dtype=float)
    week_bets = weeks["Bets"].to_numpy(dtype=float)
    indices = rng.integers(0, len(weeks), size=(cfg.bootstrap_samples, len(weeks)))
    bootstrap = week_profit[indices].sum(axis=1) / week_bets[indices].sum(axis=1)
    week_sizes = ordered.groupby("WeekID").size()
    return {
        "bets": int(len(ordered)),
        "wins": int(ordered["Win"].sum()),
        "hit_rate": float(ordered["Win"].mean()),
        "profit_units": float(profits.sum()),
        "roi": float(profits.mean()),
        "average_executable_odd": float(ordered["ExecutableOdd"].mean()),
        "max_drawdown_units": float(max_drawdown(profits)),
        "longest_losing_streak": int(longest_losing_streak(ordered["Win"])),
        "active_weeks": int(len(week_sizes)),
        "average_bets_per_active_week": float(len(ordered) / len(week_sizes)),
        "weeks_with_at_least_3": int((week_sizes >= 3).sum()),
        "weeks_with_4": int((week_sizes >= 4).sum()),
        "roi_ci_lower": float(np.quantile(bootstrap, 0.025)),
        "roi_ci_upper": float(np.quantile(bootstrap, 0.975)),
        "bootstrap_probability_positive": float((bootstrap > 0).mean()),
    }


def grouped_metrics(selected: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    if selected.empty:
        return pd.DataFrame()
    result = (
        selected.groupby(by, as_index=False)
        .agg(
            Bets=("Win", "size"),
            Wins=("Win", "sum"),
            ProfitUnits=("Profit", "sum"),
            HitRate=("Win", "mean"),
            AverageOdd=("ExecutableOdd", "mean"),
        )
    )
    result["ROI"] = result["ProfitUnits"] / result["Bets"]
    return result


def price_stress(selected: pd.DataFrame) -> pd.DataFrame:
    if selected.empty:
        return pd.DataFrame()
    scenarios = [
        ("Melhor odd -1%", 1.00, 0.01),
        ("Melhor odd -2% (oficial)", 1.00, 0.02),
        ("Melhor odd -3%", 1.00, 0.03),
        ("Melhor odd -5%", 1.00, 0.05),
        ("75% do ganho entre média e melhor -2%", 0.75, 0.02),
        ("50% do ganho entre média e melhor -2%", 0.50, 0.02),
        ("Odd média -2%", 0.00, 0.02),
    ]
    rows: list[dict[str, Any]] = []
    wins = selected["Win"].astype(int).to_numpy()
    average = selected["AverageOdd"].astype(float).to_numpy()
    best = selected["BestOdd"].astype(float).to_numpy()
    for label, capture, haircut in scenarios:
        executable = (average + capture * (best - average)) * (1.0 - haircut)
        profits = np.where(wins == 1, executable - 1.0, -1.0)
        rows.append(
            {
                "Scenario": label,
                "Capture": capture,
                "Haircut": haircut,
                "Bets": int(len(selected)),
                "Wins": int(wins.sum()),
                "HitRate": float(wins.mean()),
                "AverageOdd": float(executable.mean()),
                "ProfitUnits": float(profits.sum()),
                "ROI": float(profits.mean()),
                "MaxDrawdown": float(max_drawdown(profits)),
            }
        )
    return pd.DataFrame(rows)


def run_backtest(
    zip_path: str | Path,
    validation_seasons: Iterable[int] = range(2018, 2022),
    test_seasons: Iterable[int] = range(2022, 2026),
    cfg: V25Config = CFG,
) -> dict[str, Any]:
    matches = normalize_zip(zip_path)
    predictions = build_pre_match_probabilities(matches, cfg)
    market_rows = build_market_rows(predictions, cfg)
    zone_metrics = build_zone_season_metrics(market_rows)

    validation_candidates, validation_approvals = generate_approved_candidates(market_rows, zone_metrics, validation_seasons, cfg)
    validation_selected = select_weekly_top(validation_candidates, cfg)

    test_candidates, test_approvals = generate_approved_candidates(market_rows, zone_metrics, test_seasons, cfg)
    test_selected = select_weekly_top(test_candidates, cfg)

    return {
        "version": VERSION,
        "config": asdict(cfg),
        "matches": matches,
        "predictions": predictions,
        "market_rows": market_rows,
        "zone_metrics": zone_metrics,
        "validation_candidates": validation_candidates,
        "validation_approvals": validation_approvals,
        "validation_selected": validation_selected,
        "validation_metrics": performance_metrics(validation_selected, cfg),
        "test_candidates": test_candidates,
        "test_approvals": test_approvals,
        "test_selected": test_selected,
        "test_metrics": performance_metrics(test_selected, cfg),
        "test_by_season": grouped_metrics(test_selected, ["Season"]),
        "test_by_league": grouped_metrics(test_selected, ["League"]),
        "test_by_market": grouped_metrics(test_selected, ["Market", "Side"]),
        "test_by_month": grouped_metrics(test_selected.assign(Month=pd.to_datetime(test_selected["DateParsed"]).dt.month), ["Month"]),
        "price_stress": price_stress(test_selected),
    }


def build_current_state(matches: list[dict[str, Any]], cfg: V25Config = CFG) -> dict[str, Any]:
    """Calcula o estado pré-jogo depois de todos os jogos carregados.

    Usado pelo app para analisar um confronto novo sem inserir resultado futuro.
    """
    league_history: dict[str, deque[tuple[int, int]]] = defaultdict(lambda: deque(maxlen=1000))
    team_overall: dict[tuple[str, str], deque[tuple[int, int]]] = defaultdict(lambda: deque(maxlen=cfg.overall_games))
    team_home: dict[tuple[str, str], deque[tuple[int, int]]] = defaultdict(lambda: deque(maxlen=cfg.venue_games))
    team_away: dict[tuple[str, str], deque[tuple[int, int]]] = defaultdict(lambda: deque(maxlen=cfg.venue_games))
    for match in sorted(matches, key=lambda row: (row["DateParsed"], row["League"], row["Home"], row["Away"])):
        code = match["Code"]
        home = match["Home"]
        away = match["Away"]
        hg, ag = match["HG"], match["AG"]
        league_history[code].append((hg, ag))
        team_overall[(code, home)].append((hg, ag))
        team_overall[(code, away)].append((ag, hg))
        team_home[(code, home)].append((hg, ag))
        team_away[(code, away)].append((ag, hg))
    return {
        "league_history": league_history,
        "team_overall": team_overall,
        "team_home": team_home,
        "team_away": team_away,
    }


def sports_probabilities_for_match(
    code: str,
    home: str,
    away: str,
    state: dict[str, Any],
    cfg: V25Config = CFG,
) -> dict[str, float]:
    league_history = state["league_history"][code]
    team_overall = state["team_overall"]
    team_home = state["team_home"]
    team_away = state["team_away"]
    if len(league_history) < cfg.min_league_games:
        raise ValueError("A liga ainda não possui histórico suficiente.")
    if len(team_overall[(code, home)]) < cfg.min_team_games or len(team_overall[(code, away)]) < cfg.min_team_games:
        raise ValueError("Uma das equipes ainda não possui o mínimo de jogos históricos.")

    league_home_goals = _weighted_average([x[0] for x in league_history], cfg.league_decay) or 1.35
    league_away_goals = _weighted_average([x[1] for x in league_history], cfg.league_decay) or 1.10

    def team_rates(team: str, venue: str) -> tuple[float, float, float]:
        overall = list(team_overall[(code, team)])
        venue_values = list(team_home[(code, team)] if venue == "H" else team_away[(code, team)])
        overall_for = _weighted_average([x[0] for x in overall], cfg.team_decay) or 0.0
        overall_against = _weighted_average([x[1] for x in overall], cfg.team_decay) or 0.0
        venue_for = _weighted_average([x[0] for x in venue_values], cfg.team_decay) or overall_for
        venue_against = _weighted_average([x[1] for x in venue_values], cfg.team_decay) or overall_against
        goals_for = cfg.venue_weight * venue_for + (1.0 - cfg.venue_weight) * overall_for
        goals_against = cfg.venue_weight * venue_against + (1.0 - cfg.venue_weight) * overall_against
        effective_n = cfg.venue_weight * min(len(venue_values), cfg.venue_games) + (1.0 - cfg.venue_weight) * min(len(overall), cfg.overall_games)
        return goals_for, goals_against, effective_n

    home_for, home_against, home_n = team_rates(home, "H")
    away_for, away_against, away_n = team_rates(away, "A")

    def shrink_ratio(value: float, base: float, sample_size: float) -> float:
        return (value * sample_size + base * cfg.pseudo_games) / max(base * (sample_size + cfg.pseudo_games), 1e-9)

    lambda_home = min(4.0, max(0.15, league_home_goals * shrink_ratio(home_for, league_home_goals, home_n) * shrink_ratio(away_against, league_home_goals, away_n)))
    lambda_away = min(3.5, max(0.10, league_away_goals * shrink_ratio(away_for, league_away_goals, away_n) * shrink_ratio(home_against, league_away_goals, home_n)))
    result = _poisson_probabilities(lambda_home, lambda_away, cfg.dixon_coles_rho)
    return {"LambdaHome": lambda_home, "LambdaAway": lambda_away, **result}



def diagnosticar_zona_historica(
    zone_metrics: pd.DataFrame,
    season: int,
    market: str,
    side: str,
    market_band: float,
    difference_band: float,
    cfg: V25Config = CFG,
) -> dict[str, Any]:
    """Explica por que uma faixa foi ou não aprovada pela regra da V25.

    Diferente da versão anterior, a amostra não vira zero só porque a faixa falhou
    algum critério. O aplicativo passa a mostrar a amostra observada e os critérios
    que efetivamente impediram a aprovação.
    """
    required_columns = set(ZONE_KEYS + ["Season", "Bets", "Wins", "ProfitUnits", "ROI"])
    if zone_metrics.empty or not required_columns.issubset(zone_metrics.columns):
        return {
            "MarketHistoryAvailable": False,
            "ExactZoneObserved": False,
            "RawBets": 0,
            "EligibleBets": 0,
            "SeasonsObserved": 0,
            "EligibleSeasons": 0,
            "PositiveSeasons": 0,
            "HistoricalHitRate": None,
            "HistoricalROI": None,
            "RecentSeasonROI": None,
            "RecentSeasonBets": 0,
            "Approved": False,
            "FailureCodes": ["BASE_HISTORICA_INDISPONIVEL"],
        }

    history = zone_metrics[
        (zone_metrics["Season"] >= season - cfg.lookback_seasons)
        & (zone_metrics["Season"] < season)
        & (zone_metrics["Market"] == market)
        & (zone_metrics["Side"] == side)
    ].copy()
    market_available = not history.empty and int(history["Bets"].sum()) > 0

    exact = history[
        np.isclose(history["MarketBand"].astype(float), float(market_band), atol=1e-9)
        & np.isclose(history["DifferenceBand"].astype(float), float(difference_band), atol=1e-9)
    ].copy()
    exact_observed = not exact.empty and int(exact["Bets"].sum()) > 0
    raw_bets = int(exact["Bets"].sum()) if exact_observed else 0
    seasons_observed = int(exact["Season"].nunique()) if exact_observed else 0

    eligible = exact[exact["Bets"] >= cfg.min_zone_bets_per_season].copy() if exact_observed else exact
    eligible_bets = int(eligible["Bets"].sum()) if not eligible.empty else 0
    eligible_seasons = int(eligible["Season"].nunique()) if not eligible.empty else 0
    total_wins = int(eligible["Wins"].sum()) if not eligible.empty else 0
    total_profit = float(eligible["ProfitUnits"].sum()) if not eligible.empty else 0.0
    historical_hit = total_wins / eligible_bets if eligible_bets > 0 else None
    historical_roi = total_profit / eligible_bets if eligible_bets > 0 else None
    positive_seasons = int((eligible["ROI"] > 0).sum()) if not eligible.empty else 0

    recent = eligible[eligible["Season"] == season - 1]
    recent_roi = float(recent.iloc[0]["ROI"]) if not recent.empty else None
    recent_bets = int(recent.iloc[0]["Bets"]) if not recent.empty else 0

    failures: list[str] = []
    if not market_available:
        failures.append("SEM_DADOS_DO_MERCADO")
    elif not exact_observed:
        failures.append("FAIXA_NAO_OBSERVADA")
    elif eligible.empty:
        failures.append("AMOSTRA_POR_TEMPORADA_INSUFICIENTE")
    else:
        if eligible_bets < cfg.min_zone_total_bets:
            failures.append("AMOSTRA_TOTAL_INSUFICIENTE")
        if eligible_seasons < cfg.min_positive_seasons:
            failures.append("TEMPORADAS_OBSERVADAS_INSUFICIENTES")
        if positive_seasons < cfg.min_positive_seasons:
            failures.append("TEMPORADAS_POSITIVAS_INSUFICIENTES")
        if historical_roi is None or historical_roi < cfg.min_zone_roi:
            failures.append("RETORNO_HISTORICO_INSUFICIENTE")
        if recent_roi is None:
            failures.append("SEM_TEMPORADA_RECENTE_ELEGIVEL")
        elif recent_roi < cfg.min_recent_season_roi:
            failures.append("RETORNO_RECENTE_INSUFICIENTE")
        if historical_hit is None or historical_hit < cfg.min_zone_hit_rate:
            failures.append("ACERTO_HISTORICO_INSUFICIENTE")

    return {
        "MarketHistoryAvailable": market_available,
        "ExactZoneObserved": exact_observed,
        "RawBets": raw_bets,
        "EligibleBets": eligible_bets,
        "SeasonsObserved": seasons_observed,
        "EligibleSeasons": eligible_seasons,
        "PositiveSeasons": positive_seasons,
        "HistoricalHitRate": historical_hit,
        "HistoricalROI": historical_roi,
        "RecentSeasonROI": recent_roi,
        "RecentSeasonBets": recent_bets,
        "Approved": not failures,
        "FailureCodes": failures,
    }


def evaluate_live_market(
    league_code: str,
    season: int,
    home: str,
    away: str,
    average_odds: dict[str, float],
    best_odds: dict[str, float],
    sports: dict[str, float],
    zone_metrics: pd.DataFrame,
    cfg: V25Config = CFG,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add_group(market: str, sides: list[str], average_keys: list[str], best_keys: list[str], sports_keys: list[str]) -> None:
        if not all(key in average_odds and average_odds[key] and average_odds[key] > 1.0 for key in average_keys):
            return
        probabilities = no_vig_probabilities([average_odds[key] for key in average_keys])
        for index, side in enumerate(sides):
            best = best_odds.get(best_keys[index]) or average_odds[average_keys[index]]
            executable = best
            sports_probability = sports[sports_keys[index]]
            difference = sports_probability - probabilities[index]
            p_band = round(math.floor(probabilities[index] / cfg.market_probability_band) * cfg.market_probability_band, 3)
            d_band = round(math.floor((difference + 0.20) / cfg.model_market_difference_band) * cfg.model_market_difference_band - 0.20, 3)

            diagnostico = diagnosticar_zona_historica(
                zone_metrics,
                season,
                market,
                side,
                p_band,
                d_band,
                cfg,
            )
            historical_hit = diagnostico["HistoricalHitRate"]
            historical_roi = diagnostico["HistoricalROI"]
            status = "APROVADA" if diagnostico["Approved"] and executable <= cfg.max_executable_odd else "BLOQUEADA"

            rows.append(
                {
                    "League": LEAGUES[league_code],
                    "Season": season,
                    "Home": home,
                    "Away": away,
                    "Market": market,
                    "Side": side,
                    "MarketProbability": probabilities[index],
                    "SportsProbability": sports_probability,
                    "ProbabilityDifference": difference,
                    "AverageOdd": average_odds[average_keys[index]],
                    "BestOdd": best,
                    "ExecutableOdd": executable,
                    "MarketBand": p_band,
                    "DifferenceBand": d_band,
                    # A amostra agora representa o que realmente foi observado,
                    # mesmo quando a faixa não passou nos critérios de aprovação.
                    "HistoricalBets": int(diagnostico["EligibleBets"] or diagnostico["RawBets"]),
                    "HistoricalRawBets": int(diagnostico["RawBets"]),
                    "HistoricalEligibleBets": int(diagnostico["EligibleBets"]),
                    "HistoricalSeasonsObserved": int(diagnostico["SeasonsObserved"]),
                    "HistoricalEligibleSeasons": int(diagnostico["EligibleSeasons"]),
                    "HistoricalPositiveSeasons": int(diagnostico["PositiveSeasons"]),
                    "HistoricalMarketAvailable": bool(diagnostico["MarketHistoryAvailable"]),
                    "HistoricalExactZoneObserved": bool(diagnostico["ExactZoneObserved"]),
                    "HistoricalRecentROI": diagnostico["RecentSeasonROI"],
                    "HistoricalRecentBets": int(diagnostico["RecentSeasonBets"]),
                    "HistoricalHitRate": historical_hit,
                    "HistoricalROI": historical_roi,
                    "HistoricalEVAtCurrentPrice": historical_hit * executable - 1.0 if historical_hit is not None else None,
                    "ValidationFailures": ",".join(diagnostico["FailureCodes"]),
                    "Status": status,
                }
            )

    add_group("1X2", ["H", "D", "A"], ["H", "D", "A"], ["H", "D", "A"], ["H", "D", "A"])
    if all(key in average_odds for key in ("O25", "U25")):
        add_group("OU", ["O25", "U25"], ["O25", "U25"], ["O25", "U25"], ["O25", "U25"])
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["Status", "MarketProbability", "HistoricalHitRate"], ascending=[True, False, False])
    return frame
