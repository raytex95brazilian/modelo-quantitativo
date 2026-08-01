from __future__ import annotations

from pathlib import Path

import pandas as pd

from tex_filtro_2018 import evaluate_lot_2018
from tex_operacao_filtrada import attach_filter_results, build_operational_outputs
from tex_v25_core import LEAGUES, normalize_zip

ROOT = Path(__file__).resolve().parent
matches = normalize_zip(ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)

latest_d2 = max(m["DateParsed"] for m in matches if m["Code"] == "D2")
assert latest_d2.isoformat() == "2026-05-17"
assert max(m["Season"] for m in matches if m["Code"] == "D2") == 2025

future_games = pd.DataFrame([
    {
        "ID": "d2-bochum-hertha",
        "Data": "2026-08-08",
        "Hora": "15:30",
        "Código da liga": "D2",
        "Liga": LEAGUES["D2"],
        "Mandante": "Bochum",
        "Visitante": "Hertha",
    },
    {
        "ID": "d2-cottbus-hannover",
        "Data": "2026-08-09",
        "Hora": "08:30",
        "Código da liga": "D2",
        "Liga": LEAGUES["D2"],
        "Mandante": "Cottbus",
        "Visitante": "Hannover",
    },
])
filters = evaluate_lot_2018(future_games, matches).set_index("InputID")

bochum = filters.loc["d2-bochum-hertha"]
assert not bool(bochum["Filter2018Approved"])
assert bochum["Filter2018Status"] == "NÃO AVALIÁVEL"
assert bochum["Filter2018Rule1Basis"] == "DADOS INSUFICIENTES"
assert "temporada 2026/27" in bochum["Filter2018Rule1Detail"]
assert "17/05/2026" in bochum["Filter2018Rule1Detail"]
assert int(bochum["Filter2018HomeHistoryCount"]) == 5
assert int(bochum["Filter2018AwayHistoryCount"]) == 5

# A versão anterior usava, indevidamente, cinco partidas de Cottbus de 2014 como forma recente.
# Agora apenas a temporada atual ou a imediatamente anterior é aceita para as Regras 3 e 4.
cottbus = filters.loc["d2-cottbus-hannover"]
assert cottbus["Filter2018Status"] == "NÃO AVALIÁVEL"
assert int(cottbus["Filter2018HomeHistoryCount"]) == 0
assert "Regra 3 sem cinco jogos recentes" in cottbus["Filter2018Summary"]

# O portão operacional continua absoluto: não avaliável não entra em simples nem em múltipla.
evaluations = pd.DataFrame([
    {
        "InputID": "d2-bochum-hertha",
        "MatchID": "m1",
        "WeekID": "2026-32",
        "Market": "1X2",
        "Side": "H",
        "Selection": "Bochum",
        "ConservativeExpectedValue": 0.40,
        "ConservativeProbability": 0.70,
        "DecisionProbability": 0.71,
        "Reliability": 0.80,
        "Odd": 2.20,
        "EffectiveOdd": 2.156,
    }
])
merged = attach_filter_results(evaluations, filters.reset_index())
entries, readings, all_rows, multiple = build_operational_outputs(merged, bankroll=1000.0, unit_fraction=0.01)
assert entries.empty
assert multiple.selections.empty
assert len(all_rows) == 1
assert readings.iloc[0]["Status"] == "NÃO AVALIÁVEL — DADOS INSUFICIENTES"

# Casos históricos com dados completos continuam sendo avaliados normalmente.
known_game = pd.DataFrame([{
    "ID": "caso-aprovado",
    "Data": "2025-02-15",
    "Código da liga": "ARG",
    "Liga": "Argentina - Primera Division",
    "Mandante": "Defensa y Justicia",
    "Visitante": "Barracas Central",
}])
known = evaluate_lot_2018(known_game, matches).iloc[0]
assert bool(known["Filter2018Approved"])
assert known["Filter2018Status"] == "APROVADO"

print("TESTE V28.3.10 — INÍCIO DE TEMPORADA E DADOS INSUFICIENTES: OK")
