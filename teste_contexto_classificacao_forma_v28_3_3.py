from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from tex_filtro_2018 import FILTER_API_VERSION, build_game_form_context, build_lot_form_contexts
from tex_v25_core import normalize_zip

ROOT = Path(__file__).resolve().parent
MATCH_DATE = date(2026, 8, 8)

matches = normalize_zip(
    ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip",
    include_incomplete_annual_2026=True,
)
game = {
    "ID": "forma-gremio-sao-paulo",
    "Código da liga": "BRA",
    "Liga": "Brasileirão Série A",
    "Mandante": "Gremio",
    "Visitante": "Sao Paulo",
    "Data": MATCH_DATE.isoformat(),
}

context = build_game_form_context(game, matches)
assert FILTER_API_VERSION == "28.3.10"
assert context["HomeTeam"] == "Gremio"
assert context["AwayTeam"] == "Sao Paulo"
assert context["HomeStanding"]["Available"]
assert context["AwayStanding"]["Available"]
assert context["HomeStanding"]["Position"] >= 1
assert context["AwayStanding"]["Position"] >= 1

for key in ("HomeOverall", "HomeAtHome", "AwayOverall", "AwayAway"):
    rows = context[key]
    assert len(rows) == 5, (key, len(rows))
    assert all(item["DateParsed"] < MATCH_DATE for item in rows)
    assert all(item["Result"] in {"V", "E", "D"} for item in rows)
    assert all(item["Score"] for item in rows)

assert all(item["Venue"] == "Casa" for item in context["HomeAtHome"])
assert all(item["Venue"] == "Fora" for item in context["AwayAway"])
assert any(item["Venue"] == "Fora" for item in context["HomeOverall"])
assert any(item["Venue"] == "Casa" for item in context["AwayOverall"])

lot = build_lot_form_contexts(pd.DataFrame([game]), matches)
assert set(lot) == {game["ID"]}
assert lot[game["ID"]]["HomeStanding"] == context["HomeStanding"]

print("TESTE DE CLASSIFICAÇÃO E FORMA V28.3.3: OK")
