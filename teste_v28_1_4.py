from __future__ import annotations

import sys
import types
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Dependências mínimas para testar o patch de forma isolada.
v25 = types.ModuleType("tex_v25_core")
class V25Config:  # noqa: D101
    pass
v25.CFG = V25Config()
v25.V25Config = V25Config
v25.LEAGUES = {"BRA1": "Brasileirão Série A"}
v25.build_current_state = lambda previous, cfg: {"previous": previous}
v25.no_vig_probabilities = lambda odds: [(1 / value) / sum(1 / item for item in odds) for value in odds]

def sports_probabilities_for_match(code, home, away, state, cfg):
    return {
        "H": 0.61,
        "D": 0.22,
        "A": 0.17,
        "O25": 0.45,
        "U25": 0.55,
        "BTTS_Y": 0.55,
        "BTTS_N": 0.45,
        "LambdaHome": 1.55,
        "LambdaAway": 0.95,
    }

v25.sports_probabilities_for_match = sports_probabilities_for_match
sys.modules["tex_v25_core"] = v25

oper = types.ModuleType("tex_operacional_core")
oper.INPUT_COLUMNS = [
    "ID", "Data", "Hora", "Código da liga", "Liga", "Mandante", "Visitante",
    "Casa de apostas", "Odd mandante", "Odd empate", "Odd visitante",
    "Odd mais de 2,5", "Odd menos de 2,5", "Odd ambas marcam — Sim",
    "Odd ambas marcam — Não",
]
oper.clean_text = lambda value: "" if value is None else str(value).strip()
oper.enrich_with_standings = lambda frame, games, matches: frame
oper.latest_team_catalog = lambda rows: ({}, {})

def parse_date(value):
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()
oper.parse_date = parse_date
oper.parse_odd = lambda value: None if value is None or value == "" else float(value)
oper.season_for_match = lambda *args, **kwargs: 2026
oper.standings_context = lambda *args, **kwargs: {"Available": False}
sys.modules["tex_operacional_core"] = oper

import tex_v28_core_2814 as core

assert core.CORE_API_VERSION == "28.1.4"

# A correção histórica precisa recuperar Santos com a mesma lógica usada no app.
profile = {
    "Sample": 955,
    "Wins": 706,
    "HitRate": 706 / 955,
    "Confidence": "FORTE",
    "Reliability": 0.895,
}
adjusted = core.adjusted_probability_from_profile(0.718, profile, 100.0, 40)
assert 0.736 < adjusted < 0.738, adjusted
assert adjusted * 1.40 * 0.98 - 1 > 0

# Histórico sintético estritamente anterior ao jogo atual para calibrar Ambas Marcam.
history = []
start = date(2026, 1, 1)
for index in range(60):
    both_score = index % 5 in (0, 1, 2)  # 60% de acerto.
    history.append({
        "Code": "BRA1",
        "DateParsed": start + timedelta(days=index),
        "Home": f"Casa {index}",
        "Away": f"Fora {index}",
        "FTHG": 1,
        "FTAG": 1 if both_score else 0,
    })

class FakeModel:
    def predict(self, code, market, side, market_probability, raw_probability, odd, month):
        mapping = {
            "H": 0.718,
            "D": 0.17,
            "A": 0.11,
            "O25": 0.44,
            "U25": 0.56,
        }
        return mapping[side]

    def reliability_profile(self, code, market, side, probability):
        if side == "H":
            return {
                "Level": "GERAL", "Sample": 955, "Wins": 706,
                "MeanPred": 0.71, "HitRate": 706 / 955,
                "Brier": 0.18, "CalibrationGap": 0.025,
                "Confidence": "FORTE", "Reliability": 0.895,
            }
        return {
            "Level": "GERAL", "Sample": 300, "Wins": round(300 * probability),
            "MeanPred": probability, "HitRate": probability,
            "Brier": 0.22, "CalibrationGap": 0.0,
            "Confidence": "FORTE", "Reliability": 0.9,
        }

current_date = start + timedelta(days=70)
games = pd.DataFrame([{
    "ID": "teste001",
    "Data": current_date.isoformat(),
    "Hora": "19:30",
    "Código da liga": "BRA1",
    "Liga": "Brasileirão Série A",
    "Mandante": "Time A",
    "Visitante": "Time B",
    "Casa de apostas": "Casa teste",
    "Odd mandante": 1.40,
    "Odd empate": 4.00,
    "Odd visitante": 8.00,
    "Odd mais de 2,5": 2.10,
    "Odd menos de 2,5": 1.75,
    "Odd ambas marcam — Sim": 1.83,
    "Odd ambas marcam — Não": 1.95,
}], columns=oper.INPUT_COLUMNS)

entries, readings, evaluations, diagnostics = core.analyze_games(
    games,
    history,
    FakeModel(),
    bankroll=1000.0,
    unit_fraction=0.01,
    max_entries=5,
)

assert diagnostics.iloc[0]["Situação"] == "ANALISADO", diagnostics
assert len(evaluations) == 7, evaluations
assert not entries.empty, evaluations[["Selection", "Status", "ExpectedValue", "ProfileSample"]]
assert entries.iloc[0]["Status"] == "AUTORIZADA"
assert entries.iloc[0]["Selection"] in {"Time A", "Ambas marcam — Sim"}
assert evaluations["Market"].eq("BTTS").sum() == 2
assert "Probabilidade corrigida pelo histórico" in core.display_frame(entries).columns

print("V28.1.4: correção histórica, sete seleções, Ambas Marcam e autorização validadas.")
