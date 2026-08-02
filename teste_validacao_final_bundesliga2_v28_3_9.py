from pathlib import Path

from tex_importador_programacao import IMPORTER_API_VERSION, resolve_team_in_league
from tex_operacional_core import latest_team_catalog
from tex_v25_core import normalize_zip

assert IMPORTER_API_VERSION == "28.3.15"

root = Path(__file__).resolve().parent
matches = normalize_zip(root / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)
teams_by_code, _ = latest_team_catalog(matches)

# Estes quatro clubes eram reconhecidos na prévia, mas rejeitados na confirmação final.
fixtures = {
    "Heidenheim": "Heidenheim",
    "Wolfsburg": "Wolfsburg",
    "Cottbus": "Cottbus",
    "St Pauli": "St Pauli",
}
for raw, expected in fixtures.items():
    canonical, score = resolve_team_in_league(
        raw, "D2", teams_by_code, match_date="2026-08-08"
    )
    assert canonical == expected, (raw, canonical, score)
    assert score >= 0.98, (raw, canonical, score)

# O overlay sazonal não pode contaminar a temporada anterior.
canonical_old, score_old = resolve_team_in_league(
    "Wolfsburg", "D2", teams_by_code, match_date="2025-08-08"
)
assert canonical_old != "Wolfsburg" or score_old < 0.72, (canonical_old, score_old)

print("TESTE DE VALIDAÇÃO FINAL SAZONAL V28.3.9: OK")
