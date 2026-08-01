from __future__ import annotations

from pathlib import Path
import unicodedata

from tex_v25_core import LEAGUES, normalize_zip
from tex_operacional_core import all_team_catalog, latest_team_catalog, seasonal_team_catalog
from tex_importador_programacao import (
    IMPORTER_API_VERSION,
    infer_league_and_teams,
    normalize_name,
    resolve_team_in_league,
)

ROOT = Path(__file__).resolve().parent
MATCHES = normalize_zip(ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)
LATEST, _ = latest_team_catalog(MATCHES)
UNIVERSAL = all_team_catalog(MATCHES)
BY_SEASON = seasonal_team_catalog(MATCHES)

assert IMPORTER_API_VERSION == "28.3.14"
assert set(UNIVERSAL) == set(LEAGUES)
assert set(BY_SEASON) == set(LEAGUES)
assert sum(len(values) for values in UNIVERSAL.values()) >= 888

for code in LEAGUES:
    assert set(LATEST[code]).issubset(set(UNIVERSAL[code]))
    assert UNIVERSAL[code], code
    for canonical in UNIVERSAL[code]:
        resolved, score = resolve_team_in_league(
            canonical,
            code,
            UNIVERSAL,
            preferred_teams_by_code=LATEST,
            teams_by_season=BY_SEASON,
        )
        assert normalize_name(resolved) == normalize_name(canonical), (code, canonical, resolved, score)
        assert score >= 0.98, (code, canonical, score)

# Variações institucionais geradas para os nomes cujo núcleo é único na liga.
# Casos como Paris FC x Paris SG são deliberadamente excluídos desse teste
# sintético, porque o próprio sufixo é parte indispensável da identidade.
ORG = {"fc", "sc", "sg", "ec", "ac", "cf", "afc", "club", "clube", "fk", "sk", "if", "bk", "ff", "kv"}
for code, names in UNIVERSAL.items():
    core_groups: dict[str, list[str]] = {}
    for canonical in names:
        tokens = normalize_name(canonical).split()
        core = " ".join(token for token in tokens if token not in ORG)
        core_groups.setdefault(core.replace(" ", ""), []).append(canonical)
    for prefix in ("FC ", "SC "):
        for canonical in names:
            tokens = normalize_name(canonical).split()
            if any(token in ORG for token in tokens):
                continue
            core = "".join(tokens)
            if len(core_groups.get(core, [])) != 1:
                continue
            raw = prefix + canonical
            resolved, score = resolve_team_in_league(
                raw,
                code,
                UNIVERSAL,
                preferred_teams_by_code=LATEST,
                teams_by_season=BY_SEASON,
            )
            assert normalize_name(resolved).replace(" ", "") == normalize_name(canonical).replace(" ", ""), (code, raw, canonical, resolved, score)
            assert score >= 0.94, (code, raw, score)

# Uma amostra explícita por liga cobre nomes comerciais, siglas e denominações oficiais.
CASES = {
    "ARG": ("Argentinos Juniors", "Argentinos Jrs"),
    "BRA": ("CR Flamengo", "Flamengo RJ"),
    "USA": ("NYCFC", "New York City"),
    "MEX": ("Pumas UNAM", "UNAM Pumas"),
    "JPN": ("Jubilo Iwata", "Iwata"),
    "CHN": ("Shanghai Port FC", "Shanghai Port"),
    "SWE": ("IFK Goteborg", "Goteborg"),
    "NOR": ("FK Bodo Glimt", "Bodo/Glimt"),
    "FIN": ("Seinajoen JK", "SJK"),
    "IRL": ("University College Dublin", "UC Dublin"),
    "E0": ("Manchester City", "Man City"),
    "E1": ("Queens Park Rangers", "QPR"),
    "SP1": ("Atletico Madrid", "Ath Madrid"),
    "SP2": ("Real Zaragoza", "Zaragoza"),
    "I1": ("Internazionale", "Inter"),
    "I2": ("Hellas Verona", "Verona"),
    "D1": ("Bayern Munchen", "Bayern Munich"),
    "D2": ("Eintracht Braunschweig", "Braunschweig"),
    "F1": ("Paris Saint Germain", "Paris SG"),
    "P1": ("Sporting CP", "Sp Lisbon"),
    "N1": ("PSV", "PSV Eindhoven"),
    "B1": ("Union Saint Gilloise", "St. Gilloise"),
    "T1": ("Istanbul Basaksehir", "Buyuksehyr"),
    "G1": ("PAOK Thessaloniki", "PAOK"),
}
assert set(CASES) == set(LEAGUES)
for code, (raw, expected) in CASES.items():
    resolved, score = resolve_team_in_league(
        raw,
        code,
        UNIVERSAL,
        preferred_teams_by_code=LATEST,
        teams_by_season=BY_SEASON,
        match_date="2026-08-01",
    )
    assert resolved == expected, (code, raw, expected, resolved, score)
    assert score >= 0.72, (code, raw, score)

finland = infer_league_and_teams(
    "VPS Vaasa",
    "Ilves Tampere",
    teams_by_code=UNIVERSAL,
    leagues=LEAGUES,
    preferred_teams_by_code=LATEST,
    teams_by_season=BY_SEASON,
    match_date="2026-08-02",
)
assert finland["status"] == "RECONHECIDO", finland
assert finland["league_code"] == "FIN", finland
assert finland["home"] == "VPS" and finland["away"] == "Ilves", finland

print(
    "TESTE DO CATÁLOGO UNIVERSAL V28.3.14: OK — "
    f"{len(LEAGUES)} ligas e {sum(len(v) for v in UNIVERSAL.values())} vínculos liga/equipe."
)
