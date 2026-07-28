from pathlib import Path
import pandas as pd

from tex_v25_core import normalize_zip
from tex_v28_core import (
    INPUT_COLUMNS,
    V28Config,
    V28_CFG,
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
assert V28_CFG.max_entries == 5
overround = validate_market_odds("1X2", [1.99, 3.24, 3.87])
assert 1.069 < overround < 1.070

# 2) A mistura observada no resumo antigo deve ser bloqueada.
try:
    validate_market_odds("1X2", [1.99, 4.55, 7.30])
except ValueError as exc:
    assert "COTAÇÕES INCONSISTENTES" in str(exc)
else:
    raise AssertionError("Linha 1X2 inconsistente não foi bloqueada")

# 3) Qualquer alteração de odd precisa invalidar o hash do lote.
fingerprint_before = lot_fingerprint(games)
changed = games.copy(deep=True)
changed.loc[0, "Odd empate"] = 4.55
fingerprint_after = lot_fingerprint(changed)
assert fingerprint_before != fingerprint_after
fingerprint_bankroll = lot_fingerprint(games, 1000.0, 0.01, 4)
fingerprint_other_bankroll = lot_fingerprint(games, 1200.0, 0.01, 4)
fingerprint_other_unit = lot_fingerprint(games, 1000.0, 0.02, 4)
fingerprint_other_limit = lot_fingerprint(games, 1000.0, 0.01, 3)
fingerprint_registered = lot_fingerprint(games, 1000.0, 0.01, 4, {"2026-30": 1})
fingerprint_registered_match = lot_fingerprint(
    games,
    1000.0,
    0.01,
    4,
    {"2026-30": 1},
    {"BRA|2026-07-25|Athletico-PR|Internacional"},
)
assert len({
    fingerprint_bankroll,
    fingerprint_other_bankroll,
    fingerprint_other_unit,
    fingerprint_other_limit,
    fingerprint_registered,
    fingerprint_registered_match,
}) == 6

# 4) Três jogos consecutivos não podem compartilhar cotações.
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
ath_market = evaluations[
    (evaluations["InputID"] == "ath") & (evaluations["Market"] == "1X2")
]
expected_margin = sum(1.0 / odd for odd in [1.99, 3.24, 3.87]) - 1.0
assert ath_market["MarketMargin"].nunique() == 1
assert abs(float(ath_market.iloc[0]["MarketMargin"]) - expected_margin) < 1e-12

# Valores antigos abaixo de cinco são automaticamente elevados para a meta mínima de cinco.
legacy_entries, _, _, _ = analyze_games(games, matches, model, 1000, 0.01, 0)
assert len(legacy_entries) <= len(games)

# 5) Leitura experimental não pode ultrapassar mercado validado na leitura principal.
assert not readings["Status"].eq("EXPERIMENTAL").any(), readings[["InputID", "Status", "Selection"]].to_string(index=False)

# 6) Apostas já registradas precisam consumir o limite da semana, inclusive em outro lote.
permissive_cfg = V28Config(
    unit_fraction=0.01,
    weekly_target=5,
    strong_price_ev=0.0,
    weekly_portfolio_ev_floor=0.0,
    fallback_min_ev=-1.0,
    near_conservative_ev=-1.0,
    minimum_profile_sample=0,
)
open_entries, _, _, _ = analyze_games(
    games, matches, model, 1000, 0.01, 5, cfg=permissive_cfg
)
blocked_entries, _, blocked_evaluations, _ = analyze_games(
    games,
    matches,
    model,
    1000,
    0.01,
    5,
    cfg=permissive_cfg,
    existing_week_counts={"2026-30": 5},
)
assert not open_entries.empty
assert blocked_entries.empty
qualified_reserves = blocked_evaluations[blocked_evaluations["StatusBase"].isin(["CANDIDATA PRINCIPAL", "CANDIDATA DE COMPLEMENTO"])]
assert qualified_reserves["Status"].eq("NÃO SELECIONADA").all()
assert qualified_reserves["Reason"].str.contains("já foi atingida", regex=False).all()

match_blocked_entries, _, match_blocked_evaluations, _ = analyze_games(
    games,
    matches,
    model,
    1000,
    0.01,
    5,
    cfg=permissive_cfg,
    existing_match_ids={"BRA|2026-07-25|Athletico-PR|Internacional"},
)
assert not match_blocked_entries["MatchID"].astype(str).eq(
    "BRA|2026-07-25|Athletico-PR|Internacional"
).any()
blocked_match_rows = match_blocked_evaluations[
    match_blocked_evaluations["MatchID"].astype(str).eq(
        "BRA|2026-07-25|Athletico-PR|Internacional"
    )
    & match_blocked_evaluations["StatusBase"].isin(["CANDIDATA PRINCIPAL", "CANDIDATA DE COMPLEMENTO"])
]
assert blocked_match_rows["Status"].eq("NÃO SELECIONADA").all()
assert blocked_match_rows["Reason"].str.contains("já possui uma aposta", regex=False).all()

print("TESTE V28.1.5.12 — ESTADO, ISOLAMENTO, COTAÇÕES E META SEMANAL: OK")
print(evaluations[evaluations["Market"].eq("1X2")][["InputID", "Home", "Away", "Side", "Odd", "MarketProbability"]].to_string(index=False))
