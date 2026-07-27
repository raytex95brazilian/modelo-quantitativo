from __future__ import annotations

import ast
import gzip
import hashlib
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
    "backtest/V28_1_5_7_META_5_RESUMO.json",
]
missing = [name for name in EXPECTED_FILES if not (ROOT / name).is_file()]
assert not missing, f"Arquivos obrigatórios ausentes: {missing}"

for path in ROOT.glob("*.py"):
    py_compile.compile(str(path), doraise=True)

app_source = (ROOT / "app.py").read_text(encoding="utf-8")
core_source = (ROOT / "tex_v28_core_2812.py").read_text(encoding="utf-8")
ast.parse(app_source)
ast.parse(core_source)
assert '_v28 = _load_required_module("tex_v28_core_2812")' in app_source
assert "import tex_v28_core as _v28" not in app_source
assert 'EXPECTED_CORE_API = "28.1.2"' in app_source
assert 'INTERFACE_VERSION = "V28.1.5.11"' in app_source
assert 'Partida e cotações — etapa única' in app_source
assert 'CONFIRMAR CONFRONTO' not in app_source
assert 'Etapa 1 de 2' not in app_source
assert 'value="PIXBET"' in app_source
assert '\n                value=0.0,' not in app_source
assert 'st.markdown("### Análise para IA")' in app_source
assert 'st.code(ai_summary, language=None, wrap_lines=True)' in app_source
assert '@_fragment' in app_source
assert 'with st.form("tex_operational_config_form"' in app_source
assert 'with st.form(f"game_form_{form_version}"' in app_source
assert '"weekly_target": 5' in app_source
assert 'salvar_lote_pendente' in app_source
assert 'carregar_lote_pendente' in app_source
assert 'registrar_evento_lote' in app_source
assert '_registrar_evento_obrigatorio("UPSERT", candidate)' in app_source
assert '_confirmar_lote_remoto_antes_da_analise()' in app_source
assert 'diagnostico_google' in app_source
assert 'GRAVADO E RELIDO' in app_source
assert 'Abrir exatamente a planilha de gravação' in app_source
assert 'REPETIR SALVAMENTO NA PLANILHA' in app_source
assert 'APAGAR TODO O LOTE' in app_source
assert 'BAIXAR BACKUP DO LOTE' in app_source
for forbidden in (
    "ODDS_VALIDITY_MINUTES",
    "Cotação capturada em",
    "Validade da cotação",
    "CLV",
    "BEGIN PRIVATE KEY",
    "AGUARDAR PREÇO",
    "PREÇO FORTE",
    "ELEGÍVEL PARA META",
    "RESERVA",
    "Cotação mínima de admissibilidade da meta",
    "Cotação de equilíbrio individual",
):
    assert forbidden not in app_source, forbidden
    assert forbidden not in core_source, forbidden

metadata = json.loads((ROOT / "model" / "metadata.json").read_text(encoding="utf-8"))
assert metadata["model_version"] == "V28.0"
assert metadata["validated_markets"] == ["1X2", "OU25"]
assert metadata["experimental_markets"] == ["BTTS"]
assert core.CORE_API_VERSION == "28.1.2"
assert core.V28_CFG.max_entries == 5
assert core.V28_CFG.strong_price_ev == 0.0
assert core.V28_CFG.fallback_min_ev == -0.15
assert storage.STORAGE_API_VERSION == "28.1.5.11"
assert "Lote JSON" in storage.COLUNAS_LOTE_PENDENTE
assert "ID Evento" in storage.COLUNAS_EVENTOS_LOTE
assert "Tipo de evento" in storage.COLUNAS_EVENTOS_LOTE

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
    (ROOT / "backtest" / "V28_1_5_7_META_5_RESUMO.json").read_text(encoding="utf-8")
)
assert summary["entries"] > 0
assert 4.9 < summary["average_entries_per_week"] <= 5.0
assert summary["weeks_with_target"] >= 224
assert summary["target_per_week"] == 5
assert summary["portfolio_floor"] == 0.0
assert summary["fallback_floor"] == -0.15
assert "Recalculo operacional retrospectivo" in summary["advertencia"]

for path in ROOT.rglob("*"):
    if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts and path.stat().st_size < 5_000_000:
        content = path.read_bytes()
        if path.name != Path(__file__).name:
            assert b"-----BEGIN PRIVATE KEY-----" not in content, path

manifest_path = ROOT / "MANIFESTO_SHA256.txt"
manifest_entries = {}
for line in manifest_path.read_text(encoding="utf-8").splitlines():
    digest, relative = line.split("  ", 1)
    manifest_entries[relative] = digest

distributed_files = {
    path.relative_to(ROOT).as_posix(): path
    for path in ROOT.rglob("*")
    if path.is_file()
    and path.name != "MANIFESTO_SHA256.txt"
    and path.suffix != ".pyc"
    and "__pycache__" not in path.parts
}
assert set(manifest_entries) == set(distributed_files), (
    "Manifesto não corresponde aos arquivos distribuídos: "
    f"faltando={sorted(set(distributed_files) - set(manifest_entries))}, "
    f"extras={sorted(set(manifest_entries) - set(distributed_files))}"
)
for relative, path in distributed_files.items():
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert manifest_entries[relative] == digest, f"SHA-256 divergente: {relative}"

print("TESTE DE INTEGRIDADE DO PACOTE V28.1.5.11: OK")
