from pathlib import Path

ROOT = Path(__file__).resolve().parent
source = (ROOT / "app.py").read_text(encoding="utf-8")
requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

start = source.index('st.subheader("1. Adicionar partidas")')
end = source.index('st.subheader("2. Partidas do lote")', start)
entry = source[start:end]

# Uma única etapa visual: não existe confirmação intermediária.
assert "Partida e cotações — etapa única" in entry
assert "Etapa 1 de 2" not in entry
assert "Etapa 2 de 2" not in entry
assert "CONFIRMAR CONFRONTO" not in entry
assert "ALTERAR CONFRONTO" not in entry

# Liga e equipes ficam em fragmento independente; os demais campos ficam em formulário.
assert "@_fragment\ndef render_match_selectors" in entry
assert 'with st.form(f"game_form_{form_version}"' in entry
assert 'submitted = st.form_submit_button(' in entry
selector_end = entry.index('def render_game_entry()')
selector_part = entry[:selector_end]
assert 'key=f"entry_league_{form_version}"' in selector_part
assert 'key=f"entry_home_{form_version}_{code}"' in selector_part
assert 'key=f"entry_away_{form_version}_{code}_{home or \'empty\'}"' in selector_part
assert 'index=None' in selector_part

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

# Todos os campos de entrada manual começam vazios.
assert 'game_date = row_top[0].date_input(\n                "Data",\n                value=None,' in form_body
assert 'game_time = row_top[1].time_input(\n                "Horário",\n                value=None,' in form_body
assert 'bookmaker = row_top[2].text_input(\n                "Casa de apostas",\n                value="PIXBET",' in form_body
assert form_body.count('value=None,') >= 9  # data, horário e sete cotações
assert 'value="PIXBET"' in form_body
assert 'value=0.0' not in form_body

# A análise para IA aparece na própria tela e o download é opcional.
assert 'st.markdown("### Análise para IA")' in source
assert 'st.code(ai_summary, language=None, wrap_lines=True)' in source
assert 'não é necessário baixar arquivo' in source
assert 'BAIXAR ANÁLISE PARA IA — OPCIONAL' in source

sidebar_start = source.index('with st.sidebar:')
sidebar_end = source.index('st.markdown(', sidebar_start)
sidebar = source[sidebar_start:sidebar_end]
assert 'with st.form("tex_operational_config_form"' not in sidebar
assert 'APLICAR CONFIGURAÇÃO' not in sidebar
assert 'on_change=_apply_operational_config_automatically' in sidebar

assert 'streamlit>=1.37,<2.0' in requirements
assert 'st.tabs(["Cadastro manual", "Colar jogos e cotações 1X2"])' in entry
assert 'INTERPRETAR E PREENCHER AUTOMATICAMENTE' in entry
assert 'SALVAR TODAS AS COTAÇÕES COMPLEMENTARES' in source
print("TESTE DE USABILIDADE E ESTABILIDADE V28.3.0: OK")
