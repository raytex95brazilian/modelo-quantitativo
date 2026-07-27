from pathlib import Path
import pandas as pd

from tex_v25_core import normalize_zip
from tex_v28_core_2812 import INPUT_COLUMNS, analyze_games, build_ai_summary, load_v28_model
from tex_operacional_core import standings_context

ROOT = Path(__file__).resolve().parent
matches = normalize_zip(ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)
model = load_v28_model(ROOT / "model")

columns = [
    "ID", "Data", "Hora", "Código da liga", "Liga", "Mandante", "Visitante", "Casa de apostas",
    "Odd mandante", "Odd empate", "Odd visitante", "Odd mais de 2,5", "Odd menos de 2,5",
    "Odd ambas marcam — Sim", "Odd ambas marcam — Não",
]
rows = [
    ["b1", "2026-07-25", "20:30", "BRA", "Brasileirão Série A", "Vasco", "Mirassol", "Pixbet", 2.03, 3.32, 3.71, 2.03, 1.75, 1.85, 1.93],
    ["b2", "2026-07-26", "16:00", "BRA", "Brasileirão Série A", "Cruzeiro", "Botafogo RJ", "Pixbet", 1.80, 3.82, 4.44, 1.88, 1.88, 1.84, 1.94],
    ["b3", "2026-07-26", "16:00", "BRA", "Brasileirão Série A", "Bahia", "Corinthians", "Pixbet", 2.22, 3.44, 3.32, 1.96, 1.81, 1.78, 2.01],
    ["b4", "2026-07-26", "18:30", "BRA", "Brasileirão Série A", "Flamengo RJ", "Sao Paulo", "Pixbet", 1.50, 4.28, 6.90, 1.88, 1.88, 2.04, 1.76],
    ["b5", "2026-07-26", "18:30", "BRA", "Brasileirão Série A", "Bragantino", "Coritiba", "Pixbet", 1.64, 3.90, 5.70, 1.94, 1.83, 1.95, 1.83],
    ["b6", "2026-07-26", "18:30", "BRA", "Brasileirão Série A", "Gremio", "Fluminense", "Pixbet", 2.70, 3.35, 2.68, 1.93, 1.84, 1.76, 2.04],
    ["b7", "2026-07-26", "19:30", "BRA", "Brasileirão Série A", "Palmeiras", "Atletico-MG", "Pixbet", 1.65, 3.63, 5.30, 1.96, 1.79, 2.01, 1.77],
    ["b8", "2026-07-26", "19:30", "BRA", "Brasileirão Série A", "Remo", "Vitoria", "Pixbet", 2.15, 3.39, 3.23, 1.76, 2.00, 1.83, 1.93],
    ["m1", "2026-07-25", "20:30", "MEX", "México - Liga MX", "Guadalajara Chivas", "Juarez", "Pixbet", 1.42, 4.32, 7.20, 1.62, 2.16, 1.92, 1.77],
    ["m2", "2026-07-26", "00:00", "MEX", "México - Liga MX", "Santos Laguna", "Atl. San Luis", "Pixbet", 1.38, 4.28, 6.30, 1.68, 2.03, 1.96, 1.82],
    ["m3", "2026-07-26", "00:00", "MEX", "México - Liga MX", "Necaxa", "Monterrey", "Pixbet", 2.90, 3.54, 2.07, 1.54, 2.28, 1.49, 2.57],
    ["m4", "2026-07-26", "22:00", "MEX", "México - Liga MX", "Pachuca", "Queretaro", "Pixbet", 1.51, 3.72, 5.30, 1.64, 2.07, 1.72, 2.07],
]
games = pd.DataFrame(rows, columns=columns).reindex(columns=INPUT_COLUMNS)
entries, readings, evaluations, diagnostics = analyze_games(
    games, matches, model, bankroll=1000.0, unit_fraction=0.01, max_entries=5
)

assert len(diagnostics[diagnostics["Situação"].eq("ERRO")]) == 0
assert len(entries) == 5, entries[["Home", "Away", "Selection", "ExpectedValue"]]
assert entries["MatchID"].nunique() == 5
assert entries["Status"].eq("OPERAR").all()
assert entries["PortfolioTier"].eq("COMPLEMENTO DE META — MEIA UNIDADE").all()
assert entries["StakeMultiplier"].eq(0.5).all()
assert entries["ExpectedValue"].ge(-0.15).all()
assert {tuple(x) for x in entries[["Home", "Selection"]].to_records(index=False)} == {
    ("Vasco", "Menos de 2,5 gols"),
    ("Flamengo RJ", "Flamengo RJ"),
    ("Bragantino", "Bragantino"),
    ("Guadalajara Chivas", "Guadalajara Chivas"),
    ("Santos Laguna", "Santos Laguna"),
}
assert {"ModelSportsDifference", "MaximumComponentDisagreement", "DisagreementLevel"}.issubset(evaluations.columns)

context = standings_context(matches, "MEX", pd.Timestamp("2026-07-25").date(), "Guadalajara Chivas", "Juarez")
assert context["Available"] is True
assert context["Consolidated"] is False

summary = build_ai_summary(games, readings, evaluations, diagnostics, matches)
assert "Classificação ainda não consolidada" in summary
assert "Guadalajara Chivas 18º" not in summary
assert "Amostra histórica da faixa" in summary
assert "confiança estatística" in summary
assert "Desacordo entre componentes" in summary
assert "mínima de admissibilidade da meta" not in summary
assert "equilíbrio individual" not in summary
assert "AGUARDAR PREÇO" not in summary
assert "PREÇO FORTE" not in summary
assert "ELEGÍVEL PARA META" not in summary
assert "RESERVA" not in summary

print("TESTE META MÍNIMA 5: OK")
print(entries[["Home", "Away", "Selection", "Odd", "ExpectedValue", "PortfolioTier", "Stake"]].to_string(index=False))
