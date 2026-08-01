from pathlib import Path

from tex_importador_programacao import IMPORTER_API_VERSION, infer_league_and_teams
from tex_operacional_core import latest_team_catalog
from tex_v25_core import LEAGUES, normalize_zip

assert IMPORTER_API_VERSION == "28.3.14"

root = Path(__file__).resolve().parent
matches = normalize_zip(root / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)
teams_by_code, _ = latest_team_catalog(matches)

fixtures = [
    ("Bochum", "Hertha Berlin", "Bochum", "Hertha"),
    ("Magdeburg", "Eintracht Braunschweig", "Magdeburg", "Braunschweig"),
    ("Heidenheim", "Osnabruck", "Heidenheim", "Osnabruck"),
    ("Darmstadt", "Holstein Kiel", "Darmstadt", "Holstein Kiel"),
    ("Karlsruhe", "Bielefeld", "Karlsruhe", "Bielefeld"),
    ("Wolfsburg", "Kaiserslautern", "Wolfsburg", "Kaiserslautern"),
    ("Energie Cottbus", "Hannover", "Cottbus", "Hannover"),
    ("Nurnberg", "Dynamo Dresden", "Nurnberg", "Dresden"),
    ("St Pauli", "Greuther Fürth", "St Pauli", "Greuther Furth"),
]

for home_raw, away_raw, home_expected, away_expected in fixtures:
    result = infer_league_and_teams(
        home_raw,
        away_raw,
        teams_by_code=teams_by_code,
        leagues=LEAGUES,
        match_date="2026-08-08",
    )
    assert result["status"] == "RECONHECIDO", (home_raw, away_raw, result)
    assert result["league_code"] == "D2", (home_raw, away_raw, result)
    assert result["league_name"] == "Alemanha - 2. Bundesliga", result
    assert result["home"] == home_expected, result
    assert result["away"] == away_expected, result

# O overlay não deve ser aplicado a uma temporada anterior.
old = infer_league_and_teams(
    "Wolfsburg",
    "Kaiserslautern",
    teams_by_code=teams_by_code,
    leagues=LEAGUES,
    match_date="2025-08-08",
)
assert old["status"] == "REVISAR", old

print("TESTE DE RECONHECIMENTO DA 2. BUNDESLIGA V28.3.9: OK")
