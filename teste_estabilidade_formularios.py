from pathlib import Path

ROOT = Path(__file__).resolve().parent
source = (ROOT / "app.py").read_text(encoding="utf-8")
requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

start = source.index('st.subheader("1. Adicionar partidas")')
end = source.index('st.subheader("2. Partidas do lote")', start)
entry = source[start:end]

assert "@_fragment" in entry
assert 'draft_key = "tex_confirmed_match"' in entry
assert 'CONFIRMAR CONFRONTO E INFORMAR COTAÇÕES' in entry
assert 'ALTERAR CONFRONTO' in entry
assert 'with st.form(f"game_form_{form_version}"' in entry
assert 'submitted = st.form_submit_button(' in entry

form_start = entry.index('with st.form(f"game_form_{form_version}"')
form_end = entry.index('if not submitted:', form_start)
form_body = entry[form_start:form_end]
for field in (
    'date_input(', 'time_input(', 'text_input(',
    'key=f"odd_h_{form_version}"', 'key=f"odd_d_{form_version}"',
    'key=f"odd_a_{form_version}"', 'key=f"odd_o_{form_version}"',
    'key=f"odd_u_{form_version}"', 'key=f"odd_by_{form_version}"',
    'key=f"odd_bn_{form_version}"',
):
    assert field in form_body, f"Campo fora do formulário estável: {field}"

selector_part = entry[:form_start]
assert 'key=f"draft_league_{form_version}"' in selector_part
assert 'key=f"draft_home_{form_version}_{code}"' in selector_part
assert 'key=f"draft_away_{form_version}_{code}_{home}"' in selector_part

sidebar_start = source.index('with st.sidebar:')
sidebar_end = source.index('st.markdown(', sidebar_start)
sidebar = source[sidebar_start:sidebar_end]
assert 'with st.form("tex_operational_config_form"' in sidebar
assert 'APLICAR CONFIGURAÇÃO' in sidebar

assert 'streamlit>=1.37,<2.0' in requirements
print("TESTE DE ESTABILIDADE DOS FORMULÁRIOS V28.1.5.4: OK")
