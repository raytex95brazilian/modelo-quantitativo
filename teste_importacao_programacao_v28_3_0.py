from pathlib import Path

from tex_importador_programacao import (
    IMPORTER_API_VERSION,
    infer_league_and_teams,
    parse_pasted_schedule,
    resolve_imported_matches,
)
from tex_operacional_core import latest_team_catalog
from tex_v25_core import LEAGUES, normalize_zip

assert IMPORTER_API_VERSION == "28.3.14"

RAW = """
08/08
16:00
Grêmio
São Paulo SP

Grêmio
2.32

Empate
3.09

São Paulo SP
2.92

Grêmio
2.88

Empate
2.03

São Paulo SP
3.52

Mais de
2.5
2.03

Menos de
2.5
1.65

Sim
1.81

Não
1.85
252

08/08
18:30
Clube Do Remo
Atlético MG

Clube Do Remo
2.86

Empate
3.10

Atlético MG
2.35

Clube Do Remo
3.44

Empate
2.04

Atlético MG
2.92
247

09/08
16:00
EC Bahia
Vasco da Gama

EC Bahia
1.81

Empate
3.53

Vasco da Gama
3.81
"""

parsed = parse_pasted_schedule(RAW, default_year=2026)
assert len(parsed) == 3, parsed
assert parsed[0]["data"] == "2026-08-08"
assert parsed[0]["hora"] == "16:00"
assert parsed[0]["mandante_original"] == "Grêmio"
assert parsed[0]["visitante_original"] == "São Paulo SP"
assert parsed[0]["odd_mandante"] == 2.32
assert parsed[0]["odd_empate"] == 3.09
assert parsed[0]["odd_visitante"] == 2.92
# O segundo bloco 1X2 e os mercados adicionais não podem sobrescrever o Resultado Final.
assert parsed[0]["odd_mandante"] != 2.88

root = Path(__file__).resolve().parent
matches = normalize_zip(root / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)
teams_by_code, _ = latest_team_catalog(matches)
resolved = resolve_imported_matches(parsed, teams_by_code=teams_by_code, leagues=LEAGUES)
assert all(item["Status"] == "RECONHECIDO" for item in resolved), resolved
assert all(item["Liga"] == "Brasileirão Série A" for item in resolved), resolved
assert resolved[0]["Mandante"] == "Gremio"
assert resolved[0]["Visitante"] == "Sao Paulo"
assert resolved[1]["Mandante"] == "Remo"
assert resolved[1]["Visitante"] == "Atletico-MG"
assert resolved[2]["Mandante"] == "Bahia"
assert resolved[2]["Visitante"] == "Vasco"

mls = infer_league_and_teams(
    "NY City",
    "Inter Miami",
    teams_by_code=teams_by_code,
    leagues=LEAGUES,
)
assert mls["status"] == "RECONHECIDO", mls
assert mls["league_code"] == "USA", mls
assert mls["home"] == "New York City", mls
assert mls["away"] == "Inter Miami", mls

england = infer_league_and_teams(
    "Manchester City",
    "Arsenal",
    teams_by_code=teams_by_code,
    leagues=LEAGUES,
)
assert england["status"] == "RECONHECIDO", england
assert england["league_code"] == "E0", england
assert england["home"] == "Man City", england

print("TESTE DE IMPORTAÇÃO INTELIGENTE V28.3.0: OK")
