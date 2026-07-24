from pathlib import Path
import pandas as pd

from tex_v25_core import normalize_zip
from tex_v28_core import (
    INPUT_COLUMNS,
    analyze_games,
    load_v28_model,
    lot_fingerprint,
    validate_market_odds,
)

ROOT = Path(__file__).resolve().parent
matches = normalize_zip(ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)
model = load_v28_model(ROOT / "model")

base = {
    "Data": "2026-07-25",
    "Hora": "18:30",
    "Código da liga": "BRA",
    "Liga": "Brasileirão Série A",
    "Casa de apostas": "Pixbet",
    "Odd mais de 2,5": 2.22,
    "Odd menos de 2,5": 1.61,
    "Odd ambas marcam — Sim": 1.99,
    "Odd ambas marcam — Não": 1.78,
}

athletico = {
    **base,
    "ID": "ath",
    "Mandante": "Athletico-PR",
    "Visitante": "Internacional",
    "Odd mandante": 1.99,
    "Odd empate": 3.24,
    "Odd visitante": 3.87,
}
santos = {
    **base,
    "ID": "san",
    "Mandante": "Santos",
    "Visitante": "Chapecoense-SC",
    "Odd mandante": 1.40,
    "Odd empate": 4.55,
    "Odd visitante": 7.30,
    "Odd mais de 2,5": 1.66,
    "Odd menos de 2,5": 2.14,
    "Odd ambas marcam — Sim": 1.87,
    "Odd ambas marcam — Não": 1.89,
}
vasco = {
    **base,
    "ID": "vas",
    "Mandante": "Vasco",
    "Visitante": "Mirassol",
    "Odd mandante": 2.02,
    "Odd empate": 3.31,
    "Odd visitante": 3.67,
    "Odd mais de 2,5": 2.02,
    "Odd menos de 2,5": 1.74,
    "Odd ambas marcam — Sim": 1.84,
    "Odd ambas marcam — Não": 1.92,
}

games = pd.DataFrame([athletico, santos, vasco], columns=INPUT_COLUMNS)

# 1) A linha real da Pixbet deve ser aceita e normalizada corretamente.
overround = validate_market_odds("1X2", [1.99, 3.24, 3.87])
assert 1.069 < overround < 1.070

# 2) A mistura observada no resumo antigo deve ser bloqueada.
try:
    validate_market_odds("1X2", [1.99, 4.55, 7.30])
except ValueError as exc:
    assert "ODDS INCONSISTENTES" in str(exc)
else:
    raise AssertionError("Linha 1X2 inconsistente não foi bloqueada")

# 3) Qualquer alteração de odd precisa invalidar o hash do lote.
fingerprint_before = lot_fingerprint(games)
changed = games.copy(deep=True)
changed.loc[0, "Odd empate"] = 4.55
fingerprint_after = lot_fingerprint(changed)
assert fingerprint_before != fingerprint_after

# 4) Três jogos consecutivos não podem compartilhar odds.
entries, readings, evaluations, diagnostics = analyze_games(games, matches, model, 1000, 0.01, 4)
assert diagnostics["Situação"].eq("ANALISADO").all(), diagnostics.to_string(index=False)

expected_1x2 = {
    "ath": {"H": 1.99, "D": 3.24, "A": 3.87},
    "san": {"H": 1.40, "D": 4.55, "A": 7.30},
    "vas": {"H": 2.02, "D": 3.31, "A": 3.67},
}
for input_id, side_odds in expected_1x2.items():
    block = evaluations[(evaluations["InputID"] == input_id) & (evaluations["Market"] == "1X2")]
    actual = dict(zip(block["Side"], block["Odd"]))
    assert actual == side_odds, (input_id, actual, side_odds)

ath_home = evaluations[
    (evaluations["InputID"] == "ath")
    & (evaluations["Market"] == "1X2")
    & (evaluations["Side"] == "H")
].iloc[0]
assert abs(float(ath_home["MarketProbability"]) - 0.4698) < 0.001

# 5) Leitura experimental não pode ultrapassar mercado validado na leitura principal.
assert not readings["Status"].eq("EXPERIMENTAL").any(), readings[["InputID", "Status", "Selection"]].to_string(index=False)

print("TESTE V28.1 — ESTADO, ISOLAMENTO E ODDS: OK")
print(evaluations[evaluations["Market"].eq("1X2")][["InputID", "Home", "Away", "Side", "Odd", "MarketProbability"]].to_string(index=False))
