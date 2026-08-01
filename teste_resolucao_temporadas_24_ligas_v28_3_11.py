from __future__ import annotations

from datetime import date
from pathlib import Path

from tex_operacional_core import resolve_season_for_match, standings_context
from tex_v25_core import normalize_zip

ROOT = Path(__file__).resolve().parent
matches = normalize_zip(ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)

cases = [
    ("MEX", date(2026, 1, 10), 2025),
    ("ARG", date(2021, 1, 10), 2020),
    ("ARG", date(2026, 3, 1), 2026),
    ("BRA", date(2021, 2, 1), 2020),
    ("CHN", date(2022, 1, 5), 2021),
    ("E0", date(2020, 7, 10), 2019),
    ("I1", date(2020, 7, 20), 2019),
    ("SP1", date(2020, 7, 10), 2019),
    ("D2", date(2026, 8, 8), 2026),
]
for code, match_date, expected in cases:
    actual = resolve_season_for_match(matches, code, match_date)
    assert actual == expected, (code, match_date, actual, expected)

# A Liga MX não pode reiniciar falsamente a classificação em janeiro.
ctx_mex = standings_context(matches, "MEX", date(2026, 1, 10), "Club America", "Club Tijuana")
assert ctx_mex["Season"] == 2025
assert ctx_mex["SeasonLabel"] == "2025/26"
assert ctx_mex["SeasonMatchCount"] > 0

# Temporadas excepcionalmente estendidas permanecem vinculadas ao ciclo correto.
ctx_bra = standings_context(matches, "BRA", date(2021, 2, 1), "Sport Recife", "Flamengo RJ")
assert ctx_bra["Season"] == 2020
assert ctx_bra["SeasonMatchCount"] > 0

# Para uma temporada futura ainda sem resultados, o estado continua honestamente não avaliável.
ctx_d2 = standings_context(matches, "D2", date(2026, 8, 8), "Bochum", "Hertha")
assert ctx_d2["Season"] == 2026
assert not ctx_d2["Available"]
assert ctx_d2["UnavailableReasonCode"] == "NO_CURRENT_SEASON_STANDINGS"

print("TESTE V28.3.11 — RESOLUÇÃO DE TEMPORADAS NAS 24 LIGAS: OK")
