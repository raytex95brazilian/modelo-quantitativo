from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pandas as pd

# Reutiliza o ambiente Streamlit simulado pelo teste principal.
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import teste_app_sem_interface as base  # noqa: E402

app = importlib.import_module("app")

metrics: list[tuple[str, str]] = []
captions: list[str] = []
markdowns: list[str] = []

class MetricColumn:
    def metric(self, label, value, *args, **kwargs):
        metrics.append((str(label), str(value)))

old_columns = app.st.columns
old_caption = app.st.caption
old_markdown = app.st.markdown
try:
    app.st.columns = lambda count, *args, **kwargs: [MetricColumn() for _ in range(count)]
    app.st.caption = lambda text, *args, **kwargs: captions.append(str(text))
    app.st.markdown = lambda text, *args, **kwargs: markdowns.append(str(text))
    app.render_expected_goals(
        pd.Series({"LambdaHome": 1.42, "LambdaAway": 1.08}),
        home="Grêmio",
        away="São Paulo",
    )
finally:
    app.st.columns = old_columns
    app.st.caption = old_caption
    app.st.markdown = old_markdown

assert metrics == [
    ("Gols esperados — Grêmio", "1.42"),
    ("Gols esperados — São Paulo", "1.08"),
    ("Gols esperados — total", "2.50"),
]
assert any("Projeção de gols do modelo" in item for item in markdowns)
assert any("não correspondem a uma previsão de placar exato" in item for item in captions)

print("TESTE DE GOLS ESPERADOS V28.3.4: OK")
