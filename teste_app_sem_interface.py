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
assert app.INTERFACE_VERSION == "V28.1.5.12"
assert app.EXPECTED_CORE_API == "28.1.2"
assert app.max_entries == 5

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

    app.LOCAL_PENDING_LOT_PATH = original_path
    app.google_configurado = original_google_configurado
    st.session_state.pop("tex_games", None)

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
assert catalog.iloc[0]["Versão da interface"] == "V28.1.5.12"
assert analysis.iloc[0]["Versão da interface"] == "V28.1.5.12"
summary_text = app.build_ai_summary(games, evaluations.sort_values(["MatchID", "StatusOrder"]).drop_duplicates("MatchID"), evaluations, diagnostics, matches)
for forbidden in ("AGUARDAR PREÇO", "PREÇO FORTE", "ELEGÍVEL PARA META", "RESERVA", "mínima de admissibilidade da meta", "equilíbrio individual"):
    assert forbidden not in summary_text, forbidden

print("TESTE DO APP SEM INTERFACE GRÁFICA V28.1.5.12: OK")
