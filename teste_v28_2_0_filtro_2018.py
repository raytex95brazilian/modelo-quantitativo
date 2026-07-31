from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd

from tex_filtro_2018 import HistoryIndex, evaluate_lot_2018
from tex_operacao_filtrada import attach_filter_results, build_operational_outputs
from tex_v25_core import normalize_zip

ROOT = Path(__file__).resolve().parent

# 1) Caso real já identificado na base: todas as quatro regras devem ser aprovadas.
matches = normalize_zip(ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)
game = pd.DataFrame([{
    "ID": "caso-aprovado",
    "Data": "2025-02-15",
    "Código da liga": "ARG",
    "Liga": "Argentina - Primera Division",
    "Mandante": "Defensa y Justicia",
    "Visitante": "Barracas Central",
}])
result = evaluate_lot_2018(game, matches).iloc[0]
assert bool(result["Filter2018Approved"])
assert result["Filter2018Status"] == "APROVADO"
for field in (
    "Filter2018Rule1Pass", "Filter2018Rule2Pass",
    "Filter2018Rule3Pass", "Filter2018Rule4Pass",
):
    assert bool(result[field]), field

# 2) A exceção da Regra 2 deve ignorar confronto de copa e buscar o último de pontos corridos.
synthetic = [
    {"DateParsed": pd.Timestamp("2024-01-01").date(), "Home": "A", "Away": "B", "HG": 1, "AG": 0, "CompetitionType": "Liga"},
    {"DateParsed": pd.Timestamp("2024-06-01").date(), "Home": "B", "Away": "A", "HG": 2, "AG": 2, "CompetitionType": "Copa"},
]
index = HistoryIndex(synthetic)
last, skipped = index.last_h2h("A", "B", pd.Timestamp("2025-01-01").date())
assert skipped == 1
assert last is not None and last["HG"] == 1 and last["AG"] == 0

# 3) Jogos reprovados permanecem no quadro completo, mas não entram em simples nem múltipla.
evaluations = pd.DataFrame([
    {
        "InputID": "aprovado-1", "MatchID": "m1", "WeekID": "2026-30", "Market": "1X2", "Side": "A",
        "Selection": "Visitante 1", "ConservativeExpectedValue": 0.08, "ConservativeProbability": 0.61,
        "DecisionProbability": 0.63, "Reliability": 0.80, "Odd": 1.90, "EffectiveOdd": 1.862,
    },
    {
        "InputID": "aprovado-1", "MatchID": "m1", "WeekID": "2026-30", "Market": "OU25", "Side": "O25",
        "Selection": "Mais de 2,5 gols", "ConservativeExpectedValue": 0.03, "ConservativeProbability": 0.66,
        "DecisionProbability": 0.67, "Reliability": 0.78, "Odd": 1.65, "EffectiveOdd": 1.617,
    },
    {
        "InputID": "aprovado-2", "MatchID": "m2", "WeekID": "2026-30", "Market": "BTTS", "Side": "BTTS_Y",
        "Selection": "Ambas marcam — Sim", "ConservativeExpectedValue": 0.05, "ConservativeProbability": 0.64,
        "DecisionProbability": 0.65, "Reliability": 0.72, "Odd": 1.75, "EffectiveOdd": 1.715,
    },
    {
        "InputID": "reprovado", "MatchID": "m3", "WeekID": "2026-30", "Market": "1X2", "Side": "H",
        "Selection": "Mandante 3", "ConservativeExpectedValue": 0.50, "ConservativeProbability": 0.80,
        "DecisionProbability": 0.82, "Reliability": 0.90, "Odd": 2.00, "EffectiveOdd": 1.96,
    },
])
filters = pd.DataFrame([
    {"InputID": "aprovado-1", "Filter2018Approved": True, "Filter2018Status": "APROVADO", "Filter2018Summary": "ok"},
    {"InputID": "aprovado-2", "Filter2018Approved": True, "Filter2018Status": "APROVADO", "Filter2018Summary": "ok"},
    {"InputID": "reprovado", "Filter2018Approved": False, "Filter2018Status": "REPROVADO", "Filter2018Summary": "não"},
])
merged = attach_filter_results(evaluations, filters)
entries, readings, all_rows, multiple = build_operational_outputs(merged, bankroll=1000.0, unit_fraction=0.01)
assert len(all_rows) == len(evaluations)
assert "reprovado" not in set(entries.get("InputID", []))
assert "reprovado" not in set(multiple.selections.get("InputID", []))
assert len(entries) == 2
assert len(multiple.selections) == 2
# Na primeira partida, a simples prioriza o maior valor financeiro; a múltipla prioriza a maior probabilidade.
assert entries[entries["InputID"].eq("aprovado-1")].iloc[0]["Selection"] == "Visitante 1"
assert multiple.selections[multiple.selections["InputID"].eq("aprovado-1")].iloc[0]["Selection"] == "Mais de 2,5 gols"
assert abs(multiple.factor - (1.65 * 1.75)) < 1e-12

# 4) Compatibilidade: todas as colunas antigas permanecem como prefixo; novas colunas vêm à direita.
def extract_list(path: Path, name: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(name)

old_storage = ROOT.parent / "tex_v281512_src" / "TEX_STATISTICS_V28_1_5_12_AUTOSAVE_COTACOES_ANTES_ANALISE" / "tex_v25_storage.py"
if old_storage.is_file():
    new_storage = ROOT / "tex_v25_storage.py"
    for list_name in ("COLUNAS_COTACOES", "COLUNAS_ANALISES"):
        old = extract_list(old_storage, list_name)
        new = extract_list(new_storage, list_name)
        assert new[:len(old)] == old
        assert len(new) > len(old)

print("TESTE V28.2.0 — FILTRO 2018, PORTÃO OPERACIONAL E COMPATIBILIDADE: OK")
