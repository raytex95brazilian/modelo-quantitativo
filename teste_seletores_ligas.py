from pathlib import Path

from tex_operacional_core import latest_team_catalog
from tex_v25_core import LEAGUES, normalize_zip

ROOT = Path(__file__).resolve().parent
matches = normalize_zip(ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)
teams, seasons = latest_team_catalog(matches)

assert set(teams) == set(LEAGUES)
assert all(teams[code] for code in LEAGUES), "Todas as 24 ligas precisam ter equipes."

assert "Club America" in teams["MEX"]
assert "Tigres UANL" in teams["MEX"]
assert "Athletico-PR" not in teams["MEX"]
assert "Athletico-PR" in teams["BRA"]
assert "Club America" not in teams["BRA"]
assert teams["MEX"] != teams["BRA"]
assert seasons["MEX"] == 2026

source = (ROOT / "app.py").read_text(encoding="utf-8")
start = source.index('st.subheader("1. Adicionar partidas")')
end = source.index('st.subheader("2. Partidas do lote")', start)
selector_block = source[start:end]
assert "with st.form" not in selector_block, "Seletores dependentes não podem ficar em st.form."
assert 'teams_by_code.get(code, [])' in selector_block
assert 'key=f"home_{form_version}_{code}"' in selector_block
assert 'key=f"away_{form_version}_{code}_{home}"' in selector_block

print("TESTE DOS SELETORES DAS 24 LIGAS V28.1.5.2: OK")
