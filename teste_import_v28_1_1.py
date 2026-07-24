from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parent
for filename in (
    'app.py', 'tex_v28_core.py', 'tex_operacional_core.py',
    'tex_v25_core.py', 'tex_v25_storage.py', 'tex_v25_atualizacao.py',
):
    py_compile.compile(str(ROOT / filename), doraise=True)

import tex_v28_core as v28
import tex_operacional_core as operacional

assert v28.CORE_API_VERSION == '28.1.1'
for name in ('analyze_games', 'build_ai_summary', 'display_frame', 'load_v28_model', 'lot_fingerprint', 'validate_market_odds'):
    assert hasattr(v28, name), name
for name in ('INPUT_COLUMNS', 'enrich_with_standings', 'latest_team_catalog', 'parse_odd', 'standings_context'):
    assert hasattr(operacional, name), name
print('TESTE DE IMPORTAÇÃO V28.1.1: OK')
