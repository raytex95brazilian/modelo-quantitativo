from __future__ import annotations

from tex_importador_programacao import (
    IMPORTER_API_VERSION,
    infer_league_and_teams,
    resolve_team_in_league,
)

TEAMS = {
    "FIN": [
        "AC Oulu", "Gnistan", "HJK", "Ilves", "Inter Turku", "Jaro",
        "KuPS", "Lahti", "Mariehamn", "SJK", "TPS", "VPS",
    ],
    "SWE": ["AIK", "Djurgarden", "Hammarby", "Malmo FF"],
}
LEAGUES = {
    "FIN": "Finlândia - Veikkausliiga",
    "SWE": "Suécia - Allsvenskan",
}

assert IMPORTER_API_VERSION == "28.3.16"

EXPECTED = {
    "VPS Vaasa": "VPS",
    "Vaasan Palloseura": "VPS",
    "Ilves Tampere": "Ilves",
    "Tampereen Ilves": "Ilves",
    "Seinajoen JK": "SJK",
    "Seinäjoen JK": "SJK",
    "SJK Seinajoki": "SJK",
    "Seinajoen Jalkapallokerho": "SJK",
}
for raw, canonical in EXPECTED.items():
    resolved, score = resolve_team_in_league(raw, "FIN", TEAMS, match_date="2026-08-01")
    assert resolved == canonical, (raw, resolved, score)
    assert score == 1.0, (raw, resolved, score)

for home_raw, away_raw, home, away in (
    ("VPS Vaasa", "Ilves Tampere", "VPS", "Ilves"),
    ("Seinajoen JK", "VPS Vaasa", "SJK", "VPS"),
    ("Ilves Tampere", "Seinajoen JK", "Ilves", "SJK"),
):
    result = infer_league_and_teams(
        home_raw, away_raw, teams_by_code=TEAMS, leagues=LEAGUES, match_date="2026-08-01"
    )
    assert result["status"] == "RECONHECIDO", result
    assert result["league_code"] == "FIN", result
    assert result["home"] == home, result
    assert result["away"] == away, result
    assert result["home_score"] == 1.0, result
    assert result["away_score"] == 1.0, result

print("TESTE DE RECONHECIMENTO DA VEIKKAUSLIIGA V28.3.16: OK")
