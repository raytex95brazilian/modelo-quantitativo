from pathlib import Path
import tempfile

import pandas as pd

from tex_v28_finance import (
    atualizar_registro,
    carregar_ledger_local,
    contagens_semanais,
    criar_registros_apostas,
    identificadores_partidas_registradas,
    liquidar_registro,
    mesclar_registros,
    normalizar_ledger,
    reconciliar_ledgers,
    resumo_financeiro,
    salvar_ledger_local,
    venceu_selecao,
)

assert venceu_selecao("1X2", "H", 2, 1)
assert venceu_selecao("1X2", "D", 1, 1)
assert venceu_selecao("OU25", "O25", 2, 1)
assert venceu_selecao("OU25", "U25", 1, 1)
assert venceu_selecao("BTTS", "BTTS_Y", 2, 1)
assert venceu_selecao("BTTS", "BTTS_N", 2, 0)

entries = pd.DataFrame([
    {
        "InputID": "a1", "MatchID": "BRA|2026-07-25|Casa|Fora", "Market": "1X2",
        "Side": "H", "Odd": 2.0, "Bookmaker": "Pixbet", "League": "Brasileirão Série A",
        "Code": "BRA", "DateParsed": pd.Timestamp("2026-07-25"), "Time": "18:00",
        "Home": "Casa", "Away": "Fora", "MarketName": "Resultado final 1X2",
        "Selection": "Casa", "EffectiveOdd": 1.96, "DecisionProbability": 0.56,
        "ConservativeProbability": 0.53, "ExpectedValue": 0.0388, "ProfileSample": 300,
        "SampleConfidence": "FORTE", "Reliability": 0.90, "Stake": 10.0,
    }
])
records = criar_registros_apostas(entries, 1000.0, "V28.1.5", "28.1.2", "V28.0")
assert len(records) == 1
assert records[0]["ID Aposta"] == records[0]["ID Análise"]

legacy = pd.DataFrame([{
    **records[0],
    "Casos semelhantes": 321,
    "Confiança da amostra": "MODERADA",
    "Estabilidade %": 88.0,
}]).drop(columns=[
    "Amostra histórica da faixa",
    "Confiança estatística da amostra",
    "Estabilidade da calibração %",
], errors="ignore")
normalized_legacy = normalizar_ledger(legacy)
assert int(normalized_legacy.iloc[0]["Amostra histórica da faixa"]) == 321
assert normalized_legacy.iloc[0]["Confiança estatística da amostra"] == "MODERADA"
assert float(normalized_legacy.iloc[0]["Estabilidade da calibração %"]) == 88.0

ledger, added = mesclar_registros(None, records)
assert added == 1
assert contagens_semanais(ledger) == {"2026-30": 1}
assert identificadores_partidas_registradas(ledger) == {"BRA|2026-07-25|Casa|Fora"}
ledger2, added2 = mesclar_registros(ledger, records)
assert added2 == 0 and len(ledger2) == 1

updated = liquidar_registro(ledger.iloc[0].to_dict(), 2, 1, "Teste")
assert updated["Resultado da aposta"] == "GANHA"
assert float(updated["Lucro ou prejuízo (R$)"]) == 10.0
ledger = atualizar_registro(ledger, updated)
remote_pending = ledger.copy()
remote_pending.loc[:, "Situação da liquidação"] = "PENDENTE"
remote_pending.loc[:, "Resultado da aposta"] = "PENDENTE"
remote_pending.loc[:, "Lucro ou prejuízo (R$)"] = ""
reconciled = reconciliar_ledgers(remote_pending, ledger)
assert reconciled.iloc[0]["Situação da liquidação"] == "LIQUIDADA"
assert float(reconciled.iloc[0]["Lucro ou prejuízo (R$)"]) == 10.0
summary = resumo_financeiro(ledger, 1000.0)
assert summary["liquidadas"] == 1
assert summary["ganhas"] == 1
assert summary["lucro"] == 10.0
assert summary["banca_informada"] == 1000.0
assert summary["banca_estimada"] == 1000.0

for args in [("1X2", "O25", 2, 1), ("OU25", "H", 2, 1)]:
    try:
        venceu_selecao(*args)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Combinação mercado/seleção inválida aceita: {args}")

try:
    venceu_selecao("1X2", "H", -1, 0)
except ValueError:
    pass
else:
    raise AssertionError("Placar negativo foi aceito")

# O recuo deve respeitar a ordem cronológica dos jogos, não a ordem das linhas.
chronological = pd.DataFrame([
    {**records[0], "ID Aposta": "B", "Data do jogo": "02/01/2026", "Hora do jogo": "10:00",
     "Situação da liquidação": "LIQUIDADA", "Resultado da aposta": "GANHA",
     "Entrada (R$)": 10.0, "Lucro ou prejuízo (R$)": 20.0},
    {**records[0], "ID Aposta": "A", "Data do jogo": "01/01/2026", "Hora do jogo": "10:00",
     "Situação da liquidação": "LIQUIDADA", "Resultado da aposta": "PERDIDA",
     "Entrada (R$)": 10.0, "Lucro ou prejuízo (R$)": -10.0},
    {**records[0], "ID Aposta": "C", "Data do jogo": "03/01/2026", "Hora do jogo": "10:00",
     "Situação da liquidação": "LIQUIDADA", "Resultado da aposta": "PERDIDA",
     "Entrada (R$)": 10.0, "Lucro ou prejuízo (R$)": -10.0},
])
chronological_summary = resumo_financeiro(chronological, 1000.0)
assert chronological_summary["maior_recuo"] == 10.0

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "ledger.csv"
    salvar_ledger_local(path, ledger)
    loaded = carregar_ledger_local(path)
    assert len(loaded) == 1
    assert loaded.iloc[0]["Resultado da aposta"] == "GANHA"

print("TESTE FINANCEIRO V28: OK")
