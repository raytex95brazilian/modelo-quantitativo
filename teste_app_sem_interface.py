from __future__ import annotations

from contextlib import nullcontext
from datetime import date, time
import importlib
import json
from pathlib import Path
import sys
import types

import pandas as pd


class SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class DummyElement:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __getattr__(self, name):
        if name in {"number_input"}:
            return lambda *args, **kwargs: kwargs.get("value", 0)
        if name == "date_input":
            return lambda *args, **kwargs: kwargs.get("value", date.today())
        if name == "time_input":
            return lambda *args, **kwargs: kwargs.get("value", time(0, 0))
        if name == "selectbox":
            return lambda label, options, **kwargs: list(options)[0] if options else None
        if name == "text_input":
            return lambda *args, **kwargs: kwargs.get("value", "")
        if name == "checkbox":
            return lambda *args, **kwargs: kwargs.get("value", False)
        if name in {"button", "form_submit_button"}:
            return lambda *args, **kwargs: False
        return lambda *args, **kwargs: None


class ColumnConfig:
    class ProgressColumn:
        def __init__(self, *args, **kwargs):
            pass

    class NumberColumn:
        def __init__(self, *args, **kwargs):
            pass

    class CheckboxColumn:
        def __init__(self, *args, **kwargs):
            pass

    class SelectboxColumn:
        def __init__(self, *args, **kwargs):
            pass

    class TextColumn:
        def __init__(self, *args, **kwargs):
            pass


def decorator_passthrough(*args, **kwargs):
    if args and callable(args[0]) and len(args) == 1 and not kwargs:
        return args[0]
    return lambda function: function


st = types.ModuleType("streamlit")
st.session_state = SessionState()
st.secrets = {}
st.sidebar = DummyElement()
st.column_config = ColumnConfig()
st.cache_data = decorator_passthrough
st.cache_resource = decorator_passthrough
st.set_page_config = lambda *args, **kwargs: None
st.stop = lambda: (_ for _ in ()).throw(RuntimeError("st.stop chamado"))
st.columns = lambda spec, *args, **kwargs: [DummyElement() for _ in range(spec if isinstance(spec, int) else len(spec))]
st.tabs = lambda labels, *args, **kwargs: [DummyElement() for _ in labels]
st.form = lambda *args, **kwargs: DummyElement()
st.container = lambda *args, **kwargs: DummyElement()
st.expander = lambda *args, **kwargs: DummyElement()
st.number_input = lambda *args, **kwargs: kwargs.get("value", 0)
st.date_input = lambda *args, **kwargs: kwargs.get("value", date.today())
st.time_input = lambda *args, **kwargs: kwargs.get("value", time(0, 0))
st.selectbox = lambda label, options, **kwargs: list(options)[0] if options else None
st.text_input = lambda *args, **kwargs: kwargs.get("value", "")
st.text_area = lambda *args, **kwargs: kwargs.get("value", "")
st.data_editor = lambda data, *args, **kwargs: data
st.checkbox = lambda *args, **kwargs: kwargs.get("value", False)
st.button = lambda *args, **kwargs: False
st.form_submit_button = lambda *args, **kwargs: False
for name in (
    "error", "code", "info", "markdown", "subheader", "caption", "success",
    "warning", "dataframe", "metric", "link_button", "download_button", "write",
    "divider", "header", "rerun",
):
    setattr(st, name, lambda *args, **kwargs: None)
sys.modules["streamlit"] = st

# Impede tentativa de rede durante a importação; o app usa a base local.
update_stub = types.ModuleType("tex_v25_atualizacao")
sys.modules["tex_v25_atualizacao"] = update_stub

app = importlib.import_module("app")
assert app.INTERFACE_VERSION == "V28.3.17"
assert app.EXPECTED_CORE_API == "28.1.2"
assert app.max_entries == 0

