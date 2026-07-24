from __future__ import annotations

from datetime import date, time
from pathlib import Path
import runpy
import sys
import types

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


class SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class UIBlock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def number_input(self, _label, **kwargs):
        return kwargs.get("value", kwargs.get("min_value", 0))

    def date_input(self, _label, **kwargs):
        return kwargs.get("value", date.today())

    def time_input(self, _label, **kwargs):
        return kwargs.get("value", time(0, 0))

    def selectbox(self, _label, options, **_kwargs):
        values = list(options)
        return values[0] if values else None

    def text_input(self, _label, **kwargs):
        return kwargs.get("value", "")

    def checkbox(self, _label, **kwargs):
        return kwargs.get("value", False)

    def button(self, *_args, **_kwargs):
        return False

    def form_submit_button(self, *_args, **_kwargs):
        return False

    def columns(self, spec):
        size = spec if isinstance(spec, int) else len(spec)
        return [UIBlock() for _ in range(size)]

    def tabs(self, labels):
        return [UIBlock() for _ in labels]

    def form(self, *_args, **_kwargs):
        return UIBlock()

    def container(self, *_args, **_kwargs):
        return UIBlock()

    def expander(self, *_args, **_kwargs):
        return UIBlock()

    def __getattr__(self, _name):
        def method(*_args, **_kwargs):
            return None
        return method


class CacheDecorator:
    def __call__(self, *args, **kwargs):
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]
        def decorate(function):
            return function
        return decorate

    def clear(self):
        return None


st = types.ModuleType("streamlit")
st.session_state = SessionState()
st.secrets = {}
st.sidebar = UIBlock()
st.cache_resource = CacheDecorator()
st.cache_data = CacheDecorator()
st.column_config = types.SimpleNamespace(
    ProgressColumn=lambda *a, **k: None,
    NumberColumn=lambda *a, **k: None,
)
_ui = UIBlock()
for name in [
    "set_page_config", "markdown", "error", "info", "success", "warning", "code", "caption",
    "subheader", "header", "divider", "dataframe", "link_button", "download_button",
    "metric", "write", "stop", "rerun",
]:
    setattr(st, name, getattr(_ui, name))
for name in [
    "number_input", "date_input", "time_input", "selectbox", "text_input", "checkbox", "button",
    "form_submit_button", "columns", "tabs", "form", "container", "expander",
]:
    setattr(st, name, getattr(_ui, name))
sys.modules["streamlit"] = st

v25 = types.ModuleType("tex_v25_core")
v25.LEAGUES = {"BRA1": "Brasil — Série A"}
v25.normalize_zip = lambda *_args, **_kwargs: []
sys.modules["tex_v25_core"] = v25

storage = types.ModuleType("tex_v25_storage")
storage.COLUNAS_ANALISES = ["Amostra casa", "Amostra fora", "Amostra histórica", "Retorno histórico %"]
storage.COLUNAS_COTACOES = []
storage.google_configurado = lambda *_args, **_kwargs: False
storage.salvar_analises = lambda *_args, **_kwargs: 0
storage.salvar_cotacoes = lambda *_args, **_kwargs: 0
storage.url_planilha_configurada = lambda *_args, **_kwargs: "https://example.invalid"
sys.modules["tex_v25_storage"] = storage

operational = types.ModuleType("tex_operacional_core")
operational.INPUT_COLUMNS = [
    "ID", "Data", "Hora", "Código da liga", "Liga", "Mandante", "Visitante", "Casa de apostas",
    "Odd mandante", "Odd empate", "Odd visitante", "Odd mais de 2,5", "Odd menos de 2,5",
    "Odd ambas marcam — Sim", "Odd ambas marcam — Não",
]
operational.enrich_with_standings = lambda frame, *_args, **_kwargs: frame
operational.latest_team_catalog = lambda _rows: ({"BRA1": ["Time A", "Time B"]}, {"BRA1": 2026})
operational.parse_odd = lambda value: float(value) if value not in (None, "") else None
operational.standings_context = lambda *_args, **_kwargs: {"Available": False, "Season": 2026}
sys.modules["tex_operacional_core"] = operational

core = types.ModuleType("tex_v28_core_2814")
core.APP_NAME = "Tex Statistics V28.1.4 — Análise Ampliada"
core.CORE_API_VERSION = "28.1.4"
core.analyze_games = lambda *_args, **_kwargs: (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
core.build_ai_summary = lambda *_args, **_kwargs: ""
core.display_frame = lambda frame: frame
core.load_v28_model = lambda *_args, **_kwargs: object()
core.lot_fingerprint = lambda frame: "empty" if frame.empty else "filled"
core.validate_market_odds = lambda *_args, **_kwargs: 1.05
sys.modules["tex_v28_core_2814"] = core

sys.modules.pop("tex_v25_atualizacao", None)

runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
print("V28.1.4: app.py percorreu o fluxo inicial sem erro de nome ou atributo.")
