from datetime import date
from tex_importador_programacao import IMPORTER_API_VERSION, resolve_team_in_league

assert IMPORTER_API_VERSION == "28.3.17"

# O catálogo histórico deliberadamente não contém o promovido, reproduzindo a falha real.
teams_by_code = {"P1": [
    "Alverca", "Arouca", "Benfica", "Casa Pia", "Estoril", "Estrela",
    "Famalicao", "Gil Vicente", "Guimaraes", "Maritimo", "Moreirense",
    "Nacional", "Porto", "Rio Ave", "Santa Clara", "Sp Braga", "Sp Lisbon",
]}
preferred = {"P1": list(teams_by_code["P1"])}
seasonal = {"P1": {2025: list(teams_by_code["P1"])}}

for raw in ("Academico Viseu", "Académico de Viseu", "Académico Viseu FC", "AC Viseu"):
    team, score = resolve_team_in_league(
        raw, "P1", teams_by_code, match_date=date(2026, 8, 9),
        preferred_teams_by_code=preferred, teams_by_season=seasonal,
    )
    assert team == "Academico Viseu", (raw, team, score)
    assert score >= 0.985, (raw, team, score)

# Controle temporal: o promovido não deve ser injetado em partida da temporada anterior.
team_old, score_old = resolve_team_in_league(
    "Academico Viseu", "P1", teams_by_code, match_date=date(2025, 8, 9),
    preferred_teams_by_code=preferred, teams_by_season=seasonal,
)
assert score_old < 0.72, (team_old, score_old)

print("TESTE PRIMEIRA LIGA 2026/27 V28.3.17: OK")