# O topo do resultado deve listar todos os aprovados, inclusive os sem aposta simples.
summary_games = [
    {
        "ID": "g1", "Data": "2026-08-08", "Hora": "16:00",
        "Liga": "Brasileirão Série A", "Mandante": "Gremio", "Visitante": "Sao Paulo",
    },
    {
        "ID": "g2", "Data": "2026-08-08", "Hora": "18:30",
        "Liga": "Brasileirão Série A", "Mandante": "Remo", "Visitante": "Atletico-MG",
    },
    {
        "ID": "g3", "Data": "2026-08-08", "Hora": "20:30",
        "Liga": "Brasileirão Série A", "Mandante": "Coritiba", "Visitante": "Chapecoense-SC",
    },
]
summary_filters = pd.DataFrame([
    {"InputID": "g1", "Filter2018Approved": True},
    {"InputID": "g2", "Filter2018Approved": False},
    {"InputID": "g3", "Filter2018Approved": True},
])
summary_readings = pd.DataFrame([
    {
        "InputID": "g1", "Status": "OPERAR", "MarketName": "Ambas marcam",
        "Selection": "Ambas marcam — Sim", "ConservativeProbability": 0.57,
        "Odd": 1.90, "ConservativeExpectedValue": 0.061,
    },
    {
        "InputID": "g3", "Status": "SEM VALOR AO PREÇO ATUAL", "MarketName": "Mais de 2,5",
        "Selection": "Mais de 2,5", "ConservativeProbability": 0.61,
        "Odd": 1.55, "ConservativeExpectedValue": -0.073,
    },
])
summary = app.approved_games_summary_table(summary_games, summary_filters, summary_readings)
assert list(summary["Nº"]) == [1, 3]
assert list(summary["Partida"]) == ["Gremio x Sao Paulo", "Coritiba x Chapecoense-SC"]
assert list(summary["Resultado da análise"]) == ["OPERAR", "SEM VALOR AO PREÇO ATUAL"]
assert abs(float(summary.iloc[0]["Probabilidade final"]) - 57.0) < 1e-9
assert abs(float(summary.iloc[0]["Cotação justa"]) - (1.0 / 0.57)) < 1e-9

report_evaluations = summary_readings.copy()
report_evaluations["Filter2018Approved"] = True
report_evaluations["Filter2018Status"] = "APROVADO"
report_evaluations["Filter2018Summary"] = "Todas as regras foram atendidas."
report_evaluations["IncludedInMultiple"] = False
report_evaluations["Home"] = ["Gremio", "Coritiba"]
report_evaluations["Away"] = ["Sao Paulo", "Chapecoense-SC"]
report_evaluations["EffectiveOdd"] = report_evaluations["Odd"] * 0.98
report_evaluations["DecisionProbability"] = report_evaluations["ConservativeProbability"]
report_evaluations["MarketProbability"] = report_evaluations["ConservativeProbability"]
report_evaluations["RawSportsProbability"] = report_evaluations["ConservativeProbability"]
report_evaluations["ProfileSample"] = [0, 100]
report_evaluations["EmpiricalHitRate"] = report_evaluations["ConservativeProbability"]
report_evaluations["SampleConfidence"] = ["NÃO VALIDADA", "MODERADA"]
report_evaluations["Reliability"] = [0.0, 0.8]
report_evaluations["Reason"] = ["Cotação favorável.", "Sem valor ao preço atual."]
report_text = app.build_ai_summary(
    pd.DataFrame(summary_games), summary_readings, report_evaluations, pd.DataFrame(), []
)
assert "RESUMO DOS JOGOS APROVADOS" in report_text
assert "não existe meta mínima" in report_text.lower()
assert "complementos até o piso rígido" not in report_text
assert "meta de cinco seleções" not in report_text
assert "Ambas marcam é um mercado elegível" in report_text
assert "Gremio x Sao Paulo" in report_text

