from pathlib import Path
import pandas as pd

from tex_v25_core import LEAGUES, normalize_zip
from tex_operacional_core import analyze_games, latest_team_catalog, load_calibration_book

ROOT = Path(__file__).resolve().parent
matches = normalize_zip(ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)
book = load_calibration_book(ROOT / "calibration")
teams, seasons = latest_team_catalog(matches)

assert len(teams) == 24
assert all(teams[code] for code in LEAGUES)
assert len(teams["BRA"]) == 20
assert seasons["BRA"] == 2026

sample = pd.DataFrame([
    {
        "ID": "bot-vic",
        "Data": "2026-07-23",
        "Hora": "20:00",
        "Código da liga": "BRA",
        "Liga": LEAGUES["BRA"],
        "Mandante": "Botafogo RJ",
        "Visitante": "Vitoria",
        "Casa de apostas": "Pixbet",
        "Odd mandante": 1.80,
        "Odd empate": 3.58,
        "Odd visitante": 4.84,
        "Odd mais de 2,5": 1.78,
        "Odd menos de 2,5": 1.99,
        "Odd ambas marcam — Sim": 1.71,
        "Odd ambas marcam — Não": 2.11,
    },
    {
        "ID": "san-cha",
        "Data": "2026-07-23",
        "Hora": "21:00",
        "Código da liga": "BRA",
        "Liga": LEAGUES["BRA"],
        "Mandante": "Santos",
        "Visitante": "Chapecoense-SC",
        "Casa de apostas": "Pixbet",
        "Odd mandante": 1.41,
        "Odd empate": 4.51,
        "Odd visitante": 7.00,
        "Odd mais de 2,5": 1.66,
        "Odd menos de 2,5": 2.14,
        "Odd ambas marcam — Sim": 1.87,
        "Odd ambas marcam — Não": 1.89,
    },
    {
        "ID": "bra-cor",
        "Data": "2026-07-26",
        "Hora": "18:30",
        "Código da liga": "BRA",
        "Liga": LEAGUES["BRA"],
        "Mandante": "Bragantino",
        "Visitante": "Coritiba",
        "Casa de apostas": "Pixbet",
        "Odd mandante": 1.60,
        "Odd empate": 4.10,
        "Odd visitante": 5.60,
        "Odd mais de 2,5": 1.86,
        "Odd menos de 2,5": 1.94,
        "Odd ambas marcam — Sim": 1.90,
        "Odd ambas marcam — Não": 1.92,
    },
])
entries, readings, evaluations, diagnostics = analyze_games(sample, matches, book, 1000.0, 0.01, 4)
assert len(readings) == 3  # sempre uma leitura por partida
assert len(evaluations) == 21  # 7 seleções por jogo
assert set(evaluations["Market"]) == {"1X2", "OU25", "BTTS"}
assert not ((evaluations["Odd"] > 3.0) & evaluations["Status"].eq("OPERAR")).any()
assert not ((evaluations["Home"] == "Bragantino") & (evaluations["Side"] == "O25") & evaluations["Status"].eq("OPERAR")).any()
assert entries.empty or entries["Stake"].eq(10.0).all()
assert diagnostics["Situação"].eq("ANALISADO").all()

# Confirma que o motor consegue liberar uma entrada quando a cotação realmente
# supera o preço mínimo, sem depender do portão binário da V25.
price_test = sample.iloc[[1]].copy()
price_test.loc[:, "Odd mandante"] = 1.70
entries2, readings2, evaluations2, diagnostics2 = analyze_games(price_test, matches, book, 1000.0, 0.01, 4)
assert len(entries2) == 1
assert entries2.iloc[0]["Selection"] == "Santos"
assert entries2.iloc[0]["Stake"] == 10.0

print("TESTES OPERACIONAIS APROVADOS")
print(f"Ligas: {len(teams)} | Times no Brasileirão: {len(teams['BRA'])}")
print(f"Jogo real: {len(readings)} leituras e {len(evaluations)} seleções avaliadas")
print("Ambas marcam presente; odds acima de 3 bloqueadas; unidade fixa confirmada")
