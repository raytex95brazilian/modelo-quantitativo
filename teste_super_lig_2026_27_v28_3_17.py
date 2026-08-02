from pathlib import Path

from tex_importador_programacao import (
    IMPORTER_API_VERSION,
    canonicalize_new_team_name,
    infer_league_and_teams,
    resolve_team_in_league,
)
from tex_operacional_core import all_team_catalog, latest_team_catalog, seasonal_team_catalog
from tex_v25_core import LEAGUES, normalize_zip

ROOT = Path(__file__).resolve().parent
assert IMPORTER_API_VERSION == "28.3.17"
assert canonicalize_new_team_name("Çorum FK") == "Corum FK"
assert canonicalize_new_team_name("Amed SK") == "Amed SK"
assert canonicalize_new_team_name("Empate") == ""

matches = normalize_zip(ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)
all_teams = all_team_catalog(matches)
latest, _ = latest_team_catalog(matches)
seasonal = seasonal_team_catalog(matches)

cases = {
    "Çorum FK": "Corum FK",
    "Corum FK": "Corum FK",
    "Ahlatçı Çorum FK": "Corum FK",
    "Amed SK": "Amed SK",
    "Amedspor": "Amed SK",
    "Amed Sportif Faaliyetler": "Amed SK",
    "Göztepe İzmir": "Goztep",
    "Goztepe Izmir": "Goztep",
    "Göztepe SK": "Goztep",
}
for raw, expected in cases.items():
    resolved, score = resolve_team_in_league(
        raw,
        "T1",
        all_teams,
        match_date="2026-08-08",
        preferred_teams_by_code=latest,
        teams_by_season=seasonal,
    )
    assert resolved == expected, (raw, resolved, score)
    assert score >= 0.98, (raw, resolved, score)

pair = infer_league_and_teams(
    "Amed SK",
    "Goztepe Izmir",
    teams_by_code=all_teams,
    leagues=LEAGUES,
    match_date="2026-08-08",
    preferred_teams_by_code=latest,
    teams_by_season=seasonal,
)
assert pair["status"] == "RECONHECIDO", pair
assert pair["league_code"] == "T1", pair
assert pair["home"] == "Amed SK", pair
assert pair["away"] == "Goztep", pair

pair = infer_league_and_teams(
    "Galatasaray",
    "Corum FK",
    teams_by_code=all_teams,
    leagues=LEAGUES,
    match_date="2026-08-08",
    preferred_teams_by_code=latest,
    teams_by_season=seasonal,
)
assert pair["status"] == "RECONHECIDO", pair
assert pair["league_code"] == "T1", pair
assert pair["home"] == "Galatasaray", pair
assert pair["away"] == "Corum FK", pair

print("TESTE SÜPER LIG 2026/27 V28.3.17: OK")