# O lote deve sobreviver à perda completa do session_state usando o backup automático.
from tempfile import TemporaryDirectory
with TemporaryDirectory() as temp_dir:
    original_path = app.LOCAL_PENDING_LOT_PATH
    original_google_configurado = app.google_configurado
    app.LOCAL_PENDING_LOT_PATH = Path(temp_dir) / "lote.json"
    app.google_configurado = lambda secrets: False
    sample_lot = [{
        "ID": "persist-1",
        "Data": "2026-08-01",
        "Hora": "18:00",
        "Código da liga": "MEX",
        "Liga": "México - Liga MX",
        "Mandante": "Club America",
        "Visitante": "Tigres UANL",
        "Casa de apostas": "PIXBET",
    }]
    app._save_local_pending_lot(sample_lot)
    st.session_state.pop("tex_games", None)
    assert app.games() == sample_lot
    app._persist_snapshot_best_effort("teste automatizado")
    st.session_state.pop("tex_games", None)
    assert app.games() == sample_lot

    remote_calls = []
    app.google_configurado = lambda secrets: True
    app.registrar_evento_lote = lambda secrets, tipo_evento, jogo=None, interface_version="": remote_calls.append((tipo_evento, dict(jogo or {}))) or {
        "Registrado em": "2026-07-27T20:00:00-03:00",
        "Verificação": "GRAVADO E RELIDO",
        "Aba": "entrada_jogos",
        "Linha": 2,
        "ID Evento": "evento-teste",
        "Cotações verificadas": {},
    }
    app.salvar_lote_pendente = lambda secrets, jogos, interface_version="": {
        "Salvo em": "2026-07-27T20:00:00-03:00"
    }
    app.criar_registros_cotacoes_digitadas = lambda *args, **kwargs: []
    app.salvar_cotacoes = lambda secrets, registros: len(list(registros))
    st.session_state.tex_games = []
    app.upsert_game(sample_lot[0], 1000.0)
    assert remote_calls and remote_calls[-1][0] == "UPSERT" and remote_calls[-1][1]["Mandante"] == "Club America"

    # A nova importação 1X2 em lote não pode apagar mercados complementares existentes.
    existing = dict(sample_lot[0])
    existing.update({
        "Odd mandante": 1.90,
        "Odd empate": 3.20,
        "Odd visitante": 4.00,
        "Odd mais de 2,5": 1.85,
        "Odd menos de 2,5": 1.95,
        "Odd ambas marcam — Sim": 1.80,
        "Odd ambas marcam — Não": 2.00,
    })
    st.session_state.tex_games = [existing]
    app.registrar_eventos_lote = lambda secrets, jogos, interface_version="", substituir_lote=False: {
        "Eventos confirmados": len(list(jogos)),
        "Primeira linha": 2,
        "Última linha": 2,
        "Aba": "entrada_jogos",
        "Verificação": "GRAVADO E RELIDO EM LOTE",
    }
    app.criar_registros_cotacoes_digitadas = lambda jogo, **kwargs: [{"ID Coleta": jogo["ID"]}]
    app.salvar_cotacoes = lambda secrets, registros: len(list(registros))
    imported = dict(existing)
    imported.update({
        "Odd mandante": 2.05,
        "Odd empate": 3.10,
        "Odd visitante": 3.55,
        "Odd mais de 2,5": None,
        "Odd menos de 2,5": None,
        "Odd ambas marcam — Sim": None,
        "Odd ambas marcam — Não": None,
    })
    app.upsert_games_batch([imported], 1000.0)
    merged = st.session_state.tex_games[0]
    assert merged["Odd mandante"] == 2.05
    assert merged["Odd mais de 2,5"] == 1.85
    assert merged["Odd ambas marcam — Sim"] == 1.80

    app.LOCAL_PENDING_LOT_PATH = original_path
    app.google_configurado = original_google_configurado
    st.session_state.pop("tex_games", None)


# Uma nova importação deve substituir somente o lote ativo quando essa opção for escolhida.
original_google = app.google_configurado
original_register_batch = app.registrar_eventos_lote
original_create_records = app.criar_registros_cotacoes_digitadas
original_save_odds = app.salvar_cotacoes
original_persist = app._persist_snapshot_best_effort
try:
    app.google_configurado = lambda secrets: True
    calls = []
    app.registrar_eventos_lote = lambda secrets, jogos, interface_version="", substituir_lote=False: calls.append(bool(substituir_lote)) or {
        "Eventos confirmados": len(list(jogos)) + (1 if substituir_lote else 0),
        "Primeira linha": 2,
        "Última linha": 3,
        "Aba": "entrada_jogos",
        "Verificação": "GRAVADO E RELIDO EM LOTE",
    }
    app.criar_registros_cotacoes_digitadas = lambda jogo, **kwargs: [{"ID Coleta": jogo["ID"]}]
    app.salvar_cotacoes = lambda secrets, registros: len(list(registros))
    app._persist_snapshot_best_effort = lambda reason: None
    brazil = {
        "ID": "bra-1", "Data": "2026-08-08", "Hora": "16:00",
        "Código da liga": "BRA", "Liga": "Brasileirão Série A",
        "Mandante": "Gremio", "Visitante": "Sao Paulo",
        "Casa de apostas": "PIXBET", "Odd mandante": 2.32,
        "Odd empate": 3.09, "Odd visitante": 2.92,
        "Odd mais de 2,5": 2.03, "Odd menos de 2,5": 1.65,
        "Odd ambas marcam — Sim": None, "Odd ambas marcam — Não": None,
    }
    mexico = {
        "ID": "mex-1", "Data": "2026-08-15", "Hora": "20:00",
        "Código da liga": "MEX", "Liga": "México - Liga MX",
        "Mandante": "Atlante", "Visitante": "Toluca",
        "Casa de apostas": "PIXBET", "Odd mandante": 5.10,
        "Odd empate": 3.62, "Odd visitante": 1.48,
        "Odd mais de 2,5": None, "Odd menos de 2,5": None,
        "Odd ambas marcam — Sim": None, "Odd ambas marcam — Não": None,
    }
    st.session_state.tex_games = [brazil]
    result_replace = app.upsert_games_batch([mexico], 1000.0, replace_current_lot=True)
    assert calls[-1] is True
    assert result_replace["substituiu_lote"] is True
    assert [item["Código da liga"] for item in st.session_state.tex_games] == ["MEX"]

    st.session_state.tex_games = [brazil]
    result_append = app.upsert_games_batch([mexico], 1000.0, replace_current_lot=False)
    assert calls[-1] is False
    assert result_append["substituiu_lote"] is False
    assert {item["Código da liga"] for item in st.session_state.tex_games} == {"BRA", "MEX"}
