from tex_importador_programacao import IMPORTER_API_VERSION, resolve_team_in_league

assert IMPORTER_API_VERSION == "28.3.17"

cases = [
    ("SWE", "IFK Gotemburgo", "Goteborg"),
    ("SWE", "IFK Gothenburg", "Goteborg"),
    ("D1", "Bayern de Munique", "Bayern Munich"),
    ("I1", "Inter de Milão", "Inter"),
    ("P1", "Sporting de Lisboa", "Sp Lisbon"),
]
teams = {
    "SWE": ["Goteborg", "Malmo FF", "Hacken"],
    "D1": ["Bayern Munich", "Dortmund"],
    "I1": ["Inter", "Milan"],
    "P1": ["Sp Lisbon", "Benfica"],
}
for code, raw, expected in cases:
    resolved, score = resolve_team_in_league(raw, code, teams)
    assert resolved == expected, (code, raw, resolved, score)
    assert score >= 0.98, (code, raw, score)

print("TESTE DE NOMES LOCALIZADOS V28.3.17: OK")
