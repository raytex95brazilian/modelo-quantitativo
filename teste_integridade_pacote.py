from __future__ import annotations

import ast
import gzip
import json
from pathlib import Path
import py_compile
import zipfile

import tex_v25_storage as storage
import tex_v28_core_2812 as core
from tex_v28_finance import COLUNAS_APOSTAS

ROOT = Path(__file__).resolve().parent
EXPECTED_FILES = [
    "app.py",
    "tex_v28_core_2812.py",
    "tex_v28_core.py",
    "tex_v28_finance.py",
    "tex_operacional_core.py",
    "tex_v25_core.py",
    "tex_v25_storage.py",
    "tex_v25_atualizacao.py",
    "requirements.txt",
    "runtime.txt",
    "data/TEX_V22_DADOS_24_LIGAS.zip",
    "model/metadata.json",
    "model/reliability_profiles.csv",
    "model/tex_v28_lgbm.json",
    "backtest/V28_OOS_PREDICTIONS.csv.gz",
    "backtest/V28_1_5_FILTRO_CONSERVADOR_RESUMO.json",
]
missing = [name for name in EXPECTED_FILES if not (ROOT / name).is_file()]
assert not missing, f"Arquivos obrigatórios ausentes: {missing}"

for path in ROOT.glob("*.py"):
    py_compile.compile(str(path), doraise=True)

app_source = (ROOT / "app.py").read_text(encoding="utf-8")
ast.parse(app_source)
assert "import tex_v28_core_2812 as _v28" in app_source
assert "import tex_v28_core as _v28" not in app_source
assert 'EXPECTED_CORE_API = "28.1.2"' in app_source
assert 'INTERFACE_VERSION = "V28.1.5"' in app_source
assert 'value=5, step=1' in app_source
for forbidden in (
    "ODDS_VALIDITY_MINUTES",
    "FINANCE_API_VERSION",
    "Cotação capturada em",
    "Validade da cotação",
    "CLV",
    "BEGIN PRIVATE KEY",
):
    assert forbidden not in app_source, forbidden

metadata = json.loads((ROOT / "model" / "metadata.json").read_text(encoding="utf-8"))
assert metadata["model_version"] == "V28.0"
assert metadata["validated_markets"] == ["1X2", "OU25"]
assert metadata["experimental_markets"] == ["BTTS"]
assert core.CORE_API_VERSION == "28.1.2"
assert core.V28_CFG.max_entries == 5

for name, columns in {
    "cotações": storage.COLUNAS_COTACOES,
    "análises": storage.COLUNAS_ANALISES,
    "apostas": COLUNAS_APOSTAS,
}.items():
    assert len(columns) == len(set(columns)), f"Colunas duplicadas em {name}"

with zipfile.ZipFile(ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip") as archive:
    assert archive.testzip() is None
    assert archive.namelist(), "Base histórica vazia"

with gzip.open(ROOT / "backtest" / "V28_OOS_PREDICTIONS.csv.gz", "rb") as handle:
    assert handle.read(64), "Arquivo retrospectivo compactado vazio"

summary = json.loads(
    (ROOT / "backtest" / "V28_1_5_FILTRO_CONSERVADOR_RESUMO.json").read_text(encoding="utf-8")
)
assert summary["entries"] > 0
assert 0.0 < summary["average_entries_per_week"] <= 5.0
assert "não é um novo teste final independente" in summary["advertencia"]

for path in ROOT.rglob("*"):
    if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts and path.stat().st_size < 5_000_000:
        content = path.read_bytes()
        if path.name != Path(__file__).name:
            assert b"-----BEGIN PRIVATE KEY-----" not in content, path

print("TESTE DE INTEGRIDADE DO PACOTE V28.1.5: OK")