finally:
    app.google_configurado = original_google
    app.registrar_eventos_lote = original_register_batch
    app.criar_registros_cotacoes_digitadas = original_create_records
    app.salvar_cotacoes = original_save_odds
    app._persist_snapshot_best_effort = original_persist
    st.session_state.pop("tex_games", None)


# A tabela de apostas individuais deve identificar inequivocamente o confronto.
sample_entry = pd.DataFrame([{
    "Status": "OPERAR",
    "Home": "Grêmio",
    "Away": "São Paulo",
    "League": "Brasileirão Série A",
    "DateParsed": "2026-08-08",
    "Time": "16:00",
    "MarketName": "Ambas marcam",
    "Selection": "Ambas marcam — Sim",
    "Odd": 4.90,
    "ConservativeProbability": 0.29,
    "RequiredOddForOperation": 3.52,
    "ConservativeExpectedValue": 0.392,
    "OperationalDecision": "COTAÇÃO FAVORÁVEL",
    "Reason": "Teste",
}])
identified = app.evaluation_table(sample_entry)
assert list(identified.columns[:5]) == ["Situação", "Partida", "Liga", "Data", "Hora"]
assert identified.iloc[0]["Partida"] == "Grêmio x São Paulo"
assert identified.iloc[0]["Liga"] == "Brasileirão Série A"
assert identified.iloc[0]["Data"] == "08/08/2026"
assert identified.iloc[0]["Hora"] == "16:00"

# A forma recente deve ser legível e compacta.
assert "form-v" in app._form_badges([{"Result": "V", "Date": "01/08/2026", "Venue": "Casa", "Opponent": "Teste", "Score": "2 x 0"}])
assert list(app._form_table([{"Date": "01/08/2026", "VenueShort": "C", "Opponent": "Teste", "Score": "2 x 0", "Result": "V"}]).columns) == ["Data", "Local", "Adversário", "Placar", "R"]

from tex_v25_core import normalize_zip
from tex_v28_core_2812 import INPUT_COLUMNS, analyze_games, load_v28_model

root = Path(__file__).resolve().parent
matches = normalize_zip(root / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)
model = load_v28_model(root / "model")
row = {
    "ID": "teste-app",
    "Data": "2026-08-01",
    "Hora": "18:00",
    "Código da liga": "BRA",
    "Liga": "Brasileirão Série A",
    "Mandante": "Santos",
    "Visitante": "Chapecoense-SC",
    "Casa de apostas": "Pixbet",
    "Odd mandante": 1.40,
    "Odd empate": 4.55,
    "Odd visitante": 7.30,
    "Odd mais de 2,5": 1.66,
    "Odd menos de 2,5": 2.14,
    "Odd ambas marcam — Sim": 1.87,
    "Odd ambas marcam — Não": 1.89,
}
games = pd.DataFrame([row], columns=INPUT_COLUMNS)
_, _, evaluations, diagnostics = analyze_games(games, matches, model, 1000.0, 0.01, 5)
assert diagnostics.iloc[0]["Situação"] == "ANALISADO"

catalog = pd.DataFrame(app.make_catalog_records(evaluations, 1000.0))
analysis = pd.DataFrame(app.make_analysis_records(evaluations, 0.01))
assert not catalog.empty and not analysis.empty
line = evaluations[evaluations["Market"].eq("1X2")]
expected_margin = float(line.iloc[0]["MarketMargin"] * 100.0)
assert catalog[catalog["Grupo do mercado"].eq("1X2")]["Margem do mercado %"].nunique() == 1
assert abs(float(catalog[catalog["Grupo do mercado"].eq("1X2")].iloc[0]["Margem do mercado %"]) - expected_margin) < 1e-12
config = json.loads(str(analysis.iloc[0]["Configuração JSON"]))
assert config["api_nucleo"] == "28.1.2"
assert config["percentual_unidade"] == 0.01
assert catalog.iloc[0]["Versão da interface"] == "V28.3.17"
assert analysis.iloc[0]["Versão da interface"] == "V28.3.17"
summary_text = app.build_ai_summary(games, evaluations.sort_values(["MatchID", "StatusOrder"]).drop_duplicates("MatchID"), evaluations, diagnostics, matches)
for forbidden in ("AGUARDAR PREÇO", "PREÇO FORTE", "ELEGÍVEL PARA META", "RESERVA", "mínima de admissibilidade da meta", "equilíbrio individual"):
    assert forbidden not in summary_text, forbidden

print("TESTE DO APP SEM INTERFACE GRÁFICA V28.3.17: OK")
